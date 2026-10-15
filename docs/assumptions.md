# Supuestos y ambigüedades de la consigna

La consigna deja abiertos varios puntos. Cada uno tiene un supuesto explícito y el lugar donde se decide o se
justifica. Los que afectan al uso del proyecto se repiten en el README.

| # | La consigna dice | Ambigüedad | Supuesto | Dónde |
|---|---|---|---|---|
| 1 | `GET /movies` «retorna la lista de películas disponibles en el CSV» | ¿Las 85.855 de una vez? | Devuelve una página: 20 por defecto, hasta 100, dentro de un objeto con `items` y el total. Sin paginar serían decenas de MB | [ADR 0007](decisions/0007-api-contract.md) |
| 2 | `GET /movies?title=` «permite filtrar las películas por título» | ¿Qué título, coincidencia exacta o parcial, con o sin acentos? | Coincidencia parcial, sin distinguir mayúsculas ni acentos, en `title` y en `original_title` | [ADR 0004](decisions/0004-title-search-requirements.md) |
| 3 | «La API debe cargar los datos desde el archivo CSV proporcionado» | ¿Leerlo en cada arranque o cargarlo en una base? | El CSV es la única fuente. Lo carga en PostgreSQL un comando del propio backend (`flask seed`), que corre al levantar el proyecto | [ADR 0005](decisions/0005-data-storage.md) |
| 4 | El CSV «proporcionado» | ¿Cómo llega a quien clona el repo? | Está en el repo, comprimido con gzip y con su SHA-256 publicado | [ADR 0006](decisions/0006-csv-versioning.md) |
| 5 | Las películas se ven «en forma de tabla o tarjetas» | ¿Una de las dos? | Las dos, con un botón para cambiar; en mobile, tarjetas | [docs/ui.md](ui.md) |
| 6 | Búsqueda por título «en tiempo real» | ¿Filtrar en el navegador o consultar la API? | Se consulta la API mientras se escribe, 300 ms después de la última tecla, cancelando los pedidos viejos. Filtrar en el navegador exigiría bajar las 85.855 películas | [docs/ui.md](ui.md) |
| 7 | La consigna está en español | ¿Idioma de la interfaz y de los títulos? | Interfaz en español (es-AR). Títulos en su idioma original, porque el CSV no trae títulos en español | [ADR 0002](decisions/0002-display-title-and-ui-language.md) |
| 8 | No dice nada sobre la calidad de los datos | El CSV trae años con texto, montos en 79 monedas, nombres repetidos… | Reglas de limpieza explícitas. Una fila que no se puede interpretar se aparta con su motivo y no frena la carga | [ADR 0003](decisions/0003-data-cleaning-rules.md) |
| 9 | No dice qué datos mostrar | ¿Qué columnas en la lista y en el detalle? | Lista: título, año, géneros, directores, duración, rating y votos. Detalle: todo, salvo la fecha de estreno en Italia | [ADR 0007](decisions/0007-api-contract.md) |
| 10 | No dice cómo ordenar | ¿Qué se ve primero? | Sin búsqueda, rating ponderado; con búsqueda, relevancia y popularidad | [ADR 0008](decisions/0008-default-order.md) |
| 11 | «Instrucciones detalladas para ejecutar el proyecto localmente» | ¿Con Docker o sin Docker? | Camino principal: `docker compose up`. El README también explica cómo correrlo sin Docker, con un PostgreSQL local | README (Fase 6) |
| 12 | «Pruebas básicas para los endpoints» | ¿Qué alcance? | pytest contra un PostgreSQL real, con los criterios de aceptación como tests; en el front, Vitest, React Testing Library y MSW | [docs/test-plan.md](test-plan.md) |
| 13 | No menciona usuarios ni permisos | ¿Hace falta login? | No: es un catálogo público de solo lectura, sin datos personales. Queda fuera de alcance | [docs/security-plan.md](security-plan.md) |
| 14 | «Ejecutar el proyecto localmente» | ¿Hay que publicarlo en internet? | No. Un despliegue público queda como extra opcional | [docs/backlog.md](backlog.md) |
| 15 | No menciona navegadores | ¿Qué hay que soportar? | Versiones actuales de Chrome, Firefox, Safari y Edge, en escritorio y mobile | [docs/ui.md](ui.md) |
