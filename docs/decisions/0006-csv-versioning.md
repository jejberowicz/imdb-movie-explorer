# ADR 0006: Cómo se versiona el CSV

- Estado: Aceptada
- Fecha: 2026-10-15

## Contexto

El proyecto tiene que levantar en una máquina limpia, y la consigna pide cargar los datos desde el CSV
provisto: el archivo tiene que estar disponible después de clonar el repo. Datos del archivo (ver el
[perfil](../data-profile.md)):

- Pesa 47,9 MB; comprimido con gzip, 21,7 MB. GitHub avisa con archivos de más de 50 MB y rechaza los de más
  de 100 MB.
- Tiene finales de línea CRLF (Windows). El `.gitattributes` del repo (`* text=auto eol=lf`) convierte los
  archivos de texto a LF: si el CSV se sube tal cual, quien clone el repo recibe otro archivo, con 85.856
  bytes menos, y el perfil, que dice «CRLF», deja de reproducirse.
- El repo es público, y los datos vienen de IMDb, cuyas condiciones limitan su uso a fines personales y no
  comerciales.

## Opciones

1. **El CSV tal cual, excluido de la conversión de finales de línea.** Funciona, pero son 48 MB en el
   historial, al borde del aviso de GitHub.
2. **El CSV comprimido con gzip.** 21,7 MB. Git lo trata como binario, así que no lo convierte. Python lo lee
   con `gzip` de la librería estándar, sin descomprimirlo a disco.
3. **Git LFS.** Quien clone el repo necesita tener `git-lfs` instalado; si no, recibe un archivo de texto con un
   puntero en lugar de los datos, y la carga falla.
4. **Fuera del repo, con instrucciones para descargarlo.** El dataset original está en Kaggle, que pide una
   cuenta para descargarlo: el proyecto no levantaría con solo clonar.

## Decisión

Opción 2: `data/IMDb_movies.csv.gz`, comprimido con `gzip -9n` (`-n` deja afuera el nombre y la fecha del
archivo, así la compresión no cambia según la máquina).

- El README publica el SHA-256 del CSV original
  (`66032d99cae8414dd8695bc5265a46cfa18e1ff092d130f243d93179dee07db4`), para comprobar que
  `gunzip -c data/IMDb_movies.csv.gz | sha256sum` devuelve el mismo archivo, byte a byte.
- El `.gitattributes` marca `*.gz` como binario, para que quede explícito.
- La carga y el perfilado leen el `.gz` directamente.

## Consecuencias

- El CSV entra al repo en la Fase 1, con la carga. Hasta entonces, el perfilado sigue leyendo
  `data/IMDb_movies.csv`; en la Fase 1 pasa a leer el `.gz` y el perfil pasa a reproducirse en cualquier
  clon.
- Si el CSV cambiara, el historial sumaría otros ~22 MB por versión. No se espera que cambie.
- El README aclara el origen de los datos y que se incluyen solo para correr el desafío, sin fines comerciales.
  Si el repo tuviera que dejar de incluirlos, la opción 4 queda como alternativa.
