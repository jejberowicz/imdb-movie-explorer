"""Profile the IMDb movies CSV and write the findings to a Markdown report.

The report has two layers:
1. Format by column: each column declares the format it should have, and the
   report counts empty and invalid values, with examples. This is what surfaces
   problems nobody was looking for.
2. Targeted analyses that answer design questions: keys, search, dates,
   multi-value fields, money, rating and text quality.

Standard library only, so it runs before the project has any dependencies:

    python3 scripts/profile_dataset.py [--csv PATH] [--out PATH]
"""

from __future__ import annotations

import argparse
import codecs
import csv
import gzip
import io
import re
import statistics
import unicodedata
from collections import Counter
from collections.abc import Callable, Iterable
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "data" / "IMDb_movies.csv.gz"
DEFAULT_OUT = ROOT / "docs" / "data-profile.md"

Row = dict[str, str]

YEAR_MIN, YEAR_MAX = 1880, 2030
INT32_MAX = 2**31 - 1
NULL_TOKENS = {"none", "null", "nan", "n/a", "na", "-", "?", "unknown"}
# A spreadsheet runs values starting with these as formulas when it opens an exported CSV.
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
PRE_EURO_CURRENCIES = {"ATS", "BEF", "DEM", "ESP", "FIM", "FRF", "GRD", "IEP", "ITL", "LUF", "NLG", "PTE"}
# Names that contain the list separator (ISO 639 style), found while reviewing rows with repeated items.
COMMA_NAMES = {"Greek, Ancient (to 1453)", "Norse, Old"}
# Country names that no longer exist (dissolved or renamed), reviewed by hand among the 194 in the CSV.
FORMER_COUNTRIES = {
    "Burma", "Czechoslovakia", "East Germany", "Federal Republic of Yugoslavia", "Korea", "Netherlands Antilles",
    "North Vietnam", "Serbia and Montenegro", "Soviet Union", "Swaziland", "West Germany", "Yugoslavia", "Zaire",
}
SEARCH_PROBES = ["shawshank", "godfather", "relatos salvajes", "amelie"]
TITLE_EXAMPLES = {"tt0068646", "tt0111161", "tt3011894"}
# UTF-8 text that was decoded as Latin-1 or Windows-1252: "é" shows up as "Ã©".
MOJIBAKE = re.compile(r"Ã[\x80-\xbf]|Â[\x80-\xbf]|â€")
# Each check returns a match (or True) when the text has the problem.
ENCODING_ISSUES: dict[str, Callable[[str], object]] = {
    "mojibake (UTF-8 leído como Latin-1)": MOJIBAKE.search,
    "carácter de reemplazo U+FFFD": re.compile(r"\N{REPLACEMENT CHARACTER}").search,
    "espacios no estándar (NBSP, etc.)": re.compile(
        r"[\N{NO-BREAK SPACE}\N{EN QUAD}-\N{ZERO WIDTH SPACE}\N{NARROW NO-BREAK SPACE}"
        r"\N{MEDIUM MATHEMATICAL SPACE}\N{IDEOGRAPHIC SPACE}]"
    ).search,
}
TEXT_ISSUES: dict[str, Callable[[str], object]] = {
    **ENCODING_ISSUES,
    "caracteres de control": re.compile(r"[\x00-\x08\x0b-\x1f\x7f]").search,
    "espacios al inicio o al final": re.compile(r"^\s|\s$").search,
    "espacios dobles": re.compile(r"  ").search,
    "no normalizado en NFC": lambda text: unicodedata.normalize("NFC", text) != text,
}


# --- Parsers: return the parsed value, or None when the text doesn't have the format.
# They use regexes instead of int()/float(), which also accept " 5", "5_0", "nan" or "1e3".


def parse_id(text: str) -> str | None:
    return text if re.fullmatch(r"tt[0-9]{7,8}", text) else None


def parse_int(text: str) -> int | None:
    return int(text) if re.fullmatch(r"[0-9]+", text) else None


def parse_whole(text: str) -> int | None:
    """Integer that may come as "57.0" (pandas writes integer columns with gaps as floats)."""
    match = re.fullmatch(r"([0-9]+)(\.0)?", text)
    return int(match.group(1)) if match else None


def parse_score(text: str) -> int | None:
    score = parse_whole(text)
    return score if score is not None and score <= 100 else None


def parse_year(text: str) -> int | None:
    year = parse_int(text)
    return year if year is not None and YEAR_MIN <= year <= YEAR_MAX else None


def parse_date(text: str) -> date | int | None:
    """Calendar-checked YYYY-MM-DD, or a bare year (returned as int)."""
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", text):
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    return parse_year(text)


def parse_rating(text: str) -> float | None:
    if not re.fullmatch(r"[0-9]{1,2}(\.[0-9])?", text):
        return None
    rating = float(text)
    return rating if 1 <= rating <= 10 else None


def parse_money(text: str) -> tuple[str, int] | None:
    match = re.fullmatch(r"(\$|[A-Z]{3}) ([0-9]+)", text)
    return (match.group(1), int(match.group(2))) if match else None


def parse_list(text: str) -> list[str] | None:
    """Split on commas, re-joining the known names that contain one."""
    items: list[str] = []
    for part in (part.strip() for part in text.split(",")):
        if items and f"{items[-1]}, {part}" in COMMA_NAMES:
            items[-1] = f"{items[-1]}, {part}"
        else:
            items.append(part)
    return items if all(items) else None


def parse_text(text: str) -> str:
    return text


Parser = Callable[[str], object]

SCHEMA: dict[str, tuple[str, Parser]] = {
    "imdb_title_id": ("`tt` + 7-8 dígitos", parse_id),
    "title": ("texto", parse_text),
    "original_title": ("texto", parse_text),
    "year": (f"año {YEAR_MIN}–{YEAR_MAX}", parse_year),
    "date_published": ("`AAAA-MM-DD` o `AAAA`", parse_date),
    "genre": ("lista", parse_list),
    "duration": ("entero (minutos)", parse_int),
    "country": ("lista", parse_list),
    "language": ("lista", parse_list),
    "director": ("lista", parse_list),
    "writer": ("lista", parse_list),
    "production_company": ("texto", parse_text),
    "actors": ("lista", parse_list),
    "description": ("texto", parse_text),
    "avg_vote": ("decimal 1–10", parse_rating),
    "votes": ("entero", parse_int),
    "budget": ("`<moneda> <monto>`", parse_money),
    "usa_gross_income": ("`<moneda> <monto>`", parse_money),
    "worlwide_gross_income": ("`<moneda> <monto>`", parse_money),
    "metascore": ("entero 0–100", parse_score),
    "reviews_from_users": ("entero", parse_whole),
    "reviews_from_critics": ("entero", parse_whole),
}
TEXT_COLUMNS = [col for col, (_, parser) in SCHEMA.items() if parser in (parse_text, parse_list)]
LIST_COLUMNS = [col for col, (_, parser) in SCHEMA.items() if parser is parse_list]
MONEY_COLUMNS = [col for col, (_, parser) in SCHEMA.items() if parser is parse_money]
NUMERIC_COLUMNS = [
    col for col, (_, parser) in SCHEMA.items() if parser in (parse_int, parse_whole, parse_score, parse_rating)
]


# --- Helpers


def fold(text: str) -> str:
    """Case- and accent-insensitive form, as the search should compare."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c)).casefold()


def shape(text: str) -> str:
    """Format of a value, with each run of digits replaced by N: "2019-10-09" → "N-N-N"."""
    return re.sub(r"[0-9]+", "N", text)


def percentile(values: list[float], p: int) -> float:
    """Linear interpolation, the same as Postgres percentile_cont and pandas quantile."""
    if len(values) < 2:
        return values[0]
    return statistics.quantiles(values, n=100, method="inclusive")[p - 1]


def like_without_escaping(query: str) -> re.Pattern[str]:
    """Regex equivalent to ILIKE '%' || query || '%' when % and _ in the query are not escaped."""
    regex = "".join(".*" if c == "%" else "." if c == "_" else re.escape(c) for c in f"%{query}%")
    return re.compile(regex, re.IGNORECASE | re.DOTALL)


def unmojibake(text: str) -> str | None:
    """Undo UTF-8 that was decoded as Windows-1252 or Latin-1, or None if that doesn't reverse it cleanly."""
    for codec in ("cp1252", "latin-1"):
        try:
            fixed = text.encode(codec).decode("utf-8")
        except UnicodeError:
            continue
        if not MOJIBAKE.search(fixed):
            return fixed
    return None


def votes_of(row: Row) -> int:
    return parse_int(row["votes"]) or 0


def repeated(counter: Counter) -> int:
    return sum(1 for n in counter.values() if n > 1)


def fmt(n: float) -> str:
    """Thousands separator in es-AR style (85.855)."""
    return f"{n:,.0f}".replace(",", ".")


def dec(x: float, digits: int = 1) -> str:
    """Decimal with comma, es-AR style (5,90)."""
    return f"{x:.{digits}f}".replace(".", ",")


def pct(part: int, total: int) -> str:
    return dec(100 * part / total) + " %"


def megabytes(size: int) -> str:
    return dec(size / 1e6) + " MB"


def cell(text: str) -> str:
    """Make data safe inside a Markdown table and show invisible characters as <U+XXXX>."""
    visible = "".join(
        f"<U+{ord(c):04X}>" if c != " " and unicodedata.category(c) in ("Zs", "Cc", "Cf") else c for c in text
    )
    return visible.replace("|", "\\|")


def quote(text: str) -> str:
    return f'"{cell(text)}"'


def snippet(text: str, check: Callable[[str], object], width: int = 25) -> str:
    """Part of the text around the first problem, to show it in the report."""
    match = check(text)
    if not isinstance(match, re.Match):
        return text[: 2 * width] + ("…" if len(text) > 2 * width else "")
    start, end = max(0, match.start() - width), match.end() + width
    return ("…" if start else "") + text[start:end] + ("…" if end < len(text) else "")


def movie(row: Row) -> str:
    return f"{cell(row['original_title'])} ({row['year']})"


# --- Loading


def read_raw(path: Path) -> bytes:
    """The bytes of the CSV; a .gz file is decompressed in memory."""
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


def load(path: Path) -> tuple[list[str], list[Row], list[int]]:
    """Read the CSV. Rows with a wrong number of fields are set aside (by line number), not fatal."""
    rows: list[Row] = []
    malformed: list[int] = []
    reader = csv.reader(io.StringIO(read_raw(path).decode("utf-8-sig"), newline=""))
    header = next(reader, [])
    for fields in reader:
        if len(fields) == len(header):
            rows.append(dict(zip(header, fields)))
        else:
            malformed.append(reader.line_num)
    return header, rows, malformed


# --- Report sections


def section_overview(path: Path, header: list[str], rows: list[Row], malformed: list[int]) -> list[str]:
    raw = read_raw(path)
    gz_size = len(gzip.compress(raw, compresslevel=9))
    crlf, lf = raw.count(b"\r\n"), raw.count(b"\n")
    endings = "LF" if not crlf else "CRLF (Windows) en todas las líneas" if crlf == lf else "mezclados"
    multiline = sum(1 for r in rows for v in r.values() if "\n" in v or "\r" in v)
    lines_info = f" (líneas {', '.join(map(str, malformed[:5]))})" if malformed else ""
    unknown = [col for col in header if col not in SCHEMA]
    return [
        "## Resumen",
        "",
        f"- Filas: **{fmt(len(rows))}**; columnas: **{len(header)}**.",
        f"- Tamaño: {megabytes(len(raw))}; en gzip (nivel 9): {megabytes(gz_size)}.",
        f"- UTF-8 {'con' if raw.startswith(codecs.BOM_UTF8) else 'sin'} BOM; finales de línea: {endings}.",
        f"- Filas con una cantidad de campos distinta de {len(header)}: {fmt(len(malformed))}{lines_info}.",
        f"- Campos con saltos de línea adentro: {fmt(multiline)}.",
        *([f"- Columnas sin formato declarado: {', '.join(unknown)}."] if unknown else []),
        "",
    ]


def describe_invalid(invalid: list[Row], col: str) -> str:
    if not invalid:
        return "0"
    first = invalid[0]
    return f"{fmt(len(invalid))} (p. ej. `{first['imdb_title_id']}`: {quote(first[col])})"


def describe_shapes(values: Iterable[str], limit: int = 3) -> str:
    counts = Counter(shape(v) for v in values)
    shown = " · ".join(f"`{cell(s)}` ×{fmt(n)}" for s, n in counts.most_common(limit))
    rest = len(counts) - limit
    return shown + (f" · {rest} más" if rest > 0 else "")


def section_formats(header: list[str], rows: list[Row]) -> list[str]:
    lines = [
        "## Formato por columna",
        "",
        "Formato esperado de cada columna y cuántos valores no lo cumplen. "
        "En «Formatos observados», cada secuencia de dígitos se reemplaza por `N`.",
        "",
        "| Columna | Formato esperado | Vacíos | Inválidos | Formatos observados |",
        "|---|---|---:|---|---|",
    ]
    for col in header:
        label, parser = SCHEMA.get(col, ("sin declarar", parse_text))
        filled = [r for r in rows if r[col].strip()]
        invalid = [r for r in filled if parser(r[col]) is None]
        shapes = "—" if col in TEXT_COLUMNS else describe_shapes(r[col] for r in filled)
        empty = len(rows) - len(filled)
        empty_info = f"{fmt(empty)} ({pct(empty, len(rows))})" if empty else "0"
        lines.append(f"| `{col}` | {label} | {empty_info} | {describe_invalid(invalid, col)} | {shapes} |")
    return lines + [""]


def section_null_tokens(header: list[str], rows: list[Row]) -> list[str]:
    lines = [
        "## Nulos disfrazados",
        "",
        f"Valores que parecen «sin dato» ({', '.join(sorted(NULL_TOKENS))}), por columna:",
        "",
    ]
    for col in header:
        hits = [r for r in rows if r[col].strip().casefold() in NULL_TOKENS]
        if hits:
            counts = ", ".join(f"{quote(v)} ×{fmt(n)}" for v, n in Counter(r[col] for r in hits).items())
            ids = ", ".join(f"`{r['imdb_title_id']}`" for r in hits[:3])
            lines.append(f"- `{col}`: {counts} (p. ej. {ids}).")
    inside: list[str] = []
    for col in LIST_COLUMNS:
        tokens: Counter[str] = Counter()
        for r in rows:
            if r[col].strip().casefold() not in NULL_TOKENS:
                tokens.update({item for item in parse_list(r[col]) or [] if item.casefold() in NULL_TOKENS})
        inside += [f"{quote(token)} en {fmt(n)} filas de `{col}`" for token, n in sorted(tokens.items())]
    silent = [r for r in rows if r["language"] == "None"]
    before_1930 = sum(1 for r in silent if (year := parse_year(r["year"])) is not None and year < 1930)
    return lines + [
        f"- Dentro de una lista, junto a otros valores: {', '.join(inside) or 'ninguno'}.",
        "",
        "Revisados a mano: en los títulos son películas reales (*Unknown*, de 2006 y de 2011, y una llamada *?*). "
        f'De las {fmt(len(silent))} filas con `language` = "None", {fmt(before_1930)} son anteriores a 1930, '
        "la época del cine mudo.",
        "",
    ]


def section_keys(rows: list[Row]) -> list[str]:
    ids = Counter(r["imdb_title_id"] for r in rows)
    titles = Counter(r["original_title"] for r in rows)
    title_year = Counter((r["original_title"], r["year"]) for r in rows)
    same_movie = Counter((fold(r["original_title"]), r["year"], r["director"], r["duration"]) for r in rows)
    return [
        "## Clave y duplicados",
        "",
        f"- `imdb_title_id` repetidos: {fmt(repeated(ids))}.",
        f"- `original_title` repetidos (comparación exacta): {fmt(repeated(titles))} títulos; "
        f"con el mismo título y año: {fmt(repeated(title_year))}.",
        "- Posibles duplicados reales (mismo título, año, director y duración, con distinto id): "
        f"{fmt(repeated(same_movie))}.",
        "",
    ]


def kept_letters(text: str) -> list[str]:
    """Latin letters that folding leaves non-ASCII, because NFKD doesn't decompose them (ø, æ…)."""
    return [c for c in fold(text) if not c.isascii() and "LATIN" in unicodedata.name(c, "")]


def section_titles(rows: list[Row]) -> list[str]:
    differ = sum(1 for r in rows if r["title"] != r["original_title"])
    folded = [(fold(r["title"]), fold(r["original_title"])) for r in rows]
    kept = Counter(c for r in rows for col in ("title", "original_title") for c in kept_letters(r[col]))
    kept_rows = sorted(
        (r for r in rows if kept_letters(r["title"]) or kept_letters(r["original_title"])), key=votes_of, reverse=True
    )
    lines = [
        "## Títulos y búsqueda",
        "",
        f"- `title` difiere de `original_title` en **{fmt(differ)}** filas: `title` está en italiano "
        "(el dataset parece scrapeado con configuración regional italiana).",
        "",
        "| imdb_title_id | title | original_title |",
        "|---|---|---|",
        *(
            f"| {r['imdb_title_id']} | {cell(r['title'])} | {cell(r['original_title'])} |"
            for r in rows
            if r["imdb_title_id"] in TITLE_EXAMPLES
        ),
        "",
        "- Títulos con caracteres no ASCII: "
        f"{fmt(sum(1 for r in rows if not r['title'].isascii()))} en `title`, "
        f"{fmt(sum(1 for r in rows if not r['original_title'].isascii()))} en `original_title`.",
        "- Letras latinas que el plegado no simplifica, porque NFKD no las descompone: "
        + ", ".join(f"{c} ×{fmt(n)}" for c, n in kept.most_common())
        + f", en {fmt(len(kept_rows))} filas (p. ej. {', '.join(quote(r['original_title']) for r in kept_rows[:3])}).",
        "",
        "Resultados de cada búsqueda (substring) según la estrategia. «Plegado» = sin mayúsculas ni acentos.",
        "",
        "| Búsqueda | Solo `title` (ILIKE) | Ambas columnas (ILIKE) | Ambas columnas, plegado | La más votada |",
        "|---|---:|---:|---:|---|",
    ]
    for probe in SEARCH_PROBES:
        only_title = sum(1 for r in rows if probe in r["title"].casefold())
        both = sum(1 for r in rows if probe in r["title"].casefold() or probe in r["original_title"].casefold())
        hits = [r for r, (t, o) in zip(rows, folded) if probe in t or probe in o]
        top = movie(max(hits, key=votes_of)) if hits else "—"
        lines.append(f"| `{probe}` | {fmt(only_title)} | {fmt(both)} | {fmt(len(hits))} | {top} |")
    lines.append("")
    for char in ("%", "_"):
        containing = [
            r["original_title"] if char in r["original_title"] else r["title"]
            for r in rows
            if char in r["title"] or char in r["original_title"]
        ]
        unescaped = like_without_escaping(char)
        matched = sum(1 for r in rows if any(unescaped.fullmatch(r[col]) for col in ("title", "original_title")))
        lines.append(
            f"- `{char}`: lo contienen {fmt(len(containing))} títulos "
            f"(p. ej. {', '.join(quote(t) for t in containing[:3])}); "
            f"buscarlo sin escapar el comodín devuelve {fmt(matched)}."
        )
    longest = {col: max(rows, key=lambda r: len(r[col])) for col in ("title", "original_title")}
    lengths = {col: [len(r[col]) for r in rows] for col in ("title", "original_title")}
    short = sorted((r for r in rows if len(r["original_title"]) < 3), key=votes_of, reverse=True)
    lines += [
        "- Título más largo: "
        + ", ".join(f"{len(r[col])} caracteres en `{col}` (`{r['imdb_title_id']}`)" for col, r in longest.items())
        + ".",
        "- Largo de los títulos: "
        + "; ".join(
            f"`{col}`, promedio {dec(statistics.fmean(values))}, percentil 99 {fmt(percentile(values, 99))}, "
            f"{fmt(sum(1 for n in values if n > 100))} con más de 100 caracteres"
            for col, values in lengths.items()
        )
        + ".",
        f"- Títulos de menos de 3 caracteres: {fmt(len(short))}, entre ellos "
        f"{', '.join(quote(r['original_title']) for r in short[:8])}.",
        "",
    ]
    return lines


def section_dates(rows: list[Row]) -> list[str]:
    years = [year for r in rows if (year := parse_year(r["year"])) is not None]
    published = [(r, parse_date(r["date_published"])) for r in rows]
    full = [(r, d) for r, d in published if isinstance(d, date)]
    year_only = sum(1 for _, d in published if isinstance(d, int))
    mismatch = sum(1 for r, d in full if str(d.year) != r["year"])
    return [
        "## Año y fecha",
        "",
        f"- `year` válido: de {min(years, default='—')} a {max(years, default='—')}.",
        f"- `date_published`: {fmt(len(full))} fechas completas y {fmt(year_only)} con solo el año. "
        f"En {fmt(mismatch)} fechas completas el año no coincide con `year` (probablemente el estreno local).",
        "",
    ]


def section_numeric(rows: list[Row]) -> list[str]:
    lines = ["## Numéricos", "", "| Columna | Con valor | Mín. | Mediana | Máx. |", "|---|---:|---:|---:|---:|"]
    for col in NUMERIC_COLUMNS:
        parser = SCHEMA[col][1]
        values = [v for r in rows if (v := parser(r[col])) is not None]
        if not values:
            lines.append(f"| `{col}` | 0 | — | — | — |")
            continue
        show = dec if parser is parse_rating else fmt
        lines.append(
            f"| `{col}` | {fmt(len(values))} | {show(min(values))} | {show(statistics.median(values))} "
            f"| {show(max(values))} |"
        )
    return lines + [""]


def section_multi_value(rows: list[Row]) -> list[str]:
    lines = [
        "## Campos multivalor",
        "",
        "Valores separados por coma.",
        "",
        "| Columna | Valores distintos | Máx. por película | Filas con ítems repetidos | Más frecuentes |",
        "|---|---:|---:|---:|---|",
    ]
    counts: dict[str, Counter[str]] = {}
    example: tuple[str, Row] | None = None
    for col in LIST_COLUMNS:
        counts[col] = Counter()
        max_items = repeated_rows = 0
        for r in rows:
            items = parse_list(r[col]) if r[col].strip() else None
            if not items:
                continue
            counts[col].update(items)
            max_items = max(max_items, len(items))
            if len(set(items)) < len(items):
                repeated_rows += 1
                example = example or (col, r)
        top = ", ".join(cell(name) for name, _ in counts[col].most_common(3))
        lines.append(f"| `{col}` | {fmt(len(counts[col]))} | {max_items} | {fmt(repeated_rows)} | {top} |")
    lines.append("")
    if example:
        col, r = example
        lines.append(f"- Ejemplo de ítem repetido: `{r['imdb_title_id']}`, `{col}` = {quote(r[col])}.")
    comma_names = [(name, col) for col in LIST_COLUMNS for name in sorted(COMMA_NAMES) if counts[col][name]]
    if comma_names:
        lines.append(
            "- Nombres que contienen una coma: "
            + ", ".join(f"{quote(name)} ×{fmt(counts[col][name])} en `{col}`" for name, col in comma_names)
            + ". Partir solo por la coma inventaría valores falsos, como «Old»."
        )
    former = sorted(
        ((name, n) for name in FORMER_COUNTRIES if (n := counts["country"][name])), key=lambda item: (-item[1], item[0])
    )
    if former:
        lines.append(
            "- Países que ya no existen, disueltos o con otro nombre, y que un mapa actual no tiene: "
            + ", ".join(f"{name} ×{fmt(n)}" for name, n in former)
            + "."
        )
    genres = ", ".join(f"{name} ({fmt(n)})" for name, n in counts["genre"].most_common())
    return lines + [
        f"- Los {len(counts['genre'])} géneros: {genres}.",
        "",
    ]


def section_money(rows: list[Row]) -> list[str]:
    lines = [
        "## Montos",
        "",
        "| Columna | Con valor | Monedas | Más frecuentes | Máximo | Mayores que INT32 | En cero |",
        "|---|---:|---:|---|---|---:|---:|",
    ]
    pre_euro: set[str] = set()
    for col in MONEY_COLUMNS:
        parsed = [(r, money) for r in rows if (money := parse_money(r[col])) is not None]
        currencies = Counter(currency for _, (currency, _) in parsed)
        pre_euro |= currencies.keys() & PRE_EURO_CURRENCIES
        top = ", ".join(f"{c} ({fmt(n)})" for c, n in currencies.most_common(3))
        biggest = "—"
        if parsed:
            r, (currency, amount) = max(parsed, key=lambda item: item[1][1])
            biggest = f"{currency} {fmt(amount)} (`{r['imdb_title_id']}`)"
        over = sum(1 for _, (_, amount) in parsed if amount > INT32_MAX)
        zeros = sum(1 for _, (_, amount) in parsed if amount == 0)
        lines.append(
            f"| `{col}` | {fmt(len(parsed))} | {len(currencies)} | {top} | {biggest} | {fmt(over)} | {fmt(zeros)} |"
        )
    return lines + [
        "",
        f"- Monedas anteriores al euro: {', '.join(sorted(pre_euro)) or 'ninguna'}.",
        "- La recaudación mundial viene en la columna `worlwide_gross_income` (sic).",
        "",
    ]


def section_rating(rows: list[Row]) -> list[str]:
    rated: list[tuple[Row, float, int]] = []
    for r in rows:
        avg, votes = parse_rating(r["avg_vote"]), parse_int(r["votes"])
        if avg is not None and votes is not None:
            rated.append((r, avg, votes))
    if len(rated) < 2:
        return ["## Votos y rating ponderado", "", "Sin datos suficientes.", ""]
    votes_sorted = sorted(v for _, _, v in rated)
    c = statistics.fmean(a for _, a, _ in rated)
    m = percentile(votes_sorted, 90)

    def wr(avg: float, v: int) -> float:
        return v / (v + m) * avg + m / (v + m) * c

    def table(ranked: list[tuple[Row, float, int]]) -> list[str]:
        out = ["| # | Película | avg_vote | Votos | Ponderado |", "|---:|---|---:|---:|---:|"]
        for i, (r, a, v) in enumerate(ranked[:5], 1):
            out.append(f"| {i} | {movie(r)} | {dec(a)} | {fmt(v)} | {dec(wr(a, v), 2)} |")
        return out

    by_avg = sorted(rated, key=lambda x: (-x[1], -x[2]))
    by_wr = sorted(rated, key=lambda x: -wr(x[1], x[2]))
    raw_top = by_avg[0][0]
    raw_top_rank = next(i for i, (r, _, _) in enumerate(by_wr, 1) if r is raw_top)
    first_page = by_wr[:20]
    italian = sum(1 for r, _, _ in first_page if r["title"] != r["original_title"])
    under_500 = sum(1 for v in votes_sorted if v < 500)
    return [
        "## Votos y rating ponderado",
        "",
        f"- Votos: mínimo {fmt(votes_sorted[0])} (el dataset parece incluir solo películas con unos 100 votos o más); "
        f"percentiles 10 / 50 / 90 / 99: {' / '.join(fmt(percentile(votes_sorted, p)) for p in (10, 50, 90, 99))}.",
        f"- Películas con menos de 500 votos: {pct(under_500, len(votes_sorted))}.",
        f"- Fórmula estilo IMDb: WR = v/(v+m)·R + m/(v+m)·C, con C = {dec(c, 2)} (media global) "
        f"y m = {fmt(m)} (percentil 90 de votos).",
        "",
        "Top 5 por `avg_vote` crudo:",
        "",
        *table(by_avg),
        "",
        "Top 5 por rating ponderado:",
        "",
        *table(by_wr),
        "",
        f"- *{cell(raw_top['original_title'])}*, primera por `avg_vote` crudo, "
        f"queda en el puesto {fmt(raw_top_rank)} con el rating ponderado.",
        f"- De las {len(first_page)} primeras por rating ponderado, {italian} tienen un `title` (italiano) "
        "distinto de `original_title`.",
        "",
    ]


def section_text_quality(header: list[str], rows: list[Row]) -> list[str]:
    truncated = sum(1 for r in rows if r["description"].rstrip().endswith(("...", "…")))
    findings: list[str] = []
    clean: list[str] = []
    for col in TEXT_COLUMNS:
        found = False
        for issue, check in TEXT_ISSUES.items():
            hits = [r for r in rows if check(r[col])]
            if hits:
                found = True
                findings.append(
                    f"| `{col}` | {issue} | {fmt(len(hits))} | `{hits[0]['imdb_title_id']}`: "
                    f"{quote(snippet(hits[0][col], check))} |"
                )
        if not found:
            clean.append(col)
    formula = Counter(col for r in rows for col in header if r[col].startswith(FORMULA_PREFIXES))
    urls = sum(1 for r in rows for v in r.values() if "http" in v)
    damaged = [r for r in rows if any(check(r["description"]) for check in ENCODING_ISSUES.values())]
    mojibake = [r for r in rows if MOJIBAKE.search(r["description"])]
    reversible = sum(1 for r in mojibake if unmojibake(r["description"]) is not None)
    return [
        "## Calidad de texto",
        "",
        f"- Descripciones truncadas (terminan en «...»): {fmt(truncated)}.",
        "",
        "| Columna | Problema | Filas | Ejemplo |",
        "|---|---|---:|---|",
        *findings,
        "",
        "- Descripciones con algún problema de codificación (mojibake, U+FFFD o espacios no estándar): "
        f"{fmt(len(damaged))} distintas. El mojibake se revierte volviendo a codificar en Windows-1252 o "
        f"Latin-1 y decodificando como UTF-8 en {fmt(reversible)} de {fmt(len(mojibake))}.",
        f"- Sin ninguno de estos problemas: {', '.join(f'`{col}`' for col in clean)}.",
        "- Valores que empiezan con `=`, `+`, `-`, `@`, tabulación o retorno de carro "
        "(una planilla los ejecuta como fórmulas al abrir un CSV exportado): "
        + (", ".join(f"{n} en `{col}`" for col, n in formula.items()) or "ninguno")
        + ".",
        f"- Valores con URLs: {fmt(urls)} (no hay posters).",
        "",
    ]


# --- Entry point


def build_report(path: Path) -> str:
    header, rows, malformed = load(path)
    missing = [col for col in SCHEMA if col not in header]
    if missing:
        raise SystemExit(f"error: {path.name} is missing columns: {', '.join(missing)}")
    if not rows:
        raise SystemExit(f"error: {path.name} has no valid rows")
    source = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path.name
    lines = [
        "# Perfil del dataset",
        "",
        f"Generado con `python3 scripts/profile_dataset.py` sobre `{source}`. No editar a mano.",
        "",
    ]
    for section in (
        section_overview(path, header, rows, malformed),
        section_formats(header, rows),
        section_null_tokens(header, rows),
        section_keys(rows),
        section_titles(rows),
        section_dates(rows),
        section_numeric(rows),
        section_multi_value(rows),
        section_money(rows),
        section_rating(rows),
        section_text_quality(header, rows),
    ):
        lines += section
    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(build_report(args.csv.resolve()), encoding="utf-8")
    print(f"Report written to {args.out}")


if __name__ == "__main__":
    main()
