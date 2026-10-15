"""Run the main queries of the API with EXPLAIN ANALYZE and print their plans and times as a Markdown table.

Used to justify each index: run it before and after the migration that adds them, against the full data.

    DATABASE_URL=postgresql+psycopg://... python scripts/explain_queries.py
"""

import json
import os
import statistics

from sqlalchemy import create_engine, text

RUNS = 5
# The same shape as the API queries: a page of 20 plus the total with count(*) OVER ().
QUERIES = {
    "Búsqueda selectiva (`shawshank`)": (
        "SELECT imdb_title_id, count(*) OVER () FROM movies "
        "WHERE original_title_search LIKE '%shawshank%' OR italian_title_search LIKE '%shawshank%' "
        "ORDER BY votes DESC, imdb_title_id LIMIT 20"
    ),
    "Búsqueda amplia (`the`, 13.956 resultados)": (
        "SELECT imdb_title_id, count(*) OVER () FROM movies "
        "WHERE original_title_search LIKE '%the%' OR italian_title_search LIKE '%the%' "
        "ORDER BY votes DESC, imdb_title_id LIMIT 20"
    ),
    "Búsqueda corta (`up`)": (
        "SELECT imdb_title_id, count(*) OVER () FROM movies "
        "WHERE original_title_search LIKE '%up%' OR italian_title_search LIKE '%up%' "
        "ORDER BY votes DESC, imdb_title_id LIMIT 20"
    ),
    "Lista por rating ponderado": (
        "SELECT imdb_title_id FROM movies ORDER BY weighted_rating DESC, imdb_title_id LIMIT 20"
    ),
    "Género (`Drama`), por rating": (
        "SELECT imdb_title_id, count(*) OVER () FROM movies WHERE genres @> ARRAY['Drama'] "
        "ORDER BY weighted_rating DESC, imdb_title_id LIMIT 20"
    ),
    "País (`Russia` o `Soviet Union`), por rating": (
        "SELECT imdb_title_id, count(*) OVER () FROM movies WHERE countries && ARRAY['Russia', 'Soviet Union'] "
        "ORDER BY weighted_rating DESC, imdb_title_id LIMIT 20"
    ),
}


def scans(plan: dict) -> list[str]:
    """The scan nodes of a plan: they show whether an index is used."""
    found = []
    if "Scan" in plan["Node Type"]:
        found.append(f"{plan['Node Type']}" + (f" ({plan['Index Name']})" if "Index Name" in plan else ""))
    for child in plan.get("Plans", []):
        found += scans(child)
    return found


def main() -> None:
    engine = create_engine(os.environ["DATABASE_URL"])
    print("| Consulta | Plan | Tiempo (ms) |\n|---|---|---:|")
    with engine.connect() as conn:
        for label, sql in QUERIES.items():
            times, plan = [], {}
            for _ in range(RUNS):
                result = conn.execute(text(f"EXPLAIN (ANALYZE, FORMAT JSON) {sql}")).scalar_one()
                plan = (json.loads(result) if isinstance(result, str) else result)[0]
                times.append(plan["Execution Time"])
            nodes = ", ".join(dict.fromkeys(scans(plan["Plan"])))
            median = f"{statistics.median(times):.1f}".replace(".", ",")
            print(f"| {label} | {nodes} | {median} |")


if __name__ == "__main__":
    main()
