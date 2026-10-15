# Cómo trabajar en el proyecto

## Convenciones

- **Idiomas:** el código, los nombres y los comentarios del código van en inglés. El README, los documentos, los
  ADR y la interfaz van en español (es-AR).
- **Commits:** siguen Conventional Commits. El tipo va en inglés (`feat`, `fix`, `docs`, `test`, `refactor`,
  `perf`, `build`, `ci`, `chore`); la descripción y el cuerpo, en español. Son commits chicos, con los tests
  corridos antes de cada uno.
- **Ramas:** una por fase (`phase-1/walking-skeleton`, `phase-2/robust-data`…), que entra a `main` al cerrarla.
- **Decisiones:** cada decisión no trivial tiene un ADR en [docs/decisions](docs/decisions/README.md).
- **Secretos:** solo por variables de entorno. `.env` nunca se commitea; `.env.example` documenta las variables
  sin valores reales.

## Backend (`backend/`)

Python 3.12. Los tests corren contra un PostgreSQL real, porque la búsqueda depende de sus funciones.

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt

# Un PostgreSQL para desarrollo, con una base aparte para los tests
docker run -d --name imdb-dev-db -e POSTGRES_USER=movies -e POSTGRES_PASSWORD=movies \
  -e POSTGRES_DB=movies -p 127.0.0.1:5433:5432 postgres:18.6-trixie
docker exec imdb-dev-db psql -U movies -c "CREATE DATABASE movies_test"

# Migraciones, carga del CSV y servidor de desarrollo
export DATABASE_URL=postgresql+psycopg://movies:movies@localhost:5433/movies
.venv/bin/alembic upgrade head
.venv/bin/flask --app app seed ../data/IMDb_movies.csv.gz
.venv/bin/flask --app app run --port 8000

# Tests y estilo
TEST_DATABASE_URL=postgresql+psycopg://movies:movies@localhost:5433/movies_test .venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

## Frontend (`frontend/`)

Node 24.

```bash
cd frontend
npm ci
npm run dev        # http://localhost:5173; /api va a la API en localhost:8000
npm test           # Vitest, React Testing Library y MSW
npm run lint       # oxlint
npm run typecheck  # tsc
npm run build
```

## Datos

- **El CSV** está en `data/IMDb_movies.csv.gz`. Descomprimido, su SHA-256 es
  `66032d99cae8414dd8695bc5265a46cfa18e1ff092d130f243d93179dee07db4`.
- **El perfil del dataset** se regenera con `python3 scripts/profile_dataset.py`, y tiene que quedar idéntico.
