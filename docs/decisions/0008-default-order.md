# ADR 0008: Orden por defecto del listado

- Estado: Aceptada
- Fecha: 2026-10-15

## Contexto

Sin búsqueda, `GET /movies` devuelve la primera página de 85.855 películas, y lo primero que ve el usuario
depende del orden. El [perfil](../data-profile.md) muestra que el rating crudo engaña: la mitad de las
películas tiene menos de 500 votos, y ordenando por `avg_vote` la primera es *Suvarna Sundari* (9,9 con 896
votos), seguida de otras películas con menos de mil votos.

## Opciones

1. **`avg_vote` crudo.** Premia a las películas con pocos votos.
2. **Cantidad de votos.** Muestra las más populares, no las mejor valoradas.
3. **`avg_vote` con un mínimo de votos** (por ejemplo, 10.000). Funciona como filtro, pero el corte es
   arbitrario: una película con 9.999 votos desaparece del ranking, y otra con 10.000 entra con el mismo peso
   que una con un millón.
4. **Año, de la más nueva a la más vieja.** Abre con estrenos recientes con pocos votos.
5. **Rating ponderado estilo IMDb:** WR = v/(v+m)·R + m/(v+m)·C. Cada película parte de la media global (C) y
   se acerca a su propio rating (R) a medida que suma votos (v). m es la cantidad de votos con la que su rating
   pesa lo mismo que la media.

## Decisión

Opción 5, con C = media de `avg_vote` (5,90) y m = percentil 90 de los votos (9.820). Con estos valores, los
primeros son *The Shawshank Redemption* (9,29), *The Godfather* (9,18), *The Dark Knight* (8,99), *The
Godfather: Part II* (8,97) y *Pulp Fiction* (8,88), y *Suvarna Sundari* baja al puesto 8.439.

- **m es el percentil 90 de los votos**, una convención habitual para esta fórmula, y sale de los propios
  datos: para que su rating pese lo mismo que la media, una película necesita tantos votos como el 10 % más
  votado. Con este valor se cumple el criterio de aceptación: Shawshank y The Godfather arriba, *Suvarna
  Sundari* lejos.
- **Se calcula en la carga** y se guarda en una columna indexada: ordenar no cuesta nada en cada request. C y
  m quedan en el resumen de la carga.
- **Es el orden por defecto sin búsqueda, y `sort=rating` lo aplica en cualquier caso.** Con búsqueda, el orden
  por defecto es la relevancia ([ADR 0004](0004-title-search-requirements.md)).
- **La interfaz sigue mostrando `avg_vote`**, el rating que la gente conoce de IMDb, junto a la cantidad de
  votos. El rating ponderado solo ordena, y un texto de ayuda explica que tiene en cuenta la cantidad de votos. Ese
  texto está en la vista tabla, arriba de las filas; las tarjetas no lo tienen.

## Consecuencias

- Hay un test de aceptación: ordenando por rating ponderado, Shawshank y The Godfather están arriba y
  *Suvarna Sundari* no.
- Si cambian los datos, C y m se recalculan en la carga siguiente, y el orden se ajusta solo.
- El orden por `avg_vote` crudo no se ofrece, porque es justamente el que engaña.
