# ADR 0007: Contrato de la API

- Estado: Aceptada
- Fecha: 2026-10-15

## Contexto

La consigna fija dos endpoints: `GET /movies` («retorna la lista de películas disponibles en el CSV») y
`GET /movies?title=`. Todo lo demás se suma sin romperlos. Sin paginar, `GET /movies` devolvería las 85.855
películas, decenas de MB de JSON. Este ADR fija las decisiones de forma; la referencia completa, con
parámetros y ejemplos, está en [docs/api.md](../api.md).

## Decisiones y opciones descartadas

**1. Paginación por defecto.** `GET /movies` sin parámetros devuelve la primera página: 20 películas,
ordenadas por rating ponderado ([ADR 0008](0008-default-order.md)). `page_size` acepta de 1 a 100.

- Descartado: devolver todo, por el tamaño.
- Descartado: acotar en silencio un `page_size` fuera de rango (por ejemplo, convertir 100000 en 100), porque
  esconde errores del cliente. La API responde 400 y dice cuál es el máximo.
- Una página más allá de la última devuelve 200, con `items` vacío y el total correcto.

**2. Sobre con metadatos.** La respuesta es un objeto:

```json
{"items": [...], "page": 1, "page_size": 20, "total": 85855, "total_pages": 4293}
```

- Descartado: devolver la lista sola, con el total en headers (`X-Total-Count`, `Link`). Los headers no se ven
  en el navegador ni en un `curl` sin `-i`, y desde otro origen el front no puede leerlos sin
  `Access-Control-Expose-Headers`.
- Sigue siendo «la lista de películas»: está en `items`. Queda como supuesto en el README.

**3. Errores con RFC 9457 (Problem Details).** Todos los errores son `application/problem+json`, con `type`,
`title`, `status` y `detail`; los de validación agregan `errors`, con el parámetro y el motivo de cada uno.
Nunca hay stack traces.

- Un parámetro inválido es 400. Se descartó 422 porque está pensado para un cuerpo con formato correcto pero
  contenido inválido, y estos requests no tienen cuerpo.
- Los textos de error están en inglés: son para desarrolladores. La interfaz muestra sus propios mensajes en
  español según el código de estado, porque la API no devuelve textos de presentación
  ([ADR 0003](0003-data-cleaning-rules.md)).

**4. Nombres de los campos.** Se usa snake_case, como en Python y en el CSV. Hay dos excepciones al CSV, para
que ningún campo engañe:

- La columna `title`, que está en italiano, se publica como `italian_title`. Un campo llamado `title` con
  *Il padrino* adentro confundiría a cualquiera que use la API. El parámetro `?title=` no cambia, porque lo
  fija la consigna.
- Los montos se publican como `{"amount": 25000000, "currency": "USD"}`. En el CSV, el dólar estadounidense
  aparece como `$`; la carga lo guarda como `USD`, su código ISO 4217, como ya vienen el resto de las monedas.
  En es-AR, «$» se lee como pesos.

**5. Lista corta, detalle completo.** La lista devuelve solo los campos que muestra la interfaz, incluidos los
directores, que van en el póster de cada tarjeta ([ADR 0010](0010-generated-posters.md)), más
`weighted_rating`, que explica el orden. `GET /movies/{imdb_title_id}` devuelve todo, incluido
`italian_title`, que explica por qué una búsqueda devolvió una película. `date_published` no se publica: es la
fecha de estreno en Italia ([ADR 0003](0003-data-cleaning-rules.md), regla 8).

**6. Orden con lista blanca.** `ORDER BY` no se puede parametrizar, así que `sort` solo acepta valores fijos
(`relevance`, `rating`, `year`, `votes`, `duration`, `title`) y `order` solo acepta `asc` o `desc`. Cualquier
otro valor da 400. El orden siempre termina en `imdb_title_id`, para que la paginación sea estable: la misma
película no puede aparecer en dos páginas.

**7. OpenAPI generado desde los modelos de Pydantic**, con Swagger UI. Se elige flask-openapi3 antes que
spectree: las dos validan con Pydantic, pero flask-openapi3 recibe los parámetros como argumentos tipados de la
función, igual que FastAPI, que es lo que usa la empresa. El esquema queda en `/docs/openapi.json` y Swagger
UI en `/docs/swagger`.

**8. Rutas en la raíz** (`/movies`), como pide la consigna. El front las consume desde el mismo origen, a
través de `/api/` en el proxy reverso, así que CORS no hace falta.

**9. Filtro por país repetible.** `country` se puede repetir (`?country=Russia&country=Soviet Union`) y
devuelve las películas de cualquiera de esos países. Así, el mapa pide un país junto con los países históricos
que se pintan sobre él en un solo pedido ([ADR 0009](0009-browse-by-country.md)). `GET /countries` devuelve
cada nombre del CSV con su cantidad de películas y el país del mapa donde se pinta.

## Consecuencias

- Cada decisión tiene tests: la paginación en los bordes, los 400 con su formato, la lista blanca de `sort` y
  los nombres de los campos.
- Pasar `$` a `USD` queda como detalle de la regla 3 del ADR 0003.
- La interfaz tiene que traducir a español los códigos de error y mostrar los montos con su moneda.
