"""Measure the three ways the API could hold the data: pandas in memory, SQLite and PostgreSQL.

The three options load the real CSV, with every column, and answer the two queries the API needs:
the title search (`GET /movies?title=`: total plus the first 20 by relevance and popularity) and the
default list (the first 20 by weighted rating). For each one it measures:
- build: making the store from the CSV, once, as the seed would. pandas has none: each worker reads the CSV;
- worker: what each Gunicorn worker pays at startup, in a fresh process: time until it answers and memory;
- queries: latency in milliseconds, median and p95, after a warm-up.
It also checks that the three return the same results, so the comparison is fair.

Needs pandas and psycopg (scripts/requirements-benchmark.txt) and a throwaway Postgres:

    docker run -d --rm --name imdb-bench -e POSTGRES_PASSWORD=bench -p 127.0.0.1:5433:5432 postgres:18
    BENCH_DATABASE_URL=postgresql://postgres:bench@localhost:5433/postgres \\
        python scripts/benchmark_storage.py [--csv PATH]

Timings depend on the machine, so the report is printed, not versioned: the ADR quotes it with the
machine and the date.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import platform
import re
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
import unicodedata
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "IMDb_movies.csv"
QUERIES = ["shawshank", "godfather", "relatos salvajes", "amelie", "aeon flux", "the", "up", "%"]
PAGE = 20
WARMUP, RUNS, WORKER_RUNS = 3, 25, 3
# Latin letters that NFKD doesn't decompose (see the data profile), mapped the way Postgres unaccent does.
EXTRA_LETTERS = str.maketrans({"ø": "o", "æ": "ae", "œ": "oe", "ð": "d", "þ": "th", "ł": "l", "đ": "d"})
DERIVED = ["year_n", "avg_vote_n", "votes_n", "wr", "ots", "its"]

Rows = list[list[str]]
Result = tuple[int, list[str]]  # total, ids of the first page


def fold(text: str) -> str:
    """Case- and accent-insensitive form: stored in the search columns and applied to the query."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold().translate(EXTRA_LETTERS)


def like_escape(text: str) -> str:
    """Make %, _ and the escape character itself match literally in LIKE (escape character: backslash)."""
    return re.sub(r"([\\%_])", r"\\\1", text)


def search_params(query: str) -> dict[str, str]:
    q = fold(query)
    phrase = '"' + q.replace('"', '""') + '"'  # FTS5 phrase: the text as is, quotes doubled
    return {"q": q, "prefix": like_escape(q) + "%", "pattern": f"%{like_escape(q)}%", "fts": phrase}


# --- Reading the CSV (shared by the SQL options)


def read_csv(path: Path) -> tuple[list[str], Rows, list[tuple[Any, ...]]]:
    """Raw rows plus the derived columns: year, rating, votes, weighted rating and the folded titles."""
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        rows = list(reader)
    col = {name: i for i, name in enumerate(header)}
    years = [int(re.search(r"[0-9]{4}", r[col["year"]]).group()) for r in rows]  # lenient, as in ADR 0003
    avgs = [float(r[col["avg_vote"]]) for r in rows]
    votes = [int(r[col["votes"]]) for r in rows]
    c = statistics.fmean(avgs)
    m = statistics.quantiles(votes, n=100, method="inclusive")[89]
    derived = [
        (y, a, v, v / (v + m) * a + m / (v + m) * c, fold(r[col["original_title"]]), fold(r[col["title"]]))
        for r, y, a, v in zip(rows, years, avgs, votes)
    ]
    return header, rows, derived


# --- The three stores. Each answers search() and top_rated() with the same semantics.


class PandasStore:
    """(a) Each worker reads the CSV into a DataFrame and filters it in memory."""

    def __init__(self, csv_path: Path) -> None:
        import pandas as pd

        df = pd.read_csv(csv_path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        df["year_n"] = df["year"].str.extract(r"([0-9]{4})", expand=False).astype(int)
        df["avg_vote_n"] = df["avg_vote"].astype(float)
        df["votes_n"] = df["votes"].astype(int)
        c, m = df["avg_vote_n"].mean(), df["votes_n"].quantile(0.9)
        df["wr"] = df["votes_n"] / (df["votes_n"] + m) * df["avg_vote_n"] + m / (df["votes_n"] + m) * c
        df["ots"] = df["original_title"].map(fold)
        df["its"] = df["title"].map(fold)
        self.df = df.sort_values(["wr", "imdb_title_id"], ascending=[False, True], ignore_index=True)

    def memory_mb(self) -> float:
        return self.df.memory_usage(deep=True).sum() / 1e6

    def search(self, query: str) -> Result:
        import numpy as np

        q, df = fold(query), self.df
        hits = df[df["ots"].str.contains(q, regex=False) | df["its"].str.contains(q, regex=False)]
        exact = (hits["ots"] == q) | (hits["its"] == q)
        prefix = hits["ots"].str.startswith(q) | hits["its"].str.startswith(q)
        ranked = hits.assign(rank=np.select([exact, prefix], [0, 1], 2)).sort_values(
            ["rank", "votes_n", "imdb_title_id"], ascending=[True, False, True]
        )
        return len(hits), ranked["imdb_title_id"].head(PAGE).tolist()

    def top_rated(self) -> Result:
        return len(self.df), self.df["imdb_title_id"].head(PAGE).tolist()


class SqlStore:
    """(b) SQLite and (c) PostgreSQL: the same SQL, with each driver's parameter style."""

    def __init__(self, conn: Any, param: Callable[[str], str], fts: bool = False) -> None:
        self.conn, self.fts = conn, fts
        like = f"(ots LIKE {param('pattern')} ESCAPE '\\' OR its LIKE {param('pattern')} ESCAPE '\\')"
        fts_match = f"rowid IN (SELECT rowid FROM movies_fts WHERE movies_fts MATCH {param('fts')})"
        order = (
            f"ORDER BY CASE WHEN ots = {param('q')} OR its = {param('q')} THEN 0 "
            f"WHEN ots LIKE {param('prefix')} ESCAPE '\\' OR its LIKE {param('prefix')} ESCAPE '\\' THEN 1 "
            f"ELSE 2 END, votes_n DESC, imdb_title_id LIMIT {PAGE}"
        )
        self.like_sql = f"SELECT imdb_title_id, COUNT(*) OVER () FROM movies WHERE {like} {order}"
        self.fts_sql = f"SELECT imdb_title_id, COUNT(*) OVER () FROM movies WHERE {fts_match} {order}"

    def search_sql(self, query: str) -> str:
        # Trigrams need at least 3 characters: shorter queries scan the table.
        return self.fts_sql if self.fts and len(fold(query)) >= 3 else self.like_sql

    def search(self, query: str) -> Result:
        rows = self.conn.execute(self.search_sql(query), search_params(query)).fetchall()
        return (rows[0][1] if rows else 0), [r[0] for r in rows]

    def top_rated(self) -> Result:
        sql = f"SELECT imdb_title_id FROM movies ORDER BY wr DESC, imdb_title_id LIMIT {PAGE}"
        ids = [r[0] for r in self.conn.execute(sql)]
        total = self.conn.execute("SELECT count(*) FROM movies").fetchone()[0]
        return total, ids


def build_sqlite(path: Path, header: list[str], rows: Rows, derived: list[tuple[Any, ...]]) -> None:
    conn = sqlite3.connect(path)
    columns = ", ".join(f'"{c}" TEXT' for c in header)
    conn.execute(
        f"CREATE TABLE movies ({columns}, "
        "year_n INTEGER, avg_vote_n REAL, votes_n INTEGER, wr REAL, ots TEXT, its TEXT)"
    )
    placeholders = ", ".join(["?"] * (len(header) + len(DERIVED)))
    conn.executemany(f"INSERT INTO movies VALUES ({placeholders})", (r + list(d) for r, d in zip(rows, derived)))
    conn.execute("CREATE UNIQUE INDEX movies_id ON movies (imdb_title_id)")
    conn.execute("CREATE INDEX movies_wr ON movies (wr DESC, imdb_title_id)")
    conn.execute("CREATE VIRTUAL TABLE movies_fts USING fts5(ots, its, content='movies', tokenize='trigram')")
    conn.execute("INSERT INTO movies_fts (movies_fts) VALUES ('rebuild')")
    conn.commit()
    conn.close()


def open_sqlite(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def build_postgres(dsn: str, header: list[str], rows: Rows, derived: list[tuple[Any, ...]]) -> None:
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS movies")
        columns = ", ".join(f'"{c}" text' for c in header)
        conn.execute(
            f"CREATE TABLE movies ({columns}, year_n smallint, avg_vote_n real, votes_n integer, "
            "wr double precision, ots text, its text)"
        )
        with conn.cursor() as cur, cur.copy("COPY movies FROM STDIN") as copy:
            for r, d in zip(rows, derived):
                copy.write_row(r + list(d))
        conn.execute("ALTER TABLE movies ADD PRIMARY KEY (imdb_title_id)")
        conn.execute("CREATE INDEX movies_wr ON movies (wr DESC, imdb_title_id)")
        conn.execute("ANALYZE movies")


def add_trigram_indexes(dsn: str) -> None:
    import psycopg

    with psycopg.connect(dsn, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        conn.execute("CREATE INDEX movies_ots_trgm ON movies USING gin (ots gin_trgm_ops)")
        conn.execute("CREATE INDEX movies_its_trgm ON movies USING gin (its gin_trgm_ops)")
        conn.execute("ANALYZE movies")


def postgres_sizes(dsn: str) -> tuple[float, float]:
    import psycopg

    with psycopg.connect(dsn) as conn:
        table, indexes = conn.execute("SELECT pg_table_size('movies'), pg_indexes_size('movies')").fetchone()
    return table / 1e6, indexes / 1e6


def open_postgres(dsn: str) -> Any:
    import psycopg

    return psycopg.connect(dsn, autocommit=True)


def scan_nodes(conn: Any, store: SqlStore, query: str) -> str:
    """The scan nodes of the Postgres plan for a search: shows whether it uses the trigram indexes."""
    plan = conn.execute("EXPLAIN " + store.search_sql(query), search_params(query)).fetchall()
    nodes = [re.sub(r"\s+\(.*", "", line).strip(" ->") for (line,) in plan if "Scan" in line]
    return ", ".join(dict.fromkeys(nodes))


# --- Measuring


def latency(fn: Callable[[], object]) -> tuple[float, float]:
    """Median and p95 in milliseconds, after a warm-up."""
    for _ in range(WARMUP):
        fn()
    times = []
    for _ in range(RUNS):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000)
    return statistics.median(times), statistics.quantiles(times, n=20, method="inclusive")[18]


def timed(fn: Callable[[], object]) -> tuple[float, Any]:
    start = time.perf_counter()
    result = fn()
    return time.perf_counter() - start, result


def rss_mb() -> float:
    """Resident memory of this process (Linux), or the peak where /proc is not available."""
    try:
        status = Path("/proc/self/status").read_text()
        return int(re.search(r"VmRSS:\s+(\d+)", status).group(1)) / 1024
    except OSError:
        import resource

        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


def worker(kind: str, csv_path: Path, sqlite_path: Path, dsn: str) -> None:
    """One Gunicorn worker starting up: get its store ready, answer a search, report its memory."""
    if kind == "pandas":
        store: PandasStore | SqlStore = PandasStore(csv_path)
    elif kind == "sqlite":
        store = SqlStore(open_sqlite(sqlite_path), lambda name: f":{name}", fts=True)
    else:
        store = SqlStore(open_postgres(dsn), lambda name: f"%({name})s")
    store.search("godfather")
    print(json.dumps({"rss_mb": rss_mb()}))


def measure_worker(kind: str, csv_path: Path, sqlite_path: Path) -> tuple[float, float]:
    """Median over fresh processes: seconds until the worker answers, and its memory in MB."""
    runs = []
    for _ in range(WORKER_RUNS):
        start = time.perf_counter()
        out = subprocess.run(
            [sys.executable, __file__, "--worker", kind, "--csv", str(csv_path), "--sqlite", str(sqlite_path)],
            check=True, capture_output=True, text=True,
        ).stdout
        runs.append((time.perf_counter() - start, json.loads(out)["rss_mb"]))
    return statistics.median(t for t, _ in runs), statistics.median(m for _, m in runs)


# --- Report


def dec(x: float, digits: int = 1) -> str:
    return f"{x:,.{digits}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def environment(dsn: str) -> list[str]:
    import pandas as pd
    import psycopg

    cpuinfo = Path("/proc/cpuinfo")
    cpu = re.search(r"model name\s*:\s*(.+)", cpuinfo.read_text()) if cpuinfo.exists() else None
    with psycopg.connect(dsn) as conn:
        server = conn.execute("SHOW server_version").fetchone()[0]
    machine = cpu.group(1).strip() if cpu else platform.processor()
    return [
        f"- Máquina: {machine}, {os.cpu_count()} hilos; {platform.platform()}.",
        f"- Python {platform.python_version()}, pandas {pd.__version__}, psycopg {psycopg.__version__}, "
        f"SQLite {sqlite3.sqlite_version}, PostgreSQL {server.split()[0]}.",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--worker", choices=["pandas", "sqlite", "postgres"], help=argparse.SUPPRESS)
    parser.add_argument("--sqlite", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    dsn = os.environ.get("BENCH_DATABASE_URL", "")
    if args.worker:
        worker(args.worker, args.csv, args.sqlite, dsn)
        return
    if not dsn:
        raise SystemExit("error: set BENCH_DATABASE_URL to a throwaway Postgres (see the docstring)")

    read_s, (header, rows, derived) = timed(lambda: read_csv(args.csv))
    with tempfile.TemporaryDirectory() as tmp:
        sqlite_path = Path(tmp) / "movies.db"
        sqlite_s, _ = timed(lambda: build_sqlite(sqlite_path, header, rows, derived))
        postgres_s, _ = timed(lambda: build_postgres(dsn, header, rows, derived))
        pg_table, pg_indexes = postgres_sizes(dsn)
        pandas_s, pandas = timed(lambda: PandasStore(args.csv))
        pg_conn = open_postgres(dsn)
        stores: dict[str, Any] = {
            "pandas": pandas,
            "SQLite, recorre la tabla": SqlStore(open_sqlite(sqlite_path), lambda name: f":{name}"),
            "SQLite, FTS5 trigram": SqlStore(open_sqlite(sqlite_path), lambda name: f":{name}", fts=True),
            "PostgreSQL, recorre la tabla": SqlStore(pg_conn, lambda name: f"%({name})s"),
        }
        results = {
            name: {q: latency(lambda s=store, q=q: s.search(q)) for q in QUERIES} for name, store in stores.items()
        }
        for name, store in stores.items():
            results[name]["lista"] = latency(store.top_rated)
        trigram_s, _ = timed(lambda: add_trigram_indexes(dsn))
        _, pg_indexes_after = postgres_sizes(dsn)
        trigram = SqlStore(pg_conn, lambda name: f"%({name})s")
        stores["PostgreSQL, índices trigram"] = trigram
        results["PostgreSQL, índices trigram"] = {q: latency(lambda q=q: trigram.search(q)) for q in QUERIES}
        results["PostgreSQL, índices trigram"]["lista"] = latency(trigram.top_rated)
        plans = {q: scan_nodes(pg_conn, trigram, q) for q in ("shawshank", "the", "up")}
        workers = {kind: measure_worker(kind, args.csv, sqlite_path) for kind in ("pandas", "sqlite", "postgres")}

        reference = {q: pandas.search(q) for q in QUERIES} | {"lista": pandas.top_rated()}
        mismatches = [
            f"{name} / {q}"
            for name, store in stores.items()
            for q in reference
            if (store.top_rated() if q == "lista" else store.search(q)) != reference[q]
        ]
        sqlite_mb = sqlite_path.stat().st_size / 1e6

    names = list(results)
    out = [
        "## Entorno",
        "",
        *environment(dsn),
        "",
        "## Construcción desde el CSV",
        "",
        "| Paso | Tiempo | Tamaño |",
        "|---|---:|---:|",
        f"| Leer el CSV y derivar columnas (común a SQLite y PostgreSQL) | {dec(read_s, 2)} s | — |",
        f"| SQLite: tabla, índices y FTS5 trigram | {dec(sqlite_s, 2)} s | {dec(sqlite_mb)} MB |",
        f"| PostgreSQL: COPY, clave primaria e índice del rating | {dec(postgres_s, 2)} s "
        f"| {dec(pg_table)} MB tabla + {dec(pg_indexes)} MB índices |",
        f"| PostgreSQL: índices trigram | {dec(trigram_s, 2)} s | +{dec(pg_indexes_after - pg_indexes)} MB |",
        f"| pandas: cada worker lee el CSV | {dec(pandas_s, 2)} s | {dec(pandas.memory_mb())} MB de DataFrame |",
        "",
        f"## Cada worker de Gunicorn (proceso nuevo, mediana de {WORKER_RUNS})",
        "",
        "| Opción | Hasta responder la primera búsqueda | Memoria (RSS) |",
        "|---|---:|---:|",
        *(f"| {kind} | {dec(t, 2)} s | {dec(mb, 0)} MB |" for kind, (t, mb) in workers.items()),
        "",
        f"## Consultas (ms, mediana / p95 de {RUNS})",
        "",
        "| Consulta | Resultados | " + " | ".join(names) + " |",
        "|---|---:|" + "---:|" * len(names),
    ]
    for q in [*QUERIES, "lista"]:
        label = "lista por rating ponderado" if q == "lista" else f"`{q}`"
        cells = " | ".join(f"{dec(results[n][q][0])} / {dec(results[n][q][1])}" for n in names)
        out.append(f"| {label} | {dec(reference[q][0], 0)} | {cells} |")
    out += [
        "",
        "## Planes de PostgreSQL con índices trigram",
        "",
        *(f"- `{q}`: {nodes}" for q, nodes in plans.items()),
        "",
        "Las cinco variantes devuelven los mismos resultados (total y primera página): "
        + ("sí." if not mismatches else "no, difieren " + ", ".join(mismatches) + "."),
    ]
    print("\n".join(out))


if __name__ == "__main__":
    main()
