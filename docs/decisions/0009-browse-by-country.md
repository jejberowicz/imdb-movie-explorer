# ADR 0009: Explorar por país

- Estado: Aceptada
- Fecha: 2026-10-15

## Contexto

La interfaz permite explorar las películas por país desde un mapa del mundo, coloreado según la cantidad de
películas de cada uno. El CSV tiene 194 países, escritos como los escribe IMDb, en inglés, y 13 de ellos ya no
existen, ya sea porque se disolvieron o porque cambiaron de nombre (ver el [perfil](../data-profile.md)): West
Germany (1.114 películas), Soviet Union (866), Yugoslavia (395), Czechoslovakia (313) y otros nueve con menos
de 100. Un mapa actual no tiene dónde pintarlos.

## Opciones

1. **Listar los países históricos aparte, sin pintarlos.** Es fiel al dato, pero el mapa queda incompleto: más
   de 2.800 películas no aparecen en ningún país.
2. **Repartir cada país histórico entre todos sus sucesores**, por ejemplo la Unión Soviética entre 15
   países. Exagera: una película soviética no es de los 15.
3. **Pintar cada país histórico sobre un sucesor, y conservar el nombre original en una lista aparte.**

## Decisión

Opción 3. En el mapa, cada país histórico se suma a un sucesor:

| En el CSV | Se pinta sobre |
|---|---|
| Soviet Union | Rusia, el Estado que continuó a la Unión Soviética |
| West Germany, East Germany | Alemania |
| Yugoslavia, Federal Republic of Yugoslavia, Serbia and Montenegro | Serbia, que continuó a esos Estados |
| Czechoslovakia | República Checa |
| Netherlands Antilles | Países Bajos |
| North Vietnam | Vietnam |
| Burma, Zaire, Swaziland | Myanmar, República Democrática del Congo y Esuatini: son los mismos países, con otro nombre |
| Korea (una película de 1936, anterior a la división) | Corea del Sur |

- **El mapa aclara qué suma cada país.** Muestra las películas de cada país más las de los históricos que se le
  asignan, y el texto que aparece al pasar el mouse lo indica, por ejemplo: «Rusia (incluye Unión
  Soviética)».
- **La lista conserva el dato exacto.** Debajo del mapa, una lista con buscador muestra los 194 nombres tal como
  vienen en el CSV, con su cantidad. Ahí la Unión Soviética aparece sola. Además, la lista es la alternativa
  accesible, porque un mapa no se puede usar con el teclado ni con un lector de pantalla.
- **La correspondencia entre nombres y códigos ISO está en el backend.** `GET /countries` devuelve cada nombre
  con el código del país donde se pinta, y `GET /movies` acepta `country` repetido, así un clic en Rusia pide
  Rusia y la Unión Soviética juntas ([ADR 0007](0007-api-contract.md)).
- **Los nombres en español los pone la interfaz.** Para los países actuales usa `Intl.DisplayNames` con el
  código ISO; para los históricos, un diccionario propio.
- **La geometría del mapa** es Natural Earth en escala 1:110m, de dominio público.

## Consecuencias

- **Asignar un sucesor simplifica.** Una película soviética puede ser georgiana o ucraniana. Se acepta porque el
  mapa sirve para explorar, y la lista conserva el dato exacto.
- **Los países muy chicos no aparecen en el mapa**, como Mónaco o Hong Kong, porque la escala 1:110m no los
  dibuja. Sí están en la lista.
- **La tabla de correspondencias se mantiene a mano.** Un nombre nuevo sin código no se pinta, pero aparece en
  la lista. Un test comprueba que los 194 nombres actuales tengan su código.
