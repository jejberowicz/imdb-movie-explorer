# ADR 0004: Requisitos de la búsqueda por título

- Estado: Aceptada
- Fecha: 2026-10-14

## Contexto

`GET /movies?title=` filtra por título. El [perfil del dataset](../data-profile.md) muestra qué falla con
una búsqueda ingenua (substring en `title`, sensible a acentos):

| Búsqueda | Solo `title` | Ambas columnas | Ambas columnas, sin mayúsculas ni acentos |
|---|---:|---:|---:|
| shawshank | 0 | 1 | 1 |
| relatos salvajes | 0 | 1 | 1 |
| amelie | 3 | 3 | 5 |

Además, 10 títulos contienen `%` y 7 contienen `_`, los comodines de LIKE: sin escaparlos, buscar `%` o `_`
devuelve las 85.855 películas. El título más largo tiene 196 caracteres y 141 tienen menos de 3
(*Up*, *It*, *Us*, *Pi*, *21*).

## Opciones descartadas

- **Buscar solo en `original_title`**, el único título que muestra la interfaz
  ([ADR 0002](0002-display-title-and-ui-language.md)). Cada resultado contendría el texto buscado en su
  título visible, pero un título copiado de la columna `title` del CSV, como «Il padrino», no encontraría la
  película. La consigna es obligatoria, y una implementación literal de `GET /movies?title=` filtraría por
  esa columna: la búsqueda no puede encontrar menos que eso.
- **Exigir un mínimo de 3 caracteres**, algo habitual con índices trigram. *Up* o *It* no se podrían
  encontrar.
- **No limitar el largo de la búsqueda.** Dejaría sin validar una entrada pública.

## Decisión

Requisitos de la búsqueda, independientes de cómo se implemente:

| # | Requisito | Estado |
|---|---|---|
| 1 | Busca en `title` y en `original_title`: encuentra todo lo que encontraría filtrar solo por `title`, más los títulos originales | **Aceptada** |
| 2 | Ignora mayúsculas y acentos: «amelie» encuentra *Le fabuleux destin d'Amélie Poulain* | **Aceptada** |
| 3 | Escapa `%` y `_`: `?title=%` devuelve solo los títulos que contienen `%` | **Aceptada** |
| 4 | Ordena por relevancia y popularidad: el logaritmo de los votos, más 2 si un título es igual a la búsqueda y 1 si empieza con ella. Primero se ordenó por coincidencia y después por votos, y con «godfather» una película llamada exactamente «Godfather» (2.839 votos) quedaba antes que *The Godfather*. En las cuatro búsquedas de prueba, la primera es la esperada | **Aceptada** |
| 5 | `title` acepta hasta 200 caracteres; uno más largo es un error de validación. El límite es para lo que se busca, no para los datos: el 99 % de los títulos tiene hasta 46 caracteres, ninguno pasa de 200, y el más largo, de 196, es real (*Night of the Day of the Dawn…*, una parodia) | **Aceptada** |
| 6 | No hay un mínimo de caracteres | **Aceptada** |

La implementación (columna normalizada en la carga o función `unaccent` inmutable, índice trigram) se
decide en el ADR de almacenamiento, con mediciones.

## Consecuencias

- Cada requisito es un test de aceptación del endpoint.
- Algunos resultados no contienen el texto buscado en el título visible, porque coincidieron con el título
  italiano, que la interfaz no muestra: «libertà» encuentra *The Shawshank Redemption*. El README lo
  explica.
- Según la documentación de pg_trgm, un patrón de menos de 3 caracteres no aprovecha un índice trigram:
  hay que medir cuánto tardan esas búsquedas.
