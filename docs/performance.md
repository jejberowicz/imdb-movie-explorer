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
