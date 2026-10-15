# ADR 0001: Perfilado reproducible del dataset

- Estado: Aceptada
- Fecha: 2026-10-14

## Contexto

Antes de diseñar la base, la búsqueda y la carga hay que conocer los datos. El CSV es la única fuente
(85.855 filas, 22 columnas, 48 MB) y una exploración inicial dejó hipótesis por verificar: títulos en
italiano, acentos, comodines de LIKE dentro de los títulos y montos en varias monedas. Hace falta medir esas
hipótesis y, sobre todo, encontrar los problemas que nadie está buscando.

## Opciones

1. **Exploración manual o notebook con pandas.** Rápida de escribir, pero difícil de reproducir y de revisar
   en un diff, y suma una dependencia pesada antes de que exista el proyecto. Además, pandas convierte los
   valores al leerlos y esconde justo lo que el perfilado tiene que mostrar. Probado con pandas 3.0:
   `read_csv` convierte `"None"`, `"NA"` y `"null"` en nulos en cualquier columna, títulos incluidos, y lee
   `metascore` como número, sin que se vea que viene escrito `57.0`.
2. **Script con un chequeo puntual por hipótesis** (la primera versión). Confirma lo sospechado, pero no
   encuentra lo que no se buscó y es frágil: con un BOM al inicio del archivo se cae (`KeyError`),
   `float()` acepta `nan`, `"²".isdigit()` es verdadero pero `int("²")` falla, y al partir las listas por
   coma contaba idiomas que no existen.
3. **Script con un formato declarado por columna, más análisis dirigidos.** Cada columna declara su formato
   y el reporte cuenta vacíos e inválidos, con ejemplos. Encima, secciones que responden preguntas de
   diseño: clave, búsqueda, fechas, listas, montos, rating y calidad de texto.

## Decisión

Opción 3: `scripts/profile_dataset.py` genera `docs/data-profile.md`.

- **Solo librería estándar** (los módulos que vienen con Python: `csv`, `re`, `statistics`…), sin pandas.
  La razón principal es ver los valores crudos. A la pregunta «¿cuántas filas tienen `language` igual a
  `"None"`?», el módulo `csv` responde 68 y pandas con su configuración por defecto responde 0, porque al
  leer ya los convirtió en nulos. Se le puede pedir a pandas que no convierta nada, pero entonces todas las
  columnas quedan como texto y se pierde la comodidad que lo hacía atractivo. La razón secundaria es que
  corre con el Python del sistema, sin instalar los ~115 MB de pandas y numpy. Esto vale solo para el
  perfilado: la aplicación tiene sus propias dependencias.
- **Parsers estrictos con expresiones regulares**, en vez de `int()` y `float()`, que también aceptan
  `" 5"`, `"5_0"`, `"nan"` o `"1e3"`. Devuelven `None` cuando el valor no cumple el formato: el script
  informa el problema y nunca se cae por un dato.
- **Estructura verificada.** Detecta BOM, finales de línea, filas con más o menos campos (las aparta e
  indica la línea) y campos con saltos de línea. Si falta una columna, termina con un error claro.
- **Reporte generado y determinístico.** Con la misma versión de Python, el mismo CSV produce el mismo
  archivo byte a byte. Importa por dos razones: el reporte está versionado, y si cambiara en cada corrida
  git mostraría diferencias sin que los datos hayan cambiado; y cualquiera puede comprobar que no se editó
  a mano corriendo el script y viendo que `git status` no muestra cambios. Para lograrlo, los conjuntos se
  recorren ordenados (verificado con distintos valores de `PYTHONHASHSEED`), el reporte no incluye la fecha
  en que se generó, que ya queda en el historial de git, y el rango válido de años es fijo, 1880–2030, para
  que el resultado no dependa del día en que se corre.
- **Hechos en el reporte, decisiones en los ADR.** El reporte mide y explica; lo que se decide a partir de
  esos datos se argumenta en este directorio. Un archivo generado no debe contener conclusiones fijas que
  pueden quedar desactualizadas.
- **Percentiles con interpolación lineal** (`statistics.quantiles(method="inclusive")`), el mismo método
  que `percentile_cont` de PostgreSQL.
- **Nombres con coma en una lista explícita** (`COMMA_NAMES`). Se probó detectarlos con una heurística
  (ítems que siempre aparecen después del mismo valor) y daba falsos positivos, como dúos de directores
  reales (Michael Powell y Emeric Pressburger).
- **Sin tests propios.** Es una herramienta de análisis. Se validó contrastando sus números y corriéndola
  sobre archivos de prueba: una muestra de 50 filas, un CSV roto (con BOM, un campo de más y valores
  inválidos) y uno al que le falta una columna. El parseo que llega a producción se implementa y se testea
  en la carga de datos.

## Consecuencias

- Encontró problemas que la primera versión no veía: enteros que vienen como decimales (`"57.0"`), montos
  que no entran en un entero de 32 bits, idiomas con una coma en el nombre, ítems repetidos dentro de las
  listas, títulos reales que parecen nulos (*Unknown*, *?*) y descripciones con problemas de codificación.
  Las decisiones que salen de esto están en los ADR [0003](0003-data-cleaning-rules.md) y
  [0004](0004-title-search-requirements.md).
- Es más del doble de largo que la primera versión (unas 700 líneas contra 320) y tarda unos 10 segundos.
- El perfilado y la carga tienen código de parseo separado: el perfilado describe lo que hay y la carga
  aplica las reglas decididas. La aplicación no importa nada de `scripts/`.
