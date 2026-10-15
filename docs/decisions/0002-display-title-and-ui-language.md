# ADR 0002: Título a mostrar e idioma de la interfaz

- Estado: Aceptada
- Fecha: 2026-10-14

## Contexto

La columna `title` está en italiano en 23.372 filas (*Il padrino*, *Le ali della libertà*,
*Storie Pazzesche*): el dataset parece scrapeado con configuración regional italiana. `original_title` tiene
el título en el idioma de la película. No hay títulos en español, y las descripciones y los géneros están en
inglés. La interfaz es en español (es-AR).

## Opciones

1. **Mostrar `title`.** Es la columna «título», pero un usuario hispanohablante vería *Il padrino*.
2. **Hacer la interfaz en italiano.** El italiano es un efecto del scraping, no una elección del dataset.
3. **Traducir automáticamente los títulos italianos al español.** Sería la traducción de una traducción, y
   no da el título con que se estrenó cada película: *Relatos salvajes* es argentina, su título italiano es
   *Storie Pazzesche* y traducido de vuelta daría algo como «Historias locas». Además, requiere un servicio
   de traducción externo.
4. **Conseguir los títulos oficiales en español:**
   - Scrapear IMDb. Sus condiciones de uso lo prohíben, son 85.855 páginas con riesgo de bloqueo y la
     consigna pide cargar los datos desde el CSV provisto.
   - Usar el dataset oficial `title.akas.tsv.gz` de IMDb (uso personal y no comercial). No es una
     traducción: tiene el título de estreno de cada película por país, y se cruza por `imdb_title_id`.
     Es viable, pero suma una descarga de cientos de MB, no todas las películas tienen título para
     Argentina y queda fuera del alcance pedido.
5. **Mostrar `original_title` como principal y el título italiano como secundario, cuando difiere.**
   Explicaría por qué una búsqueda devolvió un resultado. Se evaluaron dos variantes:
   - Debajo del título, en la tabla y en las tarjetas: 13 de las 20 películas de la primera pantalla
     (ordenada por rating ponderado) mostrarían un título en italiano.
   - Solo en el detalle de la película, con la etiqueta «Título en Italia». Se ve menos, pero sería una
     excepción al criterio de mostrar solo títulos originales, para un dato que no le sirve a quien usa una
     interfaz en español.
6. **Mostrar solo `original_title`**, que es el título real de cada película, sin traducciones de por medio.

## Decisión

Opción 6:

| Punto | Decisión | Estado |
|---|---|---|
| Título | Solo `original_title` (*The Godfather*, *Relatos salvajes*), en toda la interfaz: tabla, tarjetas y detalle. El título italiano no se muestra en ninguna pantalla | **Aceptada** |
| Títulos oficiales en español | No se scrapea IMDb. El cruce con `title.akas` queda en el README, en «qué haría con más tiempo» | **Aceptada** |
| Búsqueda | Mira las dos columnas (ver [ADR 0004](0004-title-search-requirements.md)) | **Aceptada** |
| Descripciones | En inglés, tal cual, marcadas con `lang="en"` para que un lector de pantalla las pronuncie en inglés. Traducirlas al español, el idioma de la interfaz, queda en el README, en «qué haría con más tiempo» | **Aceptada** |
| Géneros | Se traducen en la interfaz con un diccionario: son 25, un conjunto cerrado (ver el [perfil](../data-profile.md)) | **Aceptada** |

## Consecuencias

- El README lo explica como supuesto: el dataset no trae títulos en español.
- Es una decisión sobre lo que muestra la interfaz: los datos conservan las dos columnas.
- La búsqueda también mira el título italiano ([ADR 0004](0004-title-search-requirements.md)), así que
  puede devolver películas cuyo título visible no contiene el texto buscado, y ninguna pantalla explica por
  qué: «libertà» encuentra *The Shawshank Redemption* (*Le ali della libertà*), *Rescue Dawn*
  (*L'alba della libertà*) y *Selma* (*Selma - La strada per la libertà*). Es un costo aceptado; el README
  lo explica.
- Quien quiera leer las descripciones en otro idioma puede usar el traductor del navegador. Los títulos van
  marcados con `translate="no"` para que el traductor no los cambie: traducir un título original es lo que
  se descartó en la opción 3.
- Hay que mantener el diccionario de géneros. Si aparece un género que no está, se muestra en inglés.
- El título que se muestra puede estar en cualquier idioma (inglés, francés, coreano…).
