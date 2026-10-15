/** The 25 genres of the CSV in Spanish (ADR 0002). An unknown genre is shown as it comes, in English. */
export const GENRES_ES: Record<string, string> = {
  Drama: 'Drama',
  Comedy: 'Comedia',
  Romance: 'Romance',
  Action: 'Acción',
  Thriller: 'Suspenso',
  Crime: 'Policial',
  Horror: 'Terror',
  Adventure: 'Aventura',
  Mystery: 'Misterio',
  Family: 'Familiar',
  Fantasy: 'Fantasía',
  'Sci-Fi': 'Ciencia ficción',
  Biography: 'Biografía',
  History: 'Historia',
  War: 'Bélica',
  Animation: 'Animación',
  Musical: 'Musical',
  Music: 'Música',
  Western: 'Western',
  Sport: 'Deporte',
  'Film-Noir': 'Cine negro',
  'Reality-TV': 'Reality',
  Adult: 'Adultos',
  Documentary: 'Documental',
  News: 'Noticias',
}

// Object.hasOwn and not GENRES_ES[genre]: a genre called "constructor" or "toString" would otherwise find a
// built-in function of every object and show its code.
export const genreLabel = (genre: string): string => (Object.hasOwn(GENRES_ES, genre) ? GENRES_ES[genre] : genre)
