# Plan de seguridad

La seguridad tiene que ser proporcional al riesgo. Esto es un catálogo público de solo lectura, sin cuentas ni
datos personales: no hay secretos de usuarios que proteger, pero sí la disponibilidad del servicio, la
integridad de los datos, las credenciales de la base y a quien usa la interfaz. Cada medida responde a una
amenaza concreta; las que serían sobreingeniería para este caso están en «Riesgos aceptados».

## Amenazas y medidas

| Amenaza | Medida | Fase |
|---|---|---|
| Inyección SQL | Consultas siempre parametrizadas. `ORDER BY` no se puede parametrizar, así que `sort` y `order` pasan por una lista blanca. Los comodines de `LIKE` se escapan | 1 a 3 |
| Entradas abusivas: títulos enormes, `page_size` gigante | Validación con Pydantic: tipos, rangos y largos máximos. `title` acepta hasta 200 caracteres y `page_size` hasta 100 | 3 |
| Una consulta inesperadamente cara | `statement_timeout` por defecto en el usuario de la API: ninguna consulta puede tomar el servidor por más de unos segundos, y la API responde 503 | 5 |
| Abuso por volumen: scraping o saturación | Límite de pedidos por IP con Flask-Limiter. Con el almacenamiento en memoria, el límite es por worker de Gunicorn; en producción iría en Redis. Queda documentado | 5 |
| XSS con datos del CSV | Los datos se tratan como no confiables: React escapa todo por defecto y no se usa `dangerouslySetInnerHTML`. La política de seguridad de contenido (CSP) solo permite recursos del propio origen | 4 y 5 |
| Clickjacking | `frame-ancestors 'none'` en la CSP: nadie puede embeber la app en un iframe | 5 |
| Errores que revelan detalles internos | Los errores 500 devuelven un Problem Details genérico; el detalle queda en el log, nunca en la respuesta. La base caída da 503 | 3 |
| Secretos en el repo | Las credenciales llegan por variables de entorno. `.env` está en `.gitignore` y en el repo solo está `.env.example`, sin valores reales. Los logs no imprimen credenciales | 1 |
| Escribir en la base desde la API | La API usa un usuario de la base con solo `SELECT`. Las migraciones y la carga usan otro. La base no se publica fuera de la red de Docker | 1 y 5 |
| Contenedores vulnerables | Imágenes slim con versiones fijas, procesos sin root, sin capabilities, de solo lectura, con límites de memoria y de procesos, y healthchecks | 1 y 5 |
| Dependencias con vulnerabilidades conocidas | Versiones fijadas; `pip-audit` y `npm audit` en CI | 5 |
| Pedidos desde otros orígenes | En Docker, front y API quedan en el mismo origen a través del proxy, así que CORS no se habilita. Si hiciera falta, solo para el origen del front | 1 |
| Headers de seguridad | CSP, `X-Content-Type-Options: nosniff` y `Referrer-Policy: strict-origin-when-cross-origin`, configurados en nginx | 5 |
| Links externos | El link a IMDb lleva `rel="noopener noreferrer"`: la página abierta no puede controlar la nuestra | 4 |
| Fórmulas en un CSV exportado | Hoy no hay exportación. Si se agrega (nivel 3), las celdas que empiezan con `=`, `+`, `-`, `@`, tabulación o retorno de carro se neutralizan: el CSV actual tiene 18 | Nivel 3 |

## Riesgos aceptados

- **Sin autenticación.** No hay datos privados ni escrituras que proteger detrás de un login: agregarlo sumaría
  superficie de ataque sin beneficio.
- **Límite de pedidos por worker.** Con varios workers, el límite real es la suma de todos. Para una app local
  alcanza; Redis lo resolvería en producción.
- **HTTP sin TLS en local.** En un despliegue real, TLS va en el proxy reverso.
- **Datos de IMDb en un repo público.** Se incluyen solo para correr el desafío, sin fines comerciales, y el
  README lo aclara ([ADR 0006](decisions/0006-csv-versioning.md)).

## Qué queda en `SECURITY.md` (Fase 5)

Un modelo de amenazas corto, con lo de este plan ya implementado, más una sección «Qué cambiaría con datos
médicos reales»:
- autenticación y autorización (OIDC y roles);
- un registro auditable de los accesos;
- TLS y cifrado en reposo;
- minimizar y anonimizar los datos (por ejemplo, los metadatos DICOM con datos del paciente);
- logs sin datos sensibles y gestión de secretos;
- políticas de retención y la normativa: en Argentina, la Ley 25.326 trata los datos de salud como datos
  sensibles.
