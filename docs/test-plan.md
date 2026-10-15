# Plan de tests

Qué se prueba, con qué y contra qué. Los tests se corren antes de cada commit desde la Fase 1, y en CI desde
la Fase 5.

## Backend (pytest)

### Unitarios: las funciones puras, sin base

Cada regla del [ADR 0003](decisions/0003-data-cleaning-rules.md) es una función pura, con sus casos borde:

| Función | Casos |
|---|---|
| Año | `2019` → 2019; `TV Movie 2019` → 2019 con warning; `1999 2001`, `abc` y `1850` → rechazo |
| Enteros | `57.0` → 57; `57.5` → inválido; vacío → `None` |
| Montos | `$ 25000000` → (USD, 25000000); `IRR 350000000000` entra en BIGINT; `$ 0` → `None` |
| Listas | `English, Norse, Old, Danish` → 3 idiomas; nombres repetidos → uno, en el orden original |
| Nulos | «None» en `language` se conserva; vacío → `None`; *Unknown* y *?* como títulos no se tocan |
| Mojibake | Los 7 casos reales se reparan; los 2 irreversibles y un texto sano quedan igual |
| Plegado | «Amélie» → «amelie»; «Æon Flux» → «aeon flux»; «Død snø» → «dod sno» |
| Escape de LIKE | `%`, `_` y `\` quedan como literales |
| Rating ponderado | La fórmula con C y m conocidos; una película sin votos queda en C |
| Países | Los 194 nombres del CSV tienen su código ISO, y los que ya no existen apuntan a su sucesor |

### Integración: contra un PostgreSQL real

Los tests de integración usan PostgreSQL y no SQLite, porque la búsqueda depende de pg_trgm. Corren contra
la base de `docker compose` en local y contra un *service container* en CI, con una base aparte para los tests.
La URL llega por `TEST_DATABASE_URL`.

Hay un **CSV de prueba armado a mano**, de unas 30 filas, con un caso de cada cosa que encontró el
[perfil](data-profile.md):
- Películas reales: *The Shawshank Redemption*, la trilogía de *The Godfather*, *Relatos salvajes*, *Amélie*
  y *Æon Flux*.
- Títulos con `%` y `_`, títulos cortos (*Up*, *It*) y los títulos *Unknown* y *?*.
- Una película muda con «None» en `language`, y otra con «None» junto a otro idioma.
- *The 13th Warrior* («Norse, Old»), *Goodfellas* (guionista repetido) y un presupuesto en `$ 0`.
- La fila de «TV Movie 2019», descripciones con mojibake y `metascore` con decimal.
- Filas inválidas a propósito: un id mal formado, un año con dos números y una fila con un campo de más.

Con ese CSV se prueba:
- **La carga:**
  - carga lo que debe;
  - rechaza lo que debe, con su motivo;
  - correrla dos veces deja el mismo estado;
  - con el mismo archivo, la segunda corrida no hace nada;
  - si los rechazos superan el umbral, falla sin tocar los datos anteriores;
  - mientras escribe, otra conexión sigue leyendo las películas anteriores, sin esperar un lock.
- **Un CSV roto a propósito:** una comilla sin cerrar (las filas tragadas cuentan como rechazadas), un campo
  demasiado largo, caracteres invisibles, un NUL y números de miles de dígitos.
- **Basura al azar, con semilla fija:** 10.000 filas con comillas, comas, controles, números enormes, otros
  alfabetos e inyecciones, y archivos con líneas basura entre filas buenas. Cada fila termina cargada o
  rechazada con su motivo, y el resumen cuenta todas las líneas del archivo.
- **Los repositorios:** búsqueda, filtros, cada orden y la paginación en los bordes.

### API: el cliente de pruebas de Flask

- Casos felices de cada endpoint, con el formato de [docs/api.md](api.md).
- Validación: cada parámetro fuera de rango da 400 en formato Problem Details y sin stack trace.
- Paginación en los bordes: la primera página, la última, una más allá de la última y `page_size` 1 y 100.
- Los health checks: `/health/ready` da 503 si la base no responde.
- La base caída, una consulta que pasa el `statement_timeout` y una conexión que nunca contesta dan 503 en
  `/movies`, sin colgar al worker.
- La seguridad: los headers, el 429 con `Retry-After`, el límite sumando todas las rutas (y los 404 y 405), y la
  IP detrás del proxy.
- `GET /genres` y `GET /countries` devuelven sus cantidades y se pueden cachear; `country` repetido devuelve
  las películas de cualquiera de esos países.

### Aceptación: contra el CSV completo

Estos tests cargan las 85.855 películas una sola vez por corrida (unos segundos) y convierten en tests los
criterios de aceptación:

| Criterio | Test |
|---|---|
| `GET /movies` → 200, paginado, `total` = 85.855 | `test_list_default_page` |
| `?title=shawshank` → primero tt0111161 | `test_search_shawshank_first` |
| `?title=godfather` → tt0068646 y después Part II | `test_search_godfather_order` |
| `?title=relatos salvajes` → tt3011894 | `test_search_original_title_only` |
| `?title=amelie` → incluye tt0211915 | `test_search_ignores_accents` |
| `?title=%` → los 10 títulos con `%`; `?title=_` → los 7 con `_` | `test_search_escapes_wildcards` |
| `?title=` vacío → igual que sin filtro; `title` de más de 200 caracteres → 400 | `test_search_empty_and_too_long` |
| `?page_size=100000`, `?page=0` y `?page=abc` → 400 | `test_pagination_validation` |
| `?sort=title;DROP TABLE movies` → 400, y la tabla sigue ahí | `test_sort_whitelist` |
| Por rating ponderado, Shawshank y The Godfather arriba y *Suvarna Sundari* no | `test_weighted_rating_order` |
| `GET /movies/tt0068646` → detalle; inexistente → 404; mal formado → 400 | `test_movie_detail` |

Se suman dos de las decisiones posteriores:
- `?title=aeon flux` encuentra *Æon Flux*.
- La moneda `$` se publica como `USD`.

## Frontend (Vitest, React Testing Library y MSW)

- **Por qué Vitest y no Jest:**
  - su API es compatible con la de Jest, que es lo que menciona la consigna;
  - reusa la configuración de Vite (TypeScript, ESM, alias) sin sumar Babel ni ts-jest.
- **MSW** responde los pedidos a la API con datos de prueba y demoras controladas, sin tocar el código de la
  app.

| Test | Qué comprueba |
|---|---|
| Búsqueda con debounce | Escribir rápido hace un solo pedido, 300 ms después de la última tecla |
| Carrera entre respuestas | La respuesta lenta de «go» llega después que la de «godf»: se ven los resultados de «godf» |
| Sin parpadeo | Mientras carga una página nueva, siguen visibles los resultados anteriores |
| Estado vacío | Muestra el mensaje y «Limpiar filtros», que vacía la URL |
| Estado de error | Muestra «Reintentar», que vuelve a pedir |
| Vista tabla o tarjetas | El botón cambia la vista y la preferencia sobrevive a una recarga (`localStorage`) |
| Estado en la URL | Abrir `?q=godfather&page=2` muestra esa búsqueda y esa página |
| Formatos | Duración, votos, montos con moneda y «—» para los datos que faltan |
| Accesibilidad básica | Labels, `aria-live` con la cantidad de resultados y `aria-sort` en las columnas |
| Explorar por | Cada opción de los menús pone el parámetro correcto en la URL y en el pedido a la API |
| Pósters | La misma película genera siempre el mismo póster, y el color sale de su género |
| Por país | El buscador filtra la lista de países y un clic lleva a las películas de ese país |

## Fuera de este plan

- **Tests de punta a punta con Playwright:** son nivel 3 del backlog y solo se hacen con tu OK.
- **Rendimiento:** en la Fase 5, un script mide p50 y p95 de los endpoints principales y el resultado queda en
  el README.

## Cómo se corren

- **Backend:** `docker compose run --rm api pytest`. Los de aceptación tienen una marca propia, para poder
  correr el resto en segundos.
- **Frontend:** `npm test` en `frontend/`.
- **En CI:** la Fase 5 agrega GitHub Actions con ruff, pytest (con PostgreSQL como *service*), eslint, tsc, los
  tests del front, `pip-audit` y `npm audit`.
- **Cobertura:** se mide y se publica, sin un mínimo obligatorio. La meta es cubrir completo el parseo y las
  reglas de limpieza, que es donde un error rompe los datos en silencio.
