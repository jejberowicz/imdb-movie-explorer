# ADR 0005: Dónde viven los datos

- Estado: Aceptada
- Fecha: 2026-10-15

## Contexto

La consigna pide que la API cargue los datos desde el CSV provisto. Hay tres formas de tenerlos disponibles
para responder: un DataFrame de pandas en memoria (lo más literal), SQLite o PostgreSQL. Para no decidir con
argumentos genéricos, `scripts/benchmark_storage.py` las mide con el CSV real y las dos consultas que la API
necesita: la búsqueda por título (total más la primera página, por relevancia y popularidad) y la lista por
rating ponderado. Las tres opciones cargan todas las columnas y devuelven exactamente los mismos resultados en
todas las consultas, así que la comparación es justa.

Corrida del 2026-10-15 en una notebook (Intel i7-1255U, WSL2), con Python 3.12, pandas 3.0, SQLite 3.45 y
PostgreSQL 18.

**Cada worker de Gunicorn**, en un proceso nuevo, hasta responder la primera búsqueda:

| Opción | Arranque | Memoria |
|---|---:|---:|
| pandas | 1,68 s | 201 MB |
| SQLite | 0,04 s | 18 MB |
| PostgreSQL | 0,13 s | 40 MB |

Con pandas, cada worker lee el CSV y guarda su propia copia: con 4 workers son unos 800 MB. Con SQLite y
PostgreSQL los datos se cargan una sola vez y cada worker solo abre una conexión.

**Búsqueda**, en milisegundos (mediana de 25):

| Búsqueda | Resultados | pandas | SQLite sin índice | SQLite con FTS5 trigram | PostgreSQL sin índice | PostgreSQL con pg_trgm |
|---|---:|---:|---:|---:|---:|---:|
| `shawshank` | 1 | 24,3 | 22,8 | 0,1 | 26,1 | 0,6 |
| `godfather` | 12 | 36,3 | 21,3 | 0,1 | 22,6 | 0,6 |
| `the` | 13.956 | 53,3 | 30,8 | 17,9 | 28,5 | 14,1 |
| `up` | 1.082 | 26,7 | 22,3 | 21,9 | 21,2 | 22,2 |

- Sin índice, las tres opciones recorren las 85.855 filas en 20 a 50 ms. pandas además ocupa el CPU del
  worker mientras tanto.
- Con un índice de trigramas, una búsqueda selectiva baja a menos de 1 ms. Las búsquedas de menos de 3
  caracteres, como «up», no pueden usarlo (el plan de PostgreSQL pasa a `Seq Scan`) y tardan unos 20 ms, lo
  que es aceptable.
- **La lista por rating ponderado** sale del índice en 0,15 ms. Lo que cuesta es contar las 85.855 filas para
  el total: entre 6 y 13 ms por request.
- **Carga, una sola vez:** leer y preparar el CSV lleva 1,6 s. PostgreSQL tarda 2,1 s más 1,5 s de índices
  trigram (58 MB de tabla y 19 MB de índices); SQLite, 1,2 s (72 MB).

**Búsqueda sin acentos.** Las tres opciones la resuelven igual: el texto se pliega en Python al cargar
(minúsculas, sin acentos y con ø, æ, ð y þ convertidas en o, ae, d y th, porque NFKD no las descompone: ver el
[perfil](../data-profile.md)) y la consulta se pliega con la misma función. En PostgreSQL, la alternativa
`unaccent` no es IMMUTABLE, así que para indexarla hace falta un wrapper, y sus reglas no son las mismas que
las de Python: habría dos definiciones de «sin acentos».

## Opciones

1. **pandas en memoria.** Es lo más literal de la consigna, pero cada worker paga 1,7 s y 201 MB, la búsqueda
   no tiene índices y pandas convierte valores al leerlos ([ADR 0001](0001-reproducible-dataset-profiling.md)).
2. **SQLite.** Es la opción más simple y la más liviana: no necesita un servidor, un worker arranca en 0,04 s y,
   con FTS5 trigram, busca en 0,1 ms. También permite correr el proyecto sin Docker sin instalar una base. Le
   falta lo que PostgreSQL trae de fábrica y el [backlog](../backlog.md) usa más adelante: un usuario de solo
   lectura y `statement_timeout` para la API, y la similitud de trigramas para tolerar errores de tipeo.
3. **PostgreSQL con pg_trgm.**

## Decisión

Opción 3: PostgreSQL 18 con la extensión pg_trgm.

- El CSV sigue siendo la única fuente. Lo carga un comando del propio backend (`flask seed`), que corre una vez
  al levantar el proyecto, antes que la API.
- Las columnas de búsqueda se guardan plegadas, con índices GIN de trigramas.
- El rating ponderado se calcula al cargar y se indexa ([ADR 0008](0008-default-order.md)).
- El total sin filtros sale del resumen de la última carga, no de un `count(*)` por request.

Frente a SQLite, el beneficio concreto es que la seguridad y las funciones previstas (usuario de solo lectura,
`statement_timeout`, tolerancia a errores de tipeo) vienen incluidas, sin cambiar de base a mitad de camino.

## Consecuencias

- `docker compose` suma la base y el seed como servicios, con healthchecks: el usuario sigue levantando todo con
  un solo comando.
- Correrlo sin Docker exige un PostgreSQL local. El README lo explica.
- Los tests corren contra un PostgreSQL real, porque la búsqueda depende de pg_trgm.
- Un worker pesa unos 40 MB más Flask y el resto de sus dependencias, sin una copia de los datos.
- Si se leyera la consigna como «la API lee el CSV en cada arranque»: el seed es parte del backend y lee el CSV
  provisto. Queda como supuesto en el README.
