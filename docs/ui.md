# Interfaz: boceto y dirección visual

La interfaz toma de la sección de películas de Letterboxd la estructura y el tono:
- una barra superior oscura;
- una barra para explorar con menús desplegables;
- una grilla de pósters con sus estadísticas debajo.

El nombre (FakeIMDb), el color de acento y los pósters son propios: no se usan el logo ni los colores de
Letterboxd. La dirección se validó con una maqueta navegable hecha con datos reales.

## Pantallas

### Explorar (`/`)

```text
+------------------------------------------------------------------------------------------------+
| * FakeIMDb                                                                       (barra oscura) |
+------------------------------------------------------------------------------------------------+
| EXPLORAR POR [AÑO v|RATING v|POPULARIDAD v|GÉNERO v|NOMBRE v|PAÍS v]   BUSCAR PELÍCULA [       ] |
|                                                                                                |
| MEJOR VALORADAS                                        85.855 películas    [Tarjetas | Tabla]   |
| ---------------------------------------------------------------------------------------------- |
| +----------+ +----------+ +----------+ +----------+ +----------+ +----------+                  |
| | DRAMA    | | POLICIAL | | ACCIÓN   | | POLICIAL | | POLICIAL | | ACCIÓN   |                  |
| |          | |   The    | |==========| |          | |  Pulp    | |==========|                  |
| | THE      | | Godfather| | THE DARK | | THE      | | Fiction  | | THE LORD |                  |
| | SHAWSHANK| |          | | KNIGHT   | | GODFATHER| |          | | OF THE...|                  |
| | REDEMP...| |   1972   | |==========| | PART II  | |   1994   | |==========|                  |
| +----------+ +----------+ +----------+ +----------+ +----------+ +----------+                  |
| * 9,3 · 2,3 M * 9,2 · 1,6 M  ...                                                              |
|                                                                                                |
|                       <- Anterior    Página 1 de 3.578    Siguiente ->                         |
+------------------------------------------------------------------------------------------------+
```

- **La barra superior** solo lleva el nombre, FakeIMDb, que vuelve al inicio. No tiene los links de cuenta ni
  de secciones de Letterboxd.
- **«Explorar por»** reúne los menús desplegables. Cada opción es un pedido a la API:

  | Menú | Opciones | Qué pide a la API |
  |---|---|---|
  | Año | Todas; 2020s, 2010s… hasta 1890s. Se pueden elegir varias | `decade`, una por década |
  | Rating | Más alto primero, más bajo primero | `sort=rating`, con `order` |
  | Popularidad | Más votadas, menos votadas | `sort=votes`, con `order` |
  | Género | Todos y los 25 géneros, en español. Se pueden elegir varios: quedan las películas que tienen todos | `genre`, uno por género |
  | Nombre | De la A a la Z, de la Z a la A | `sort=title`, con `order` |
  | País | Abre la página de países | — |

- **Lo elegido se marca con un punto** del color del logo, más discreto que una tilde. Elegir de nuevo algo
  elegido lo saca, en cualquier menú: una década, un género o un orden, que vuelve al de por defecto. Año y
  Género quedan abiertos después de cada clic, para elegir varios; Esc o un clic afuera los cierra.
- **Con una sola década elegida, abajo aparece la tira de sus años**, como en Letterboxd: «2010s», 2010, 2011…
  Solo muestra los años con películas (`GET /years`). Un año filtra solo ese año (`year_from` y `year_to`);
  tocarlo de nuevo, o tocar la década, vuelve a la década entera.
- **El título de la sección** dice el orden: «Mejor valoradas» por defecto. Con una búsqueda, dice
  «Resultados para "godf"».
- **La leyenda** cuenta en una frase lo que dejan los filtros, con los valores en negrita: «Hay 430 películas
  del género Drama, hechas en Italia, estrenadas en los 2010s». Mientras cargan los resultados nuevos, sigue
  describiendo los que están en pantalla. Sin filtros no aparece, y la cantidad va arriba a la derecha.
- **«Limpiar filtros»** aparece cuando hay algo elegido y vuelve al estado inicial.
- **Cada página muestra 24 películas**, que llenan cuatro filas de seis en un escritorio.

### Vista tabla

```text
| TÍTULO         | AÑO  | GÉNEROS              | PAÍS            | DURACIÓN   | RATING | VOTOS     |
|----------------|------|----------------------|-----------------|------------|--------|-----------|
| Pulp Fiction   | 1994 | Policial, Drama      | Estados Unidos  | 2 h 34 min |    8,9 | 1.780.147 |
| Goodfellas     | 1990 | Biografía, Policial… | Estados Unidos  | 2 h 26 min |    8,7 |   991.505 |
```

- **Título, Año, Duración, Rating y Votos ordenan**, y llevan `aria-sort`, también para el orden por defecto. Un
  clic ordena por esa columna y otro invierte el orden.
- **«Rating» ordena por el rating ponderado y muestra `avg_vote`**
  ([ADR 0008](decisions/0008-default-order.md)). Mientras la tabla está ordenada así, una nota arriba explica
  que el orden tiene en cuenta la cantidad de votos.
- **«Anterior» y «Siguiente» no se deshabilitan del todo** (`aria-disabled`): así, al llegar a la última página
  con el teclado, el foco no se pierde.
- **El botón «Tarjetas | Tabla» recuerda la elección** en `localStorage`. En pantallas angostas se ven siempre
  tarjetas, de a dos por fila.

### Detalle (`/movies/:id`)

```text
+------------------------------------------------------------------------------+
| <- Volver                                                                     |
| +------------+   THE SHAWSHANK REDEMPTION                                     |
| |   póster   |   1994 · Drama · 2 h 22 min                                    |
| |  generado  |   * 9,3 (2.278.845 votos) · Metascore 80                       |
| +------------+   Two imprisoned men bond over a number of years, finding...   |
|                  [Ver en IMDb ->]                                             |
|  Dirección    Frank Darabont         Guion        Stephen King, Frank Darabont|
|  Elenco       Tim Robbins, Morgan Freeman, Bob Gunton, ...                    |
|  País         USA                    Idioma       English                     |
|  Presupuesto  US$ 25.000.000         Recaudación  US$ 28.815.245 (mundial)    |
+------------------------------------------------------------------------------+
```

- **Es una ruta propia**, así el detalle tiene una URL para compartir, y «Volver» regresa a la lista con los
  mismos filtros.
- **El link a IMDb** se abre en otra pestaña, con `rel="noopener noreferrer"`. Si la descripción viene cortada
  («...»), ahí está la sinopsis completa.
- **Los datos que faltan muestran «—»**, con «Sin datos» para lectores de pantalla. Un idioma «None» se
  muestra como «Sin diálogos».
- **La descripción, en inglés,** va marcada con `lang="en"`.

### Por país (`/countries`)

```text
+------------------------------------------------------------------------------+
| POR PAÍS                                                          <- Volver   |
| +--------------------------------------------------------------------------+ |
| |                      mapa del mundo, cada país con un                     | |
| |                 tono según su cantidad de películas                       | |
| +--------------------------------------------------------------------------+ |
| [Buscar un país...      ]                                                    |
| Alemania            3.721     Alemania Occidental   1.114     Argentina   ... |
+------------------------------------------------------------------------------+
```

- **El mapa** pinta los países que ya no existen sobre un sucesor, y al pasar el mouse lo aclara: «Rusia:
  1.083 películas · Unión Soviética: 866 películas». Un clic abre la lista de películas de ese país y de los
  que se le suman ([ADR 0009](decisions/0009-browse-by-country.md)).
- **Cada tono abarca diez veces más que el anterior:** 1–9, 10–99, 100–999, 1.000–9.999 y 10.000 o más, porque las cantidades van
  de 1 a 34.325 (Estados Unidos). Una leyenda los explica.
- **Los países chicos son puntos:** a escala 1:110m no hay forma para Hong Kong (1.884 películas), Singapur o
  Malta, así que se dibujan como un punto. La Antártida no se dibuja.
- **La lista de abajo muestra los países tal como vienen en el CSV**, en español, ordenados de la A a la Z y
  con buscador, que ignora tildes y acepta también el nombre en inglés. Los que ya no existen llevan la
  marca «ya no existe». Es la alternativa accesible al mapa: se usa con el teclado y con lector de pantalla.
- **Los filtros elegidos antes se mantienen:** si se abre el mapa con «Drama» elegido, un país abre los
  dramas de ese país.
- **El mapa se descarga aparte**, solo al abrir esta página: d3-geo y las formas pesan unos 67 KB comprimidos.
  Los datos salen de Natural Earth, de dominio público, con `scripts/build_world_map.py`.

## Estados

| Estado | Qué se ve |
|---|---|
| Primera carga | Pósters o filas «esqueleto» con la forma del contenido |
| Cargando con resultados previos | Siguen los resultados anteriores y una barra fina de progreso arriba. Nada parpadea |
| Sin resultados | «No encontramos películas…» y, si hay filtros, «Limpiar filtros». Solo cuando el total es 0: una página más allá de la última lleva a la última |
| Filtros que la API rechaza | «No pudimos buscar con estos filtros.» y «Limpiar filtros», porque reintentar no cambiaría nada. Casi no pasa: los valores de una URL compartida se acotan antes a los rangos de la API |
| Error | «No pudimos cargar las películas.» y «Reintentar» |
| Película inexistente | «Esa película no está en el catálogo.» y un link para volver |

## Comportamiento

- **Búsqueda en tiempo real:**
  - consulta la API 300 ms después de la última tecla;
  - un pedido nuevo cancela al anterior, y una respuesta vieja nunca reemplaza a una nueva.
- **Estado en la URL:** `?q=&page=&genre=&country=&decade=&year_from=&year_to=&sort=&order=`, con `genre`,
  `country` y `decade` repetibles. Se puede compartir,
  recargar y usar el botón atrás. Cambiar la búsqueda o un filtro vuelve a la página 1.
- **Formato es-AR con `Intl`:**
  - votos con separador de miles (2.278.845) y abreviados en las tarjetas (2,3 M);
  - duración como «2 h 22 min»;
  - montos con su moneda (US$ 25.000.000).
- **Accesibilidad:**
  - los menús se abren y se cierran con el teclado (Esc los cierra);
  - el foco se ve, con un anillo del color de acento;
  - la cantidad de resultados se anuncia con `aria-live`;
  - los títulos llevan `translate="no"`, para que el traductor del navegador no los cambie;
  - se respeta `prefers-reduced-motion`.
- **Navegadores:** versiones actuales de Chrome, Firefox, Safari y Edge.

## Dirección visual

### Paleta

| Token | Color | Uso | Contraste |
|---|---|---|---|
| `nav` | `#0e1217` | Barra superior | — |
| `page` | `#1b2129` | Fondo de la página | — |
| `surface` / `raised` | `#252d37` / `#2c3540` | Menús, campos y filas | — |
| `text` | `#e7ebef` | Texto principal | 13,5:1 sobre `page` |
| `muted` | `#9aa6b3` | Texto secundario y etiquetas | 6,5:1 sobre `page` |
| `accent` | `#f2b544` | Estrellas, selección activa y foco | 8,9:1 sobre `page` |
| `control` | `#6e7b88` | Borde de los campos | 3,7:1 sobre `page` |

Los contrastes cumplen WCAG AA: 4,5:1 para el texto y 3:1 para los bordes de los controles. El tema es oscuro
de entrada, así que un modo claro sería el extra, no al revés.

### Tipografía

| Uso | Fuente |
|---|---|
| Interfaz y datos | **IBM Plex Sans**: legible y con números tabulares, que alinean las columnas |
| Nombre de la app y títulos de los pósters | **Oswald**: angosta y gruesa, como la letra de los afiches |
| Títulos de una de las composiciones de póster | **Fraunces** en cursiva |

Las tres tienen licencia libre (SIL OFL) y se sirven desde la propia app con `@fontsource`. Así no se piden
recursos a terceros, y la política de seguridad de contenido (CSP) puede limitarse al propio origen.

### Pósters generados

Cada tarjeta es un póster 2:3 hecho con CSS ([ADR 0010](decisions/0010-generated-posters.md)). Hay cuatro
composiciones:
1. degradado con el título abajo;
2. marco fino con el título en cursiva;
3. círculo de luz detrás del título;
4. bandas con una línea de acento.

Se elige con un hash del `imdb_title_id`. El color sale de la familia del primer género, y el texto blanco
tiene un contraste de 5,4:1 o más:

| Familia | Géneros | Degradado |
|---|---|---|
| Drama | Drama, Biography | `#4a5d7a` → `#151c27` |
| Comedia | Comedy | `#9a5b0f` → `#2e1a05` |
| Romance | Romance | `#a23e62` → `#2c0f1b` |
| Acción | Action, Adventure, War, Western | `#8e3b2e` → `#250d09` |
| Suspenso | Thriller, Crime, Mystery, Horror, Film-Noir | `#2f3b3a` → `#0a0f0f` |
| Fantástico | Sci-Fi, Fantasy, Animation | `#2f6b58` → `#0a2019` |
| Familia y música | Family, Musical, Music | `#6a4c93` → `#1c1330` |
| Otros | History, Sport, Documentary, News, Reality-TV, Adult | `#6b6255` → `#1d1a15` |

Debajo de cada póster van el rating (`avg_vote`) y los votos, en el lugar donde Letterboxd muestra sus
estadísticas.
