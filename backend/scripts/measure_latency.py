"""Measure p50 and p95 of the main endpoints of a running API and print them as a Markdown table.

Each request goes one after the other, from a single client: it measures how long one request takes, not how
many the server can take at once. Run it with the rate limit raised, or the limit itself would answer 429:

    RATE_LIMIT="100000 per minute" docker compose up -d api
    python scripts/measure_latency.py http://127.0.0.1:8000
"""

import statistics
import sys
import time
import urllib.error
import urllib.request

RUNS = 200
WARMUP = 10
ENDPOINTS = {
    "Lista sin filtros (rating ponderado)": "/movies",
    "Búsqueda selectiva (`shawshank`)": "/movies?title=shawshank",
    "Búsqueda popular (`godfather`)": "/movies?title=godfather",
    "Búsqueda amplia (`the`)": "/movies?title=the",
    "Búsqueda corta (`up`)": "/movies?title=up",
    "Género (`Drama`), por votos": "/movies?genre=Drama&sort=votes",
    "País (`Russia` o `Soviet Union`)": "/movies?country=Russia&country=Soviet%20Union",
    "Página 100 de la lista": "/movies?page=100",
    "Detalle (`tt0068646`)": "/movies/tt0068646",
    "Géneros": "/genres",
    "Países": "/countries",
}


def timed_get(url: str) -> float:
    start = time.perf_counter()
    with urllib.request.urlopen(url, timeout=10) as response:  # noqa: S310 (a URL given by whoever runs this)
        response.read()
    return (time.perf_counter() - start) * 1000


def main(base: str) -> int:
    if not base.startswith(("http://", "https://")):
        print("Usage: measure_latency.py http://host:port", file=sys.stderr)
        return 2
    print(f"{RUNS} pedidos por endpoint, uno por vez, después de {WARMUP} de calentamiento.\n")
    print("| Endpoint | p50 | p95 |")
    print("|---|---:|---:|")
    for name, path in ENDPOINTS.items():
        try:
            for _ in range(WARMUP):
                timed_get(base + path)
            times = [timed_get(base + path) for _ in range(RUNS)]
        except urllib.error.HTTPError as error:
            print(f"\n{path} answered {error.code}. Is the rate limit raised?", file=sys.stderr)
            return 1
        cuts = statistics.quantiles(times, n=100)
        print(f"| {name} | {cuts[49]:.1f} ms | {cuts[94]:.1f} ms |".replace(".", ","))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"))
