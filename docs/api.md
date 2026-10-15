# Contrato de la API

Las decisiones de forma están en el [ADR 0007](decisions/0007-api-contract.md). Esta es la referencia: qué
recibe y qué devuelve cada endpoint. La API publica la misma información como OpenAPI en `/docs/openapi.json`,
con Swagger UI en `/docs/swagger`.

## Convenciones

- **URL base:** `http://localhost:8000`, directo a la API. Desde el front, `http://localhost:8080/api`.
- **Formato:** JSON en UTF-8, con nombres de campo en snake_case.
- **Datos que faltan:** `null`, nunca un texto como «N/A». La interfaz decide cómo mostrarlos
  ([ADR 0003](decisions/0003-data-cleaning-rules.md)).
- **Montos:** van como `{"amount": 25000000, "currency": "USD"}`, con el código ISO 4217 de la moneda.
- **Errores:** usan `application/problem+json` (RFC 9457), con los textos en inglés.

## `GET /movies`

Devuelve una página de películas. Con `title`, filtra por título.

| Parámetro | Tipo | Por defecto | Reglas |
|---|---|---|---|
| `title` | texto | — | Hasta 200 caracteres. Se recortan los espacios de los extremos y los repetidos. Vacío equivale a no filtrar |
| `page` | entero | 1 | 1 o más |
| `page_size` | entero | 20 | Entre 1 y 100 |
| `sort` | `relevance`, `rating`, `year`, `votes`, `duration`, `title` | `relevance` si hay `title`; si no, `rating` | `relevance` solo vale con `title`. `rating` es el rating ponderado |
| `order` | `asc`, `desc` | `asc` para `title`; `desc` para el resto | `relevance` siempre es de mayor a menor |
| `genre` | texto | — | Un género de `GET /genres`, en inglés, como en los datos; hasta 40 caracteres. Uno que no existe devuelve una lista vacía |
| `country` | texto, repetible | — | Un país de `GET /countries`, como en los datos; hasta 20 valores. Con varios, devuelve las películas de cualquiera de ellos |
| `year_from`, `year_to` | entero | — | Entre 1880 y 2100, con `year_from` menor o igual que `year_to` |
| `min_votes` | entero | — | 0 o más |

- **Búsqueda** ([ADR 0004](decisions/0004-title-search-requirements.md)):
  - busca el texto en cualquier parte del título original o del italiano;
  - no distingue mayúsculas ni acentos;
  - toma `%` y `_` como caracteres literales.
- **Relevancia:** primero los títulos iguales al texto buscado, después los que empiezan con él y al final el
  resto; dentro de cada grupo, de más a menos votos.
- **Desempates:** todo orden termina en `imdb_title_id`, así la paginación es estable.
- **Parámetros desconocidos:** se ignoran.

`GET /movies?title=shawshank`:

```json
{
  "items": [
    {
      "imdb_title_id": "tt0111161",
      "original_title": "The Shawshank Redemption",
      "year": 1994,
      "genres": ["Drama"],
      "directors": ["Frank Darabont"],
      "duration": 142,
      "avg_vote": 9.3,
      "votes": 2278845,
      "weighted_rating": 9.29
    }
  ],
  "page": 1,
  "page_size": 20,
  "total": 1,
  "total_pages": 1
}
```

Sin parámetros, `total` es 85855 y `total_pages` es 4293. Una página más allá de la última devuelve `items`
vacío con el total correcto.

## `GET /movies/{imdb_title_id}`

Devuelve el detalle completo de una película. El id tiene que ser `tt` seguido de 7 u 8 dígitos.

`GET /movies/tt0111161`:

```json
{
  "imdb_title_id": "tt0111161",
  "original_title": "The Shawshank Redemption",
  "italian_title": "Le ali della libertà",
  "year": 1994,
  "genres": ["Drama"],
  "duration": 142,
  "countries": ["USA"],
  "languages": ["English"],
  "directors": ["Frank Darabont"],
  "writers": ["Stephen King", "Frank Darabont"],
  "production_company": "Castle Rock Entertainment",
  "actors": ["Tim Robbins", "Morgan Freeman", "Bob Gunton", "William Sadler", "Clancy Brown", "Gil Bellows",
             "Mark Rolston", "James Whitmore", "Jeffrey DeMunn", "Larry Brandenburg", "Neil Giunto"],
  "description": "Two imprisoned men bond over a number of years, finding solace and eventual redemption through acts of common decency.",
  "avg_vote": 9.3,
  "votes": 2278845,
  "weighted_rating": 9.29,
  "metascore": 80,
  "reviews_from_users": 8232,
  "reviews_from_critics": 164,
  "budget": {"amount": 25000000, "currency": "USD"},
  "usa_gross_income": {"amount": 28699976, "currency": "USD"},
  "worldwide_gross_income": {"amount": 28815245, "currency": "USD"},
  "imdb_url": "https://www.imdb.com/title/tt0111161/"
}
```

- `italian_title` es la columna `title` del CSV.
- `worldwide_gross_income` corrige el nombre de la columna del CSV, `worlwide_gross_income`.
- En `languages`, «None» indica una película sin diálogos ([ADR 0003](decisions/0003-data-cleaning-rules.md),
  regla 7).

## `GET /genres`

Devuelve los géneros con la cantidad de películas de cada uno, de más a menos. Sirve para armar los filtros.
La respuesta se puede cachear: incluye `Cache-Control: public, max-age=3600`.

```json
{"items": [{"name": "Drama", "movies": 47110}, {"name": "Comedy", "movies": 29368}]}
```

El ejemplo está recortado: son 25 géneros.

## `GET /countries`

Devuelve cada país tal como viene en el CSV, con su cantidad de películas y el código ISO del país del mapa
donde se pinta ([ADR 0009](decisions/0009-browse-by-country.md)). `former` indica los países que ya no existen.
Se puede cachear, igual que `/genres`.

```json
{"items": [
  {"name": "USA", "movies": 34325, "map_code": "US", "former": false},
  {"name": "Soviet Union", "movies": 866, "map_code": "RU", "former": true}
]}
```

El ejemplo está recortado: son 194 países.

## `GET /health` y `GET /health/ready`

- `/health` confirma que el proceso responde, sin tocar la base: `{"status": "ok"}`.
- `/health/ready` confirma que la base responde y que hay una carga completa:
  `{"status": "ready", "movies": 85855}`. Si no, devuelve 503 con un Problem Details. Docker lo usa como
  healthcheck de la API.

## Errores

| Código | Cuándo |
|---|---|
| 400 | Un parámetro inválido: `page=0`, `page_size=100000`, un `sort` fuera de la lista, un id con otro formato… |
| 404 | El id tiene un formato válido, pero no existe |
| 429 | Demasiados pedidos (Fase 5). Incluye `Retry-After` |
| 500 | Un error inesperado. El detalle queda en el log, nunca en la respuesta |
| 503 | La base no responde o todavía no hay datos cargados |

`GET /movies?page_size=100000&sort=title;DROP TABLE movies`:

```json
{
  "type": "about:blank",
  "title": "Bad Request",
  "status": 400,
  "detail": "Invalid query parameters.",
  "errors": [
    {"parameter": "page_size", "detail": "Must be between 1 and 100."},
    {"parameter": "sort", "detail": "Must be one of: relevance, rating, year, votes, duration, title."}
  ]
}
```

`GET /movies/tt9999999`:

```json
{"type": "about:blank", "title": "Not Found", "status": 404, "detail": "Movie tt9999999 not found."}
```

## Ejemplos con curl

```bash
curl "http://localhost:8000/movies"
curl "http://localhost:8000/movies?title=relatos%20salvajes"
curl "http://localhost:8000/movies?genre=Drama&year_from=1990&year_to=1999&sort=votes"
curl "http://localhost:8000/movies/tt0068646"
curl "http://localhost:8000/genres"
curl "http://localhost:8000/movies?country=Russia&country=Soviet%20Union"
```
