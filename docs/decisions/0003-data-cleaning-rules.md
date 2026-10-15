# ADR 0003: Reglas de limpieza de datos

- Estado: Aceptada
- Fecha: 2026-10-14

## Contexto

El [perfil del dataset](../data-profile.md) muestra valores que no se pueden cargar tal cual. La política
general de la carga es que una fila que no se puede interpretar no frena el proceso: se rechaza con su
motivo, se cuenta y al final hay un resumen; si los rechazos superan un umbral, la carga falla. Este ADR
fija qué se corrige, qué se rechaza y qué se deja como está.

## Opciones descartadas

- **Rechazar cualquier fila con un valor inesperado.** Se perdería *Bad Education* (2019) por un texto que
  contiene el año sin ambigüedad. Para recuperarla habría que editar el CSV a mano, con lo que el archivo
  dejaría de ser el original, o mantener un archivo de correcciones manuales, una por caso.
- **Convertir los montos a dólares.** No hay tipos de cambio en los datos y varias monedas ya no existen.
- **Tratar «None», «Unknown» y «?» como nulos en todas las columnas.** Borraría títulos de películas reales.
- **Convertir «None» en NULL en `language`** (la primera propuesta de la regla 7). «None» indica que la
  película no tiene diálogos, y como NULL se mezclaría con los 833 idiomas vacíos, que sí son datos que
  faltan.
- **Mostrar todas las descripciones dañadas tal cual** (la primera propuesta de la regla 9). 7 de los 9
  casos con mojibake se pueden revertir de forma exacta, con un control que no toca textos sanos.
- **Guardar los montos en INTEGER.** La carga fallaría con 116 valores.

## Decisión

| # | Caso (evidencia del perfil) | Regla | Estado |
|---|---|---|---|
| 1 | `year` con texto: una fila, `tt8206668`, con «TV Movie 2019» en `year` y en `date_published` | Se extrae el año si hay exactamente uno válido; si no, se rechaza la fila. Detalle abajo. | **Aceptada** |
| 2 | `metascore`, `reviews_from_users` y `reviews_from_critics` son enteros, pero vienen como decimales (`57.0`). Probablemente el CSV se exportó con pandas, que convierte a decimal una columna de enteros con vacíos: estas tres tienen vacíos, y `duration` y `votes`, que no tienen, vienen como enteros | Se acepta `N.0` como entero. Cualquier otro decimal es inválido. | **Aceptada** |
| 3 | Montos en 79 monedas, algunas anteriores al euro (ATS, DEM, FRF, ITL…). El mayor es IRR 350.000.000.000 | Se guarda monto + moneda, sin convertir, en BIGINT: 113 presupuestos y 3 recaudaciones superan el máximo de un entero de 32 bits. | **Aceptada** |
| 4 | 34 presupuestos en 0 (`$ 0`, `GBP 0`, `INR 0`…) | Se guardan como «sin dato»: monto y moneda en NULL. Ninguna película se hace sin presupuesto, así que un 0 significa que falta el dato, y mostrar «$ 0» diría que la película no costó nada. | **Aceptada** |
| 5 | Listas separadas por coma. «Greek, Ancient (to 1453)» y «Norse, Old» tienen una coma en el nombre: son nombres del estándar ISO 639-2, que invierte algunos. Partiendo en cada coma, *The 13th Warrior* (1999) tendría un idioma «Old». Revisado: no hay otros nombres con coma en idiomas ni en países | Se separa por coma, respetando esos nombres. | **Aceptada** |
| 6 | Ítems repetidos dentro de una fila: `writer` en 6.191 filas, `actors` en 191, `director` en 89. IMDb acredita a una persona una vez por rol y el CSV perdió el rol: en *Goodfellas* (1990), `writer` dice «Nicholas Pileggi, Nicholas Pileggi» (autor del libro y coguionista) | Se eliminan los repetidos y se conserva el orden. | **Aceptada** |
| 7 | `language` con el texto «None»: 68 filas con ese único valor y 28 donde aparece junto a otros idiomas. Es el valor que usa IMDb para las películas sin diálogos: 12 son mudas anteriores a 1930, y otras son películas sin diálogos como *The Thief* (1952) o *Le bal* (1983) | La carga no lo toca y la interfaz lo muestra como «Sin diálogos». En los títulos, «Unknown» y «?» son películas reales y no se tocan. Los valores vacíos son NULL en todas las columnas. | **Aceptada** |
| 8 | 17.054 fechas completas con un año distinto de `year`: `date_published` es la fecha de estreno en Italia (detalle abajo) | Los filtros y el orden usan `year`. La interfaz no muestra `date_published`: es un dato de Italia, como el título italiano, y la consigna no lo pide. | **Aceptada** |
| 9 | 14 descripciones con problemas de codificación (una tiene dos): 9 con mojibake, texto UTF-8 leído con otra codificación («fiancÃ©»); 1 con U+FFFD, un carácter que se perdió; y 5 con espacios no estándar | Se reparan las 7 con mojibake que se pueden revertir de forma exacta: el texto se vuelve a codificar en Windows-1252 o Latin-1 y se decodifica como UTF-8. Solo se aplica si el texto tiene el patrón de mojibake y la reversión sale limpia, así que no toca textos sanos. Las otras 3 visibles se muestran tal cual; los espacios no estándar se ven como espacios normales. | **Aceptada** |

### Regla 1: año escrito con texto

Aceptada el 2026-10-14. Si `year` no es un número de 4 dígitos, se busca el año dentro del texto:

| Valor | Resultado | ¿Aparece en el CSV? |
|---|---|---|
| `2019` | 2019 | Sí: es el caso normal, un año solo (85.854 filas) |
| `TV Movie 2019` | 2019, con un warning en el resumen de la carga | Sí: una fila, `tt8206668` |
| `1999 2001` | Fila rechazada: hay más de un año | No |
| `abc` | Fila rechazada: no hay ningún año | No |
| `1850` | Fila rechazada: fuera del rango válido | No |

Los valores que no aparecen en el CSV son casos borde: definen qué hace la regla si llegaran en otra versión
del archivo, y se convierten en tests.

- Cuenta como año un número de exactamente 4 dígitos, no parte de un número más largo, entre 1880 y el
  año actual.
- `date_published` recibe el mismo tratamiento cuando no es una fecha completa ni un año solo.
- El texto que acompaña al año («TV Movie») se descarta: no hay una columna para el tipo de título.
- Por qué tolerante y no estricta: la regla estricta perdería *Bad Education* (2019), y recuperarla
  obligaría a editar el CSV original o a mantener correcciones manuales. Con estos límites la regla no
  adivina: si el texto es ambiguo, rechaza la fila.

### Regla 8: `date_published` es la fecha de estreno en Italia

Aceptada el 2026-10-15. Se tomaron las 300 películas no italianas más votadas con fecha completa y se
compararon con sus fechas de estreno por país en Wikidata (propiedad P577 con el país como calificador
P291, consultada el 2026-10-15):

| País | Películas con fecha en Wikidata | Coincide con `date_published` |
|---|---:|---:|
| Italia | 31 | 29 (94 %) |
| Estados Unidos | 261 | 16 (6 %) |
| Alemania | 297 | 31 (10 %) |
| Francia | 126 | 23 (18 %) |

- Las 2 que no coinciden con Italia son *Gravity* y *La La Land*: la fecha que Wikidata tiene para Italia
  es la de su estreno en el Festival de Venecia, y la del CSV es posterior.
- Las coincidencias con otros países son, probablemente, estrenos el mismo día que en Italia.
- Es coherente con los títulos: el dataset parece scrapeado con configuración regional italiana.

## Consecuencias

- Cada regla tiene tests unitarios en la carga de datos, con estos casos borde.
- El resumen de la carga informa cuántos valores corrigió cada regla y cuántas filas rechazó.
- Rechazar una fila no es perderla: se guarda con su contenido original y el motivo. Si después se ajusta
  una regla, se vuelve a correr la carga, que deja siempre el mismo estado aunque se corra dos veces.
- Los montos no se pueden ordenar ni comparar entre monedas: se muestran como monto + moneda.
- `writer` y `director` traen como máximo 2 nombres por película: la lista viene cortada en el origen. En
  *Goodfellas* falta Martin Scorsese como coguionista. Va en el README como limitación conocida.
- «Sin dato» se representa igual en todas las capas: NULL en la base y `null` en el JSON de la API. La API
  no devuelve textos de presentación; la interfaz decide cómo mostrarlo: «—», con el texto «Sin datos»
  para lectores de pantalla. Vale para todos los campos sin dato, no solo para los presupuestos en 0.
