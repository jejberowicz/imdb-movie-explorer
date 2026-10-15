# Backlog, calendario y riesgos

## Backlog por niveles

Las estimaciones son gruesas, en horas de trabajo, e incluyen los tests de cada ítem.

- **Nivel 1:** la consigna impecable.
- **Nivel 2:** alto valor y costo bajo.
- **Nivel 3:** solo si sobra tiempo y con OK explícito.

**Estado al entregar (15/10):** las fases 1 a 6 están completas, con los niveles 1 y 2. Del nivel 3 está
hecha la página por país con el mapa; lo demás queda en «Qué haría con más tiempo» del README.

### Fase 1: esqueleto que camina

Al terminar esta fase, el proyecto ya cumple lo mínimo de la consigna.

| # | Ítem | Nivel | Estimación |
|---|---|---|---:|
| 1.1 | `docker compose` con db, seed, api y web; healthchecks y versiones fijas | 1 | 3 h |
| 1.2 | Backend: app factory, configuración, Gunicorn, `/health` y Dockerfile | 1 | 2 h |
| 1.3 | CSV comprimido en el repo y seed mínimo con `COPY`. El perfilado pasa a leer el `.gz` | 1 | 2,5 h |
| 1.4 | `GET /movies` paginado y `?title=` en las dos columnas, sin acentos y con comodines escapados | 1 | 2 h |
| 1.5 | Front: Vite, React y TypeScript; lista y buscador con TanStack Query; nginx con proxy | 1 | 3 h |
| 1.6 | Un test de cada lado y un README mínimo para levantarlo | 1 | 1,5 h |

### Fase 2: datos robustos

| # | Ítem | Nivel | Estimación |
|---|---|---|---:|
| 2.1 | Alembic, el modelo final con sus `CHECK` y los dos usuarios de la base | 1 | 2 h |
| 2.2 | Las reglas del ADR 0003 como funciones puras y testeadas, más `$` → `USD` y la reparación del mojibake | 1 | 4 h |
| 2.3 | Rechazos con su motivo, resumen de la carga, umbral, idempotencia y salto por SHA-256 | 1 | 2 h |
| 2.4 | CSV de prueba a mano y tests de integración de la carga | 1 | 2 h |
| 2.5 | Índices justificados con `EXPLAIN ANALYZE`, antes y después | 2 | 1,5 h |

### Fase 3: API completa

| # | Ítem | Nivel | Estimación |
|---|---|---|---:|
| 3.1 | Validación completa con Pydantic: `sort` y `order` con lista blanca, filtros | 1 | 3 h |
| 3.2 | Errores con Problem Details | 1 | 1 h |
| 3.3 | Detalle, `GET /genres` cacheable y `/health/ready` | 2 | 1,5 h |
| 3.4 | OpenAPI con Swagger UI y colección de Postman | 2 | 1,5 h |
| 3.5 | Tests de la API y criterios de aceptación | 1 | 3 h |
| 3.6 | `GET /countries`, filtro `country` repetible y tabla de países con su código ISO | 3, aprobado | 2 h |

### Fase 4: frontend

| # | Ítem | Nivel | Estimación |
|---|---|---|---:|
| 4.1 | Búsqueda en tiempo real (debounce, cancelación, sin parpadeo) y estados de carga, vacío y error | 1 | 3 h |
| 4.2 | Dirección visual inspirada en Letterboxd: barra oscura, tipografía, paleta y tokens | 2 | 2 h |
| 4.3 | Pósters generados, vista tabla y botón para cambiar; tarjetas en mobile | 2 | 4 h |
| 4.4 | Barra «Explorar por» con sus menús, contador, «Limpiar filtros» y estado en la URL | 2 | 4 h |
| 4.5 | Detalle, link a IMDb y formatos con `Intl` | 2 | 3 h |
| 4.6 | Accesibilidad: `aria-live`, `aria-sort`, foco y teclado | 1 | 1,5 h |
| 4.7 | Tests con React Testing Library y MSW, incluida la carrera entre respuestas | 2 | 3 h |
| 4.8 | Página por país: mapa con d3-geo y lista accesible con buscador | 3, aprobado | 6 h |

### Fase 5: seguridad, rendimiento y CI

| # | Ítem | Nivel | Estimación |
|---|---|---|---:|
| 5.1 | Límite de pedidos, headers de seguridad, `statement_timeout` y contenedores sin root | 2 | 3 h |
| 5.2 | CI con GitHub Actions | 2 | 2,5 h |
| 5.3 | `SECURITY.md` | 2 | 1 h |
| 5.4 | Medición de p50 y p95, compresión gzip y cache HTTP | 2 | 2 h |

### Fase 6: documentación y entrega

| # | Ítem | Nivel | Estimación |
|---|---|---|---:|
| 6.1 | README completo: quick start, sin Docker, API con curl, decisiones, supuestos, limitaciones y qué haría con más tiempo | 1 | 3 h |
| 6.2 | Capturas | 2 | 1 h |
| 6.3 | Prueba de clone limpio, siguiendo el README al pie de la letra | 1 | 1 h |

**Total de los niveles 1 y 2: 69,5 horas de trabajo.** Con el mapa por país, que es nivel 3 pero ya está
aprobado, son 77,5 horas.

### Nivel 3: solo con tu OK

- **Aprobado:** la página por país, con el mapa ([ADR 0009](decisions/0009-browse-by-country.md)). Está en las
  fases 3 y 4.
- **Al final, en veremos:** portadas reales desde la API de TMDB, con la clave solo en el backend y el póster
  generado cuando no hay clave ([ADR 0010](decisions/0010-generated-posters.md)).
- Tests de punta a punta con Playwright.
- Tolerancia a errores de tipeo con la similitud de pg_trgm.
- Exportar a CSV, neutralizando fórmulas.
- Favoritos en `localStorage`.
- Modo claro: la interfaz ya es oscura.
- Despliegue con una URL pública, presentando antes dos opciones con sus pros y contras.
- Escaneo con OWASP ZAP.

### Fuera de alcance

Se explica en el README:
- login y usuarios, porque no hay datos ni escrituras que proteger;
- alta, baja y modificación de películas;
- microservicios, colas y Kubernetes.

## Entrega

La fecha límite es el 19/10. La entrega se adelantó al 15/10, para dejar tiempo de evaluación.

**Si falta tiempo**, se recorta en este orden, de lo nivel 2 que menos aporta a lo que más:
1. La colección de Postman: los ejemplos con curl del README cumplen la consigna.
2. La medición de p50 y p95.
3. Las capturas automatizadas: se sacan a mano.
4. El mapa por país: la lista con buscador alcanza para filtrar.

El nivel 1 no se recorta.

## Riesgos del proyecto

| Riesgo | Mitigación |
|---|---|
| Plazo corto | Backlog por niveles, orden de recorte definido y checkpoints cortos al cierre de cada fase |
| Docker en la máquina de quien evalúa: Windows, o Mac con ARM | Imágenes oficiales multiplataforma, `.gitattributes` con `eol=lf` y una prueba de clone limpio antes de entregar |
| Puertos ocupados en esa máquina | Solo se publican el 8080 y el 8000, configurables por `.env`. La base no se publica |
| Búsquedas de 1 o 2 caracteres sin índice | Medidas: unos 20 ms ([ADR 0005](decisions/0005-data-storage.md)). Aceptable con este volumen |
| Sorpresas en los datos | Perfilado reproducible, umbral de rechazos en la carga y un CSV de prueba con los casos borde |
| flask-openapi3 no encaja como se espera | Se prueba en la Fase 1 con el primer endpoint; la alternativa es spectree |
| Datos de IMDb en un repo público | Aclarado en el README ([ADR 0006](decisions/0006-csv-versioning.md)). Se puede dejar el repo privado hasta entregarlo |
| Primer `docker compose up` lento | La carga tarda unos segundos y se salta si el archivo ya está cargado |
