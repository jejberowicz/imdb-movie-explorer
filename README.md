# FakeIMDb: explorador de películas de IMDb

API REST en Flask y front en React para explorar y buscar las 85.855 películas del CSV de IMDb.

## Cómo levantarlo

Hace falta Docker con Docker Compose.

```bash
docker compose up --build
```

| Qué | Dónde |
|---|---|
| El front | http://localhost:8080 |
| La API | http://localhost:8000/movies |
| La documentación de la API (Swagger) | http://localhost:8000/docs/swagger |

- **La primera vez** se construyen las imágenes y se carga el CSV en PostgreSQL, en unos segundos.
- **Si los puertos 8000 u 8080 están ocupados**, se pueden cambiar:
  `API_PORT=8001 WEB_PORT=8081 docker compose up --build`.

## Ejemplos con curl

```bash
curl "http://localhost:8000/movies"
curl "http://localhost:8000/movies?title=relatos%20salvajes"
curl "http://localhost:8000/movies?title=godfather&page=1&page_size=5"
```

## Documentación

- [Contrato de la API](docs/api.md)
- [Arquitectura y modelo de datos](docs/architecture.md)
- [Decisiones (ADR)](docs/decisions/README.md)
- [Perfil del dataset](docs/data-profile.md)
- [Cómo trabajar en el proyecto](CONTRIBUTING.md)
