# Perfil del dataset

Generado con `python3 scripts/profile_dataset.py` sobre `data/IMDb_movies.csv.gz`. No editar a mano.

## Resumen

- Filas: **85.855**; columnas: **22**.
- Tamaño: 47,9 MB; en gzip (nivel 9): 21,7 MB.
- UTF-8 sin BOM; finales de línea: CRLF (Windows) en todas las líneas.
- Filas con una cantidad de campos distinta de 22: 0.
- Campos con saltos de línea adentro: 0.

## Formato por columna

Formato esperado de cada columna y cuántos valores no lo cumplen. En «Formatos observados», cada secuencia de dígitos se reemplaza por `N`.

| Columna | Formato esperado | Vacíos | Inválidos | Formatos observados |
|---|---|---:|---|---|
| `imdb_title_id` | `tt` + 7-8 dígitos | 0 | 0 | `ttN` ×85.855 |
| `title` | texto | 0 | 0 | — |
| `original_title` | texto | 0 | 0 | — |
| `year` | año 1880–2030 | 0 | 1 (p. ej. `tt8206668`: "TV Movie 2019") | `N` ×85.854 · `TV Movie N` ×1 |
| `date_published` | `AAAA-MM-DD` o `AAAA` | 0 | 1 (p. ej. `tt8206668`: "TV Movie 2019") | `N-N-N` ×81.292 · `N` ×4.562 · `TV Movie N` ×1 |
| `genre` | lista | 0 | 0 | — |
| `duration` | entero (minutos) | 0 | 0 | `N` ×85.855 |
| `country` | lista | 64 (0,1 %) | 0 | — |
| `language` | lista | 833 (1,0 %) | 0 | — |
| `director` | lista | 87 (0,1 %) | 0 | — |
| `writer` | lista | 1.572 (1,8 %) | 0 | — |
| `production_company` | texto | 4.455 (5,2 %) | 0 | — |
| `actors` | lista | 69 (0,1 %) | 0 | — |
| `description` | texto | 2.115 (2,5 %) | 0 | — |
| `avg_vote` | decimal 1–10 | 0 | 0 | `N.N` ×85.855 |
| `votes` | entero | 0 | 0 | `N` ×85.855 |
| `budget` | `<moneda> <monto>` | 62.145 (72,4 %) | 0 | `$ N` ×16.602 · `EUR N` ×2.422 · `INR N` ×906 · 76 más |
| `usa_gross_income` | `<moneda> <monto>` | 70.529 (82,1 %) | 0 | `$ N` ×15.321 · `GBP N` ×3 · `EUR N` ×1 · 1 más |
| `worlwide_gross_income` | `<moneda> <monto>` | 54.839 (63,9 %) | 0 | `$ N` ×30.955 · `INR N` ×58 · `GBP N` ×1 · 2 más |
| `metascore` | entero 0–100 | 72.550 (84,5 %) | 0 | `N.N` ×13.305 |
| `reviews_from_users` | entero | 7.597 (8,8 %) | 0 | `N.N` ×78.258 |
| `reviews_from_critics` | entero | 11.797 (13,7 %) | 0 | `N.N` ×74.058 |

## Nulos disfrazados

Valores que parecen «sin dato» (-, ?, n/a, na, nan, none, null, unknown), por columna:

- `title`: "?" ×1 (p. ej. `tt0775413`).
- `original_title`: "Unknown" ×2, "?" ×1 (p. ej. `tt0450340`, `tt0775413`, `tt1401152`).
- `language`: "None" ×68 (p. ej. `tt0000009`, `tt0000574`, `tt0004972`).
- Dentro de una lista, junto a otros valores: "None" en 28 filas de `language`.

Revisados a mano: en los títulos son películas reales (*Unknown*, de 2006 y de 2011, y una llamada *?*). De las 68 filas con `language` = "None", 12 son anteriores a 1930, la época del cine mudo.

## Clave y duplicados

- `imdb_title_id` repetidos: 0.
- `original_title` repetidos (comparación exacta): 3.729 títulos; con el mismo título y año: 125.
- Posibles duplicados reales (mismo título, año, director y duración, con distinto id): 0.

## Títulos y búsqueda

- `title` difiere de `original_title` en **23.372** filas: `title` está en italiano (el dataset parece scrapeado con configuración regional italiana).

| imdb_title_id | title | original_title |
|---|---|---|
| tt0068646 | Il padrino | The Godfather |
| tt0111161 | Le ali della libertà | The Shawshank Redemption |
| tt3011894 | Storie Pazzesche | Relatos salvajes |

- Títulos con caracteres no ASCII: 7.239 en `title`, 7.566 en `original_title`.
- Letras latinas que el plegado no simplifica, porque NFKD no las descompone: ø ×384, æ ×190, ð ×50, þ ×8, en 295 filas (p. ej. "Æon Flux", "Død snø", "Adams æbler").

Resultados de cada búsqueda (substring) según la estrategia. «Plegado» = sin mayúsculas ni acentos.

| Búsqueda | Solo `title` (ILIKE) | Ambas columnas (ILIKE) | Ambas columnas, plegado | La más votada |
|---|---:|---:|---:|---|
| `shawshank` | 0 | 1 | 1 | The Shawshank Redemption (1994) |
| `godfather` | 8 | 12 | 12 | The Godfather (1972) |
| `relatos salvajes` | 0 | 1 | 1 | Relatos salvajes (2014) |
| `amelie` | 3 | 3 | 5 | Le fabuleux destin d'Amélie Poulain (2001) |

- `%`: lo contienen 10 títulos (p. ej. "99 and 44/100% Dead!", "Brasília 18%", "Wool 100%"); buscarlo sin escapar el comodín devuelve 85.855.
- `_`: lo contienen 7 títulos (p. ej. "E_mail", "On_Line", "Un_seduttore_in_incognito"); buscarlo sin escapar el comodín devuelve 85.855.
- Título más largo: 196 caracteres en `title` (`tt0475343`), 196 caracteres en `original_title` (`tt0475343`).
- Largo de los títulos: `title`, promedio 17,0, percentil 99 46, 3 con más de 100 caracteres; `original_title`, promedio 15,7, percentil 99 44, 6 con más de 100 caracteres.
- Títulos de menos de 3 caracteres: 141, entre ellos "Up", "X2", "It", "21", "Us", "Pi", "PK", "9".

## Año y fecha

- `year` válido: de 1894 a 2020.
- `date_published`: 81.292 fechas completas y 4.562 con solo el año. En 17.054 fechas completas el año no coincide con `year` (probablemente el estreno local).

## Numéricos

| Columna | Con valor | Mín. | Mediana | Máx. |
|---|---:|---:|---:|---:|
| `duration` | 85.855 | 41 | 96 | 808 |
| `avg_vote` | 85.855 | 1,0 | 6,1 | 9,9 |
| `votes` | 85.855 | 99 | 484 | 2.278.845 |
| `metascore` | 13.305 | 1 | 57 | 100 |
| `reviews_from_users` | 78.258 | 1 | 9 | 10.472 |
| `reviews_from_critics` | 74.058 | 1 | 8 | 999 |

## Campos multivalor

Valores separados por coma.

| Columna | Valores distintos | Máx. por película | Filas con ítems repetidos | Más frecuentes |
|---|---:|---:|---:|---|
| `genre` | 25 | 3 | 0 | Drama, Comedy, Romance |
| `country` | 194 | 25 | 0 | USA, France, UK |
| `language` | 266 | 18 | 0 | English, French, Spanish |
| `director` | 34.707 | 2 | 89 | Michael Curtiz, Jesús Franco, Lloyd Bacon |
| `writer` | 61.695 | 2 | 6.191 | Jing Wong, Kuang Ni, Jesús Franco |
| `actors` | 417.320 | 16 | 191 | Brahmanandam, Anupam Kher, Eric Roberts |

- Ejemplo de ítem repetido: `tt0021725`, `director` = "William A. Seiter, William A. Seiter".
- Nombres que contienen una coma: "Greek, Ancient (to 1453)" ×10 en `language`, "Norse, Old" ×4 en `language`. Partir solo por la coma inventaría valores falsos, como «Old».
- Países que ya no existen, disueltos o con otro nombre, y que un mapa actual no tiene: West Germany ×1.114, Soviet Union ×866, Yugoslavia ×395, Czechoslovakia ×313, East Germany ×74, Federal Republic of Yugoslavia ×73, Serbia and Montenegro ×7, Netherlands Antilles ×5, Zaire ×2, Burma ×1, Korea ×1, North Vietnam ×1, Swaziland ×1.
- Los 25 géneros: Drama (47.110), Comedy (29.368), Romance (14.128), Action (12.948), Thriller (11.388), Crime (11.067), Horror (9.557), Adventure (7.590), Mystery (5.225), Family (3.962), Fantasy (3.812), Sci-Fi (3.608), Biography (2.377), History (2.296), War (2.242), Animation (2.141), Musical (2.041), Music (1.689), Western (1.583), Sport (1.064), Film-Noir (663), Reality-TV (3), Adult (2), Documentary (2), News (1).

## Montos

| Columna | Con valor | Monedas | Más frecuentes | Máximo | Mayores que INT32 | En cero |
|---|---:|---:|---|---|---:|---:|
| `budget` | 23.710 | 79 | $ (16.602), EUR (2.422), INR (906) | IRR 350.000.000.000 (`tt2351576`) | 113 | 34 |
| `usa_gross_income` | 15.326 | 4 | $ (15.321), GBP (3), EUR (1) | $ 936.662.225 (`tt2488496`) | 0 | 0 |
| `worlwide_gross_income` | 31.016 | 5 | $ (30.955), INR (58), GBP (1) | $ 2.797.800.564 (`tt4154796`) | 3 | 0 |

- Monedas anteriores al euro: ATS, BEF, DEM, ESP, FIM, FRF, GRD, IEP, ITL, NLG, PTE.
- La recaudación mundial viene en la columna `worlwide_gross_income` (sic).

## Votos y rating ponderado

- Votos: mínimo 99 (el dataset parece incluir solo películas con unos 100 votos o más); percentiles 10 / 50 / 90 / 99: 131 / 484 / 9.820 / 205.858.
- Películas con menos de 500 votos: 50,8 %.
- Fórmula estilo IMDb: WR = v/(v+m)·R + m/(v+m)·C, con C = 5,90 (media global) y m = 9.820 (percentil 90 de votos).

Top 5 por `avg_vote` crudo:

| # | Película | avg_vote | Votos | Ponderado |
|---:|---|---:|---:|---:|
| 1 | Suvarna Sundari (2019) | 9,9 | 896 | 6,23 |
| 2 | Notuku Potu (2017) | 9,8 | 926 | 6,23 |
| 3 | Ek (2019) | 9,8 | 527 | 6,10 |
| 4 | Lejos de Casa pelicula Venezolana (2020) | 9,8 | 133 | 5,95 |
| 5 | Jeeudo (2020) | 9,8 | 130 | 5,95 |

Top 5 por rating ponderado:

| # | Película | avg_vote | Votos | Ponderado |
|---:|---|---:|---:|---:|
| 1 | The Shawshank Redemption (1994) | 9,3 | 2.278.845 | 9,29 |
| 2 | The Godfather (1972) | 9,2 | 1.572.674 | 9,18 |
| 3 | The Dark Knight (2008) | 9,0 | 2.241.615 | 8,99 |
| 4 | The Godfather: Part II (1974) | 9,0 | 1.098.714 | 8,97 |
| 5 | Pulp Fiction (1994) | 8,9 | 1.780.147 | 8,88 |

- *Suvarna Sundari*, primera por `avg_vote` crudo, queda en el puesto 8.439 con el rating ponderado.
- De las 20 primeras por rating ponderado, 13 tienen un `title` (italiano) distinto de `original_title`.

## Calidad de texto

- Descripciones truncadas (terminan en «...»): 23.811.

| Columna | Problema | Filas | Ejemplo |
|---|---|---:|---|
| `description` | mojibake (UTF-8 leído como Latin-1) | 9 | `tt0291942`: "… de renta propiedad del tÃ<U+00AD>o de Carlos. Deciden rent…" |
| `description` | carácter de reemplazo U+FFFD | 1 | `tt0462284`: "…en two co-workers who can�۪t see eye to eye in the …" |
| `description` | espacios no estándar (NBSP, etc.) | 5 | `tt0399445`: "…his older brother Freddy.<U+00A0> Raul's destiny as a memb…" |
| `description` | espacios dobles | 3 | `tt0019312`: "Note: Contains Spoilers  The story, set in Russia …" |

- Descripciones con algún problema de codificación (mojibake, U+FFFD o espacios no estándar): 14 distintas. El mojibake se revierte volviendo a codificar en Windows-1252 o Latin-1 y decodificando como UTF-8 en 7 de 9.
- Sin ninguno de estos problemas: `title`, `original_title`, `genre`, `country`, `language`, `director`, `writer`, `production_company`, `actors`.
- Valores que empiezan con `=`, `+`, `-`, `@`, tabulación o retorno de carro (una planilla los ejecuta como fórmulas al abrir un CSV exportado): 4 en `title`, 4 en `original_title`, 8 en `description`, 2 en `production_company`.
- Valores con URLs: 0 (no hay posters).
