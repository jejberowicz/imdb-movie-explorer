# Seguridad

FakeIMDb es un catálogo público de solo lectura: 85.855 películas de IMDb, sin cuentas, sin escrituras desde la
web y sin datos personales. La seguridad está pensada para ese riesgo, y cada medida responde a una amenaza
concreta. El plan con el que se diseñó está en [docs/security-plan.md](docs/security-plan.md).

## Qué se protege

- **La disponibilidad:** que nadie pueda tirar el servicio o acapararlo con pedidos caros o masivos.
- **La integridad de los datos:** que nadie pueda cambiar ni borrar el catálogo desde la web.
- **Las credenciales de la base**, que no estén en el repo ni en los logs.
- **A quien usa la interfaz:** que los datos del CSV no puedan ejecutar código en su navegador.

## Amenazas y medidas implementadas

| Amenaza | Medida | Dónde |
|---|---|---|
| Inyección SQL | Consultas siempre parametrizadas con SQLAlchemy. `ORDER BY` no se puede parametrizar, así que `sort` y `order` pasan por una lista blanca. Los comodines `%` y `_` de `LIKE` se escapan. Un test manda `sort=title;DROP TABLE movies`: responde 400 y la tabla sigue ahí | `repositories/movies.py`, `test_acceptance.py` |
| Entradas abusivas | Pydantic valida tipos, rangos y largos: `title` hasta 200 caracteres, `page_size` hasta 100, hasta 20 países. Los textos no aceptan caracteres de control. Lo inválido responde 400 con el parámetro y el motivo | `schemas/movies.py` |
| Escribir en la base desde la API | La API se conecta con `movies_api`, que solo tiene `SELECT` y cuyas transacciones son de solo lectura. Las migraciones y la carga usan otro usuario | `db/init/01-api-reader.sh` |
| Una consulta cara que acapare la base | `statement_timeout` de 5 s en el usuario de la API. El pedido real más lento tarda unos 60 ms de punta a punta ([docs/performance.md](docs/performance.md)) | `db/init/01-api-reader.sh` |
| Abuso por volumen | 300 pedidos por minuto por IP con Flask-Limiter, y 429 con `Retry-After` al pasarse. Detrás de nginx, la IP sale de `X-Forwarded-For`, que nginx reescribe; sin proxy, ese header se ignora. Solo el healthcheck de Docker, desde adentro del contenedor, queda exento | `app/security.py` |
| XSS con datos del CSV | Los datos se tratan como no confiables: React escapa todo y no hay `dangerouslySetInnerHTML`, `innerHTML` ni `eval`. Además, la CSP solo permite scripts del propio origen, sin `unsafe-inline` | `frontend/nginx/security-headers.conf` |
| Clickjacking | `frame-ancestors 'none'` en la CSP del sitio y de la API, y `X-Frame-Options: DENY` en la API | nginx y `app/security.py` |
| Errores que revelan detalles internos | Todo error sale como Problem Details (RFC 9457). Un 500 dice «Unexpected error.»; el detalle queda solo en el log | `app/errors.py` |
| Secretos en el repo | Las contraseñas llegan por variables de entorno. `.env` está en `.gitignore` y en el repo solo hay `.env.example`, sin valores reales. Ningún log imprime la URL de la base | `.env.example` |
| Superficie expuesta | La base no se publica fuera de la red de Docker. La API se publica solo en `127.0.0.1`: el navegador entra por nginx, en el mismo origen, así que CORS no está habilitado | `docker-compose.yml` |
| Contenedores | Imágenes slim con versiones fijas, procesos sin root (la API corre con el uid 10001; nginx es la imagen sin privilegios) y healthchecks | `Dockerfile` |
| Dependencias vulnerables | Versiones fijadas (pip freeze y `package-lock.json`). `pip-audit` y `npm audit` corren en cada push. `npm ci --ignore-scripts`: ninguna dependencia puede correr código al instalarse | `.github/workflows/ci.yml` |
| Cadena de suministro del CI | Las GitHub Actions están fijadas a un commit, no a un tag que se pueda mover, y el workflow solo puede leer el repo | `.github/workflows/ci.yml` |
| Links externos | El link a IMDb lleva `rel="noopener noreferrer"`: la pestaña nueva no puede controlar la nuestra | `MoviePage.tsx` |
| Otros headers | `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `Permissions-Policy` y nginx sin su versión en las respuestas | nginx y `app/security.py` |

## Riesgos aceptados

- **No hay autenticación.** No hay datos privados ni escrituras que proteger detrás de un login: agregarlo
  sumaría superficie de ataque sin ningún beneficio.
- **El límite de pedidos es por worker.** El contador vive en la memoria de cada worker de Gunicorn, así que
  con 2 workers el límite real es el doble. Para una sola máquina alcanza; con varias, iría en Redis.
- **Sin TLS en local.** En un despliegue real, TLS se termina en el proxy reverso, con HSTS.
- **Swagger UI no lleva CSP**, porque necesita sus propios scripts. Se sirve solo en el puerto de la API, que
  está publicado en `127.0.0.1`.
- **Las contraseñas por defecto de `docker-compose.yml`** sirven solo para una base local que no se publica
  fuera de Docker. En cualquier otro entorno se cambian con `.env`.
- **La carga corre con el superusuario de la base** que crea la imagen de PostgreSQL. Solo se usa dentro de la
  red de Docker y con contraseña; la API, que es lo expuesto, usa el usuario de solo lectura. En producción,
  el dueño de las tablas sería un usuario sin privilegios de superusuario.
- **El puerto directo de la API confía en `X-Forwarded-For`**, porque en Docker siempre hay un nginx adelante.
  Alguien en esta misma máquina podría inventarse una IP para esquivar el límite; desde afuera no se llega a
  ese puerto.
- **Las imágenes se fijan por versión, no por digest**, y pip instala sin verificar hashes. Fijar digests y
  usar `--require-hashes` cerraría la cadena de suministro del todo, a cambio de más mantenimiento.
- **gzip con respuestas que repiten lo que manda el usuario** es la condición de BREACH, pero ese ataque busca
  secretos en la misma respuesta (tokens, cookies), y acá no hay ninguno.
- **Datos de IMDb en un repo público.** Se incluyen solo para correr el desafío, sin fines comerciales
  ([ADR 0006](docs/decisions/0006-csv-versioning.md)).

## Revisión de seguridad

Al terminar, revisé todo el proyecto con el código delante, capa por capa: el SQL, la validación, los
errores, los headers, el límite de pedidos, los usuarios de la base, Docker, el CI, las dependencias y el
historial de git. Probé la API corriendo con entradas hostiles: inyección en `sort`, comodines, textos y
listas de más, años cruzados, páginas enormes, métodos no permitidos, URLs de 9.000 caracteres y caracteres
de control.

Encontré y corregí tres cosas, cada una con su test:

1. **Un byte NUL (`%00`) en la búsqueda daba 500.** PostgreSQL lo rechaza, y cada pedido dejaba un stack trace
   en el log. Ahora es un 400.
2. **`/health/ready` estaba exento del límite para cualquiera.** A través de nginx es público y consulta la
   base. Ahora solo queda exento el healthcheck de Docker.
3. **Cadena de suministro y secretos:** el build del front ya no corre scripts de instalación, y ningún `.env`
   puede terminar dentro de una imagen.

Sin hallazgos en el resto:
- ni secretos ni contraseñas reales en el repo ni en el historial;
- `pip-audit` y `npm audit` sin vulnerabilidades conocidas;
- ningún `innerHTML` ni `eval` en el front;
- la CSP no se viola en ninguna pantalla, revisada con Playwright.

## Qué cambiaría con datos médicos reales

Si en vez de películas fueran estudios de pacientes (por ejemplo, imágenes DICOM con sus metadatos), el riesgo
es otro y cambian las prioridades:

- **Autenticación y autorización:** OIDC contra el proveedor de identidad de la institución, con roles
  (médico, técnico, auditor) y acceso solo a lo que cada uno necesita. Sesiones cortas y MFA.
- **Registro de accesos auditable:** quién vio qué estudio y cuándo, en un log que no se pueda modificar y que
  se revise.
- **Cifrado:** TLS en todos los saltos, también dentro de la red, y cifrado en reposo de la base, los backups
  y las imágenes.
- **Minimización y anonimización:** guardar solo lo necesario. Los metadatos DICOM traen nombre, documento,
  fecha de nacimiento e institución del paciente; para entrenar o investigar, se anonimizan o seudonimizan
  antes de que salgan del sistema clínico.
- **Logs sin datos sensibles:** ni nombres, ni identificadores de pacientes, ni el contenido de las consultas
  en los logs de la aplicación.
- **Gestión de secretos:** un vault o el gestor del proveedor de nube en vez de variables de entorno, con
  rotación.
- **Retención y borrado:** plazos definidos por tipo de dato, y borrado verificable cuando vencen.
- **Normativa:** en Argentina, la Ley 25.326 de Protección de Datos Personales trata los datos de salud como
  datos sensibles: requieren consentimiento expreso y medidas de seguridad reforzadas. Si los datos cruzan
  fronteras, aplican también las normas de cada destino (por ejemplo, GDPR o HIPAA).

## Cómo reportar un problema

Si encontrás una vulnerabilidad, escribime por privado en vez de abrir un issue público, con los pasos para
reproducirla.
