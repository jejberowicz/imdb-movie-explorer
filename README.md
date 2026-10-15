# FakeIMDb: explorador de películas de IMDb

Una API REST en Flask y una interfaz en React para explorar y buscar las 85.855 películas del CSV de IMDb.
Se busca por título mientras se escribe, en el título original o en el italiano, sin importar mayúsculas ni
acentos. También se puede filtrar por uno o varios géneros, décadas (o un año) y países (con un mapa), ordenar
y ver el detalle de cada película. Los datos viven en PostgreSQL, y todo se levanta con un solo comando.

![La pantalla de explorar: barra «Explorar por», búsqueda y pósters generados](docs/screenshots/explorar.png)

<table>
  <tr>
    <td><img src="docs/screenshots/busqueda.png" alt="Búsqueda de «padrino»: encuentra The Godfather por su título italiano"></td>
    <td><img src="docs/screenshots/tabla.png" alt="Vista tabla con policiales de los 90"></td>
  </tr>
  <tr>
    <td><img src="docs/screenshots/detalle.png" alt="Detalle de The Godfather"></td>
    <td><img src="docs/screenshots/por-pais.png" alt="Mapa por país: Rusia suma las películas de la Unión Soviética"></td>
  </tr>
</table>

## Cómo levantarlo

Hace falta Docker con Docker Compose.

```bash
git clone https://github.com/jejberowicz/imdb-movie-explorer.git
cd imdb-movie-explorer
docker compose up --build
```

La primera vez se construyen las imágenes y se cargan las películas en PostgreSQL. Tarda un par de minutos,
casi todo en la construcción. Cuando `web` aparece como listo:

| Qué | Dónde |
|---|---|
| La aplicación | http://localhost:8080 |
| La API | http://localhost:8000/movies |
| La documentación de la API (Swagger UI) | http://localhost:8000/docs/swagger |
| El esquema OpenAPI | http://localhost:8000/docs/openapi.json |

- **Si los puertos 8000 u 8080 están ocupados**, se cambian al levantar:
  `API_PORT=8001 WEB_PORT=8081 docker compose up --build`.
- **Para empezar de cero**, borrando la base: `docker compose down -v`.
- **La API se publica solo en `127.0.0.1`.** El navegador no la usa directamente: entra por nginx, en
  `http://localhost:8080/api`, en el mismo origen que la app.

El orden de arranque es `db` → `seed` → `api` → `web`, y cada servicio espera a que el anterior esté sano:
- `seed` aplica las migraciones y carga el CSV, y después termina;
- si ese mismo archivo ya estaba cargado, según su SHA-256, termina sin hacer nada.

### Variables de entorno

Todas tienen un valor por defecto, para que `docker compose up` funcione sin configurar nada. Para cambiarlas,
copiá `.env.example` a `.env`, que no se commitea.

| Variable | Por defecto | Para qué |
|---|---|---|
| `POSTGRES_PASSWORD` | `postgres-local-only` | Contraseña del superusuario. Solo sirve para administrar desde adentro del contenedor: por la red no puede entrar |
| `MOVIES_DB_PASSWORD` | `movies-local-only` | Contraseña del dueño de la base, que corre las migraciones y la carga y no es superusuario |
| `API_DB_PASSWORD` | `api-local-only` | Contraseña de `movies_api`, el usuario de solo lectura de la API |
| `API_PORT`, `WEB_PORT` | `8000`, `8080` | Puertos publicados en esta máquina |
| `GUNICORN_WORKERS` | `2` | Procesos de la API |
| `RATE_LIMIT` | `300 per minute` | Pedidos permitidos por IP, sumando todas las rutas. Un valor inválido no deja arrancar la API |

Las contraseñas se aplican cuando se crea la base: para cambiarlas después, primero `docker compose down -v`.
La base no se publica: está en una red interna de Docker que solo comparten la carga y la API, así que ni nginx
llega a ella.

### Sin Docker

Hace falta Python 3.12, Node 24 y PostgreSQL 16 o más nuevo, con la extensión `pg_trgm` (viene en el
paquete *contrib*). Se probó con PostgreSQL 18.

```bash
# Una base y un usuario dueño
createuser --pwprompt movies          # contraseña: movies
createdb --owner movies movies

# Backend: migraciones, carga del CSV y la API en http://localhost:8000
cd backend
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://movies:movies@localhost:5432/movies
.venv/bin/alembic upgrade head        # también crea la extensión pg_trgm
.venv/bin/flask --app app seed ../data/IMDb_movies.csv.gz
.venv/bin/flask --app app run --port 8000

# Front, en otra terminal: http://localhost:5173, con /api apuntando a la API
cd frontend
npm ci
npm run dev
```

Así la API usa el usuario dueño. Los usuarios separados (dueño sin superusuario y API de solo lectura) los crea
`db/init/01-roles.sh` en Docker.

## La API

| Endpoint | Qué devuelve |
|---|---|
| `GET /movies` | Una página de películas. Filtra con `title`, `genre`, `country` y `decade` (repetibles), `year_from`, `year_to` y `min_votes`; ordena con `sort` (`relevance`, `rating`, `year`, `votes`, `duration`, `title`) y `order` (`asc`, `desc`); pagina con `page` y `page_size` (hasta 100) |
| `GET /movies/{imdb_title_id}` | El detalle completo de una película |
| `GET /genres` | Los 25 géneros, con su cantidad de películas |
| `GET /countries` | Los 194 países del CSV, con su cantidad de películas y el código ISO donde los pinta el mapa |
| `GET /years` | Los años con películas, con su cantidad |
| `GET /health`, `GET /health/ready` | Si el proceso responde; si además la base responde y tiene las películas cargadas |

```bash
# La primera página: las mejor valoradas
curl "http://localhost:8000/movies"

# Buscar por título, en el original y en el italiano: el `title` de Relatos salvajes es «Storie Pazzesche»
curl "http://localhost:8000/movies?title=relatos%20salvajes"

# Sin acentos, y paginando
curl "http://localhost:8000/movies?title=amelie&page=1&page_size=5"

# Filtros y orden: los dramas de los 90 más votados
curl "http://localhost:8000/movies?genre=Drama&year_from=1990&year_to=1999&sort=votes"

# Varios países a la vez: Rusia y la Unión Soviética
curl "http://localhost:8000/movies?country=Russia&country=Soviet%20Union"

# El detalle de una película
curl "http://localhost:8000/movies/tt0068646"

# Un error: page_size fuera de rango y un sort que no está en la lista blanca
curl "http://localhost:8000/movies?page_size=100000&sort=title;DROP%20TABLE%20movies"
```

Las respuestas de `GET /movies` traen `items`, `page`, `page_size`, `total` y `total_pages`. Los errores
siguen el formato Problem Details (RFC 9457): 400 con cada parámetro inválido y su motivo, 404 si la
película no existe, 429 si se pasa el límite de pedidos (de la API, o el más grueso de nginx) y 503 si la base no
responde. Nunca devuelven un stack trace.

- **Referencia completa**, con ejemplos de cada respuesta: [docs/api.md](docs/api.md).
- **Swagger UI**, para probarla desde el navegador: http://localhost:8000/docs/swagger.
- **Colección de Postman**, con 16 pedidos y un test por cada uno:
  [docs/postman](docs/postman/imdb-movie-explorer.postman_collection.json). Se importa en Postman, o se corre
  con `npx newman run docs/postman/imdb-movie-explorer.postman_collection.json`.

## Tests

```bash
# Backend: 202 tests contra un PostgreSQL real, incluidos los criterios de aceptación sobre el CSV completo
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
docker run -d --name imdb-dev-db -e POSTGRES_USER=movies -e POSTGRES_PASSWORD=movies \
  -e POSTGRES_DB=movies -p 127.0.0.1:5433:5432 postgres:18.6-trixie
docker exec imdb-dev-db psql -U movies -c "CREATE DATABASE movies_test"
TEST_DATABASE_URL=postgresql+psycopg://movies:movies@localhost:5433/movies_test .venv/bin/pytest

# Front: 76 tests con Vitest, React Testing Library y MSW
cd frontend
npm ci
npm test
```

- **Los tests del backend usan una base de verdad**, porque la búsqueda depende de pg_trgm y del orden de
  PostgreSQL. Cada corrida borra y recrea el esquema de `TEST_DATABASE_URL`, así que tiene que ser una base
  descartable. `pytest -m "not acceptance"` deja afuera los que cargan las 85.855 películas.
- **Los del front simulan la API con MSW**, sobre 8 películas reales. Cubren la búsqueda con debounce, que una
  respuesta lenta vieja nunca pise a una nueva, los resultados que quedan en pantalla mientras carga la
  página siguiente, los estados vacío y de error, los menús con teclado, el estado en la URL, la tabla, el
  detalle y el mapa.
- **El CI** ([.github/workflows/ci.yml](.github/workflows/ci.yml)) corre en cada push:
  - estilo (ruff y oxlint), tipos, los tests de los dos lados y la auditoría de dependencias (`pip-audit` y
    `npm audit`);
  - `docker compose up` desde una base vacía, con un smoke test a través de nginx.

## Arquitectura

```mermaid
flowchart LR
    browser([Navegador]) -->|":8080"| web
    subgraph compose["docker compose"]
        web["web<br/>nginx: la app compilada<br/>y proxy de /api"]
        api["api<br/>Flask + Gunicorn"]
        seed["seed<br/>migraciones + carga<br/>(corre una vez)"]
        db[("db<br/>PostgreSQL 18 + pg_trgm")]
        web -->|"/api/movies → /movies"| api
        api -->|"usuario de solo lectura"| db
        seed -->|"COPY, usuario dueño"| db
    end
    csv[/"data/IMDb_movies.csv.gz"/] --> seed
```

- **Backend:** Flask 3 con flask-openapi3 (Pydantic valida la entrada y genera el OpenAPI), en tres capas finas:
  - rutas;
  - servicios;
  - repositorios, con SQL parametrizado en SQLAlchemy Core.
  
  Alembic maneja las migraciones, y la carga es un comando del mismo paquete (`flask seed`).
- **Base:** PostgreSQL 18. La búsqueda usa `LIKE '%…%'` sobre los títulos plegados (en minúsculas y sin
  acentos), con índices trigram. Una búsqueda selectiva tarda 0,1 ms en la base y unos 6 ms de punta a punta
  ([docs/performance.md](docs/performance.md)).
- **Front:** React 19 con TypeScript, Vite y TanStack Query, que cancela los pedidos viejos y mantiene los
  resultados anteriores mientras llegan los nuevos. React Router guarda todo el estado en la URL. El mapa usa
  d3-geo con las formas de Natural Earth.
- **Detalle:** [docs/architecture.md](docs/architecture.md), con el modelo de datos, los índices y la carga
  paso a paso.

## Hallazgos en los datos

El CSV se perfiló antes de escribir código, con un script reproducible
([docs/data-profile.md](docs/data-profile.md)). Lo más importante:

- **La columna `title` es el título en Italia**, no el original ni uno en español: el CSV viene de la versión
  italiana de IMDb. Por eso la interfaz muestra `original_title`, y la búsqueda mira las dos columnas:
  «padrino» encuentra *The Godfather*.
- **`date_published` es la fecha de estreno en Italia.** Lo comprobé contra Wikidata: coincide en el 94 % de
  las películas italianas y en muy pocas de otros países. No se carga ni se muestra.
- **Los enteros vienen como decimales** («57.0»): 165.621 valores se convierten sin perder nada.
- **Los montos vienen en 79 monedas**, y el dólar con «$», que en Argentina se lee como pesos: 62.866 se
  guardan como `USD`. Cada monto se muestra en su moneda, sin convertirlo.
- **Hay listas con nombres repetidos:** 6.471 filas, porque IMDb acredita a una persona una vez por rol y el
  CSV perdió el rol. En *Goodfellas*, los guionistas dicen «Nicholas Pileggi, Nicholas Pileggi». Además, 14
  idiomas contienen una coma, como «Greek, Ancient (to 1453)», y no se parten.
- **«None» en `language` significa sin diálogos:** 68 películas, 12 de ellas anteriores a 1930, la época del
  cine mudo. Se muestra «Sin diálogos».
- **13 países ya no existen** (la Unión Soviética, Yugoslavia, Alemania Occidental...). En el mapa se pintan
  sobre su sucesor, y en la lista quedan con su nombre.
- **9 descripciones tienen mojibake**, texto leído con otra codificación («fiancÃ©»). Las 7 que se pueden
  revertir de forma exacta se reparan.
- **Un año viene como «TV Movie 2019»**: se extrae el año.

La carga aplica estas reglas y registra cada corrección: de las 85.855 filas, ninguna se rechaza
([ADR 0003](docs/decisions/0003-data-cleaning-rules.md)).

## Decisiones

Cada decisión no trivial tiene un ADR corto, con el contexto, las opciones, la decisión y sus consecuencias
([índice](docs/decisions/README.md)):

| ADR | Decisión |
|---|---|
| [0001](docs/decisions/0001-reproducible-dataset-profiling.md) | Perfilar el CSV con un script reproducible antes de escribir código |
| [0002](docs/decisions/0002-display-title-and-ui-language.md) | Mostrar el título original; la interfaz en español |
| [0003](docs/decisions/0003-data-cleaning-rules.md) | Las reglas de limpieza: qué se corrige, qué se rechaza y qué queda como está |
| [0004](docs/decisions/0004-title-search-requirements.md) | La búsqueda: las dos columnas, sin acentos, comodines literales y orden por relevancia |
| [0005](docs/decisions/0005-data-storage.md) | PostgreSQL, comparado con pandas y SQLite con mediciones |
| [0006](docs/decisions/0006-csv-versioning.md) | El CSV en el repo, comprimido con gzip |
| [0007](docs/decisions/0007-api-contract.md) | El contrato de la API: paginación, errores 400 con Problem Details, OpenAPI |
| [0008](docs/decisions/0008-default-order.md) | El orden por defecto: rating ponderado, como el top de IMDb |
| [0009](docs/decisions/0009-browse-by-country.md) | Explorar por país, con los países que ya no existen sobre su sucesor |
| [0010](docs/decisions/0010-generated-posters.md) | Pósters generados con los datos de cada película, porque el CSV no trae imágenes |

La seguridad sigue un modelo de amenazas proporcional a un catálogo público de solo lectura:
[SECURITY.md](SECURITY.md).

## Supuestos

La consigna deja puntos abiertos; cada uno tiene un supuesto explícito en
[docs/assumptions.md](docs/assumptions.md). Los que más afectan al uso:

- **`GET /movies` pagina:** 20 películas por defecto y hasta 100, con el total. Devolver las 85.855 de una vez
  serían decenas de MB.
- **«Filtrar por título»** es una coincidencia parcial, sin mayúsculas ni acentos, en el título original y en
  el italiano. No hay títulos en español: el CSV no los trae.
- **La búsqueda en tiempo real consulta la API** 300 ms después de la última tecla, en vez de filtrar en el
  navegador, que obligaría a descargar todo el catálogo.
- **Sin búsqueda, el orden es por rating ponderado.** Por `avg_vote`, la primera sería *Suvarna Sundari*,
  con 9,9 y 896 votos; así, arriba quedan *The Shawshank Redemption* y *The Godfather*.
- **No hay login:** es un catálogo público de solo lectura.

## Limitaciones conocidas

- **Directores y guionistas:** el CSV trae como mucho dos nombres por película. Por ejemplo, en *Goodfellas*
  falta Martin Scorsese como coguionista.
- **Búsquedas de 1 o 2 letras:** no usan el índice, porque pg_trgm necesita al menos 3. Tardan unos 25 ms,
  aceptable con este volumen.
- **El límite de pedidos se cuenta por worker**, en memoria. Con varias máquinas, iría en Redis.
- **Sin TLS en local.** En un despliegue real, iría en el proxy reverso.
- **Las descripciones, los países en el detalle y los idiomas** vienen en inglés en el CSV. Los países se
  traducen; las descripciones y los idiomas, no.

## Qué haría con más tiempo

- **Portadas reales** desde la API de TMDB, con la clave solo en el backend y el póster generado como respaldo.
- **Títulos en español** desde `title.akas` de IMDb, para buscar también «El padrino».
- **Traducir las descripciones** y los idiomas al español, o al idioma que elija cada usuario.
- **Tolerancia a errores de tipeo** con la similitud de pg_trgm: «godfahter» encontraría *The Godfather*.
- **Filtros como chips** que se quitan de a uno, el filtro por votos mínimos en la interfaz (la API ya lo
  tiene) y resaltar el texto buscado.
- **Tests de punta a punta** con Playwright, y un escaneo con OWASP ZAP.
- **Un despliegue con URL pública.**

**Fuera de alcance:** login y usuarios, alta, baja y modificación de películas, microservicios, colas y
Kubernetes. No hay datos privados ni escrituras que los justifiquen.

## Sobre los datos

El CSV es el que vino con el desafío: 85.855 películas de IMDb hasta 2020. Está en
`data/IMDb_movies.csv.gz`, comprimido para que entre en el repo
([ADR 0006](docs/decisions/0006-csv-versioning.md)). Se incluye solo para correr el desafío, sin fines
comerciales; los datos son de IMDb. Para comprobar que es el mismo archivo, byte a byte:

```bash
gunzip -c data/IMDb_movies.csv.gz | sha256sum
# 66032d99cae8414dd8695bc5265a46cfa18e1ff092d130f243d93179dee07db4
```

El mapa usa [Natural Earth](https://www.naturalearthdata.com/), de dominio público. FakeIMDb no está
relacionado con IMDb.

## Más documentación

- [Cómo trabajar en el proyecto](CONTRIBUTING.md): convenciones, comandos y scripts.
- [Interfaz](docs/ui.md), [plan de tests](docs/test-plan.md), [rendimiento](docs/performance.md) y
  [backlog](docs/backlog.md).
