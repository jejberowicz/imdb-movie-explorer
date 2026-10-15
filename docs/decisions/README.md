# Decisiones de arquitectura (ADR)

Cada decisión no trivial tiene un registro corto: contexto, opciones, decisión y consecuencias.
La evidencia sobre los datos está en el [perfil del dataset](../data-profile.md).

| # | Decisión | Estado |
|---|---|---|
| [0001](0001-reproducible-dataset-profiling.md) | Perfilado reproducible del dataset | Aceptada |
| [0002](0002-display-title-and-ui-language.md) | Título a mostrar e idioma de la interfaz | Aceptada |
| [0003](0003-data-cleaning-rules.md) | Reglas de limpieza de datos | Aceptada |
| [0004](0004-title-search-requirements.md) | Requisitos de la búsqueda por título | Aceptada |

Pendientes de la Fase 0:

- Dónde viven los datos: pandas en memoria, SQLite o PostgreSQL, con mediciones.
- Cómo se versiona el CSV (tal cual, en gzip o fuera del repo). El archivo tiene finales de línea CRLF y el
  `.gitattributes` convierte los archivos de texto a LF.
- Contrato de la API: paginación por defecto y formato de las respuestas y de los errores.
- Orden por defecto del listado: rating ponderado.
