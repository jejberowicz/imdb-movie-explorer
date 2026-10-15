# ADR 0010: Tarjetas sin portadas: pósters generados

- Estado: Aceptada
- Fecha: 2026-10-15

## Contexto

La vista de tarjetas se inspira en Letterboxd, donde cada tarjeta es la portada de la película. El CSV no trae
imágenes: el [perfil](../data-profile.md) no encuentra ninguna URL.

## Opciones

1. **Iniciales y un color por género.** Es simple, pero queda pobre al lado de una grilla de portadas.
2. **Tarjetas solo con texto.** Se pierde la grilla de pósters, que es lo que hace atractiva la vista.
3. **Portadas reales desde la API de TMDB**, una base de películas con una API gratuita para uso no comercial.
   Necesita una clave, que no tiene quien clone el repo. Además, la clave tendría que quedar en el backend,
   que pediría y cachearía las imágenes.
4. **Imágenes generadas con IA.** Inventarían un póster que no existe, con costo y con problemas de licencia.
5. **Pósters tipográficos generados con los datos de cada película.**

## Decisión

Opción 5. Cada tarjeta es un póster en proporción 2:3 hecho con CSS:

- **Un degradado en el color de la familia del género**, con contraste de 5,4:1 o más para el texto blanco.
- **El título grande**, con una letra angosta como la de los afiches, y como créditos, el género, el año y el
  director.
- **Una de cuatro composiciones**: degradado con el título abajo, marco con el título en cursiva, círculo de
  luz detrás del título o bandas. Se elige con un hash del `imdb_title_id`, así la grilla se ve variada y cada
  película se ve siempre igual.
- **Texto real, no una imagen:** lo leen los lectores de pantalla, se puede seleccionar y lleva
  `translate="no"`.

Las portadas de TMDB quedan para el final del nivel 3. Si hay una clave configurada, la portada real reemplaza
al póster generado; si no, se ve el generado.

## Consecuencias

- La lista de la API incluye los directores, que van en los créditos del póster.
- No hay imágenes que descargar ni servicios externos: la grilla carga al instante y funciona sin internet.
- Un test comprueba que la misma película produce siempre el mismo póster.
