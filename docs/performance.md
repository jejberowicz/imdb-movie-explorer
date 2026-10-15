# Rendimiento

## Índices

Cada índice de la migración `0003_indexes` se justificó midiendo las consultas principales de la API con
`EXPLAIN ANALYZE`, antes y después de crearlo:
- con las 85.855 películas cargadas;
- en la notebook de desarrollo (Intel i7-1255U, WSL2) y PostgreSQL 18;
- tomando la mediana de 5 corridas.

Las consultas tienen la misma forma que las de la API: una página de 20 y el total con `count(*) OVER ()`.

| Consulta | Sin índices | Con índices | Plan con índices |
|---|---:|---:|---|
| Búsqueda selectiva (`shawshank`) | 20,0 ms | 0,1 ms | Bitmap Index Scan en los dos índices trigram |
| Búsqueda amplia (`the`, 13.956 resultados) | 23,8 ms | 10,9 ms | Bitmap Index Scan en los dos índices trigram |
| Búsqueda corta (`up`) | 19,0 ms | 15,5 ms | Seq Scan: con menos de 3 caracteres no hay trigramas |
| Lista por rating ponderado | 16,7 ms | 0,0 ms | Index Only Scan en `movies_weighted_rating` |
| Género (`Drama`), por rating | 41,9 ms | 26,3 ms | Bitmap Index Scan en `movies_genres` |
| País (`Russia` o `Soviet Union`), por rating | 22,3 ms | 1,6 ms | Bitmap Index Scan en `movies_countries` |

- **Las búsquedas de 1 o 2 caracteres recorren la tabla.** pg_trgm necesita al menos 3 para armar un
  trigrama. Tardan unos 15 ms, lo que es aceptable con este volumen
  ([ADR 0004](decisions/0004-title-search-requirements.md)).
- **En el filtro por Drama, lo que cuesta es contar.** Drama abarca 47.110 películas, y el total necesita
  recorrerlas todas.
- **Los cinco índices ocupan unos 17 MB:** 6 MB cada trigram, 3,4 MB el del rating y menos de 0,5 MB cada GIN de
  arrays.

Para repetir la medición, con la base cargada:

```bash
cd backend
DATABASE_URL=postgresql+psycopg://... .venv/bin/python scripts/explain_queries.py
```

## Latencia de punta a punta

`backend/scripts/measure_latency.py` mide los endpoints principales contra la API corriendo en Docker:
- 200 pedidos por endpoint, uno por vez, después de 10 de calentamiento;
- con Gunicorn (2 workers), la red de Docker y la serialización a JSON incluidas;
- en la misma notebook.

Mide cuánto tarda un pedido, no cuántos aguanta el servidor a la vez.

| Endpoint | p50 | p95 |
|---|---:|---:|
| Lista sin filtros (rating ponderado) | 4,8 ms | 5,9 ms |
| Búsqueda selectiva (`shawshank`) | 5,6 ms | 8,4 ms |
| Búsqueda popular (`godfather`) | 5,7 ms | 8,5 ms |
| Búsqueda amplia (`the`) | 24,3 ms | 39,0 ms |
| Búsqueda corta (`up`) | 25,4 ms | 32,4 ms |
| Género (`Drama`), por votos | 57,9 ms | 95,6 ms |
| País (`Russia` o `Soviet Union`) | 12,3 ms | 21,9 ms |
| Página 100 de la lista | 15,0 ms | 30,0 ms |
| Detalle (`tt0068646`) | 4,5 ms | 9,2 ms |
| Géneros | 4,2 ms | 8,1 ms |
| Países | 5,2 ms | 8,1 ms |

- **Todo queda por debajo de los 100 ms**, y casi todo por debajo de los 40 ms. Con el debounce de 300 ms del
  front, la búsqueda se siente inmediata.
- **El filtro por Drama es el más lento** por lo que ya mostraba `EXPLAIN`: contar 47.110 películas para el total.
- **Géneros y países se cuentan una vez por carga.** Antes recorrían las 85.855 películas en cada pedido: 38 ms
  de p50 cada uno. Ahora la API pregunta cuál es la última carga, que tarda menos de 1 ms, y si no cambió
  responde lo que ya contó. Una carga nueva se ve enseguida, sin reiniciar nada.
- **Entre corridas, los números varían** unos milisegundos: es una notebook con WSL2, no un servidor dedicado.

Para repetirlo, con el límite de pedidos subido (si no, el propio límite respondería 429):

```bash
RATE_LIMIT="100000 per minute" API_PORT=8000 docker compose up -d api
backend/.venv/bin/python backend/scripts/measure_latency.py http://127.0.0.1:8000
```

## Lo que no llega a la API

- **gzip en nginx:** el script principal del front pasa de 373 KB a 118 KB, y las respuestas JSON también viajan
  comprimidas.
- **Caché HTTP:** los archivos del build llevan un hash en el nombre y se cachean por un año (solo si existen:
  un 404 no se cachea); `index.html` se revalida en cada visita. `/genres` y `/countries` se pueden cachear una
  hora (`Cache-Control`).
- **El mapa se descarga aparte**, solo en la página por país: el resto del sitio no paga sus 67 KB.

