/**
 * Generated posters (ADR 0010): the CSV has no images, so each card is a poster made from the movie's data.
 * The composition comes from a hash of the id, so a movie always looks the same and the grid looks varied.
 */

export type Family = 'drama' | 'comedia' | 'romance' | 'accion' | 'suspenso' | 'fantastico' | 'familia' | 'otros'

const FAMILY: Record<string, Family> = {
  Drama: 'drama',
  Biography: 'drama',
  Comedy: 'comedia',
  Romance: 'romance',
  Action: 'accion',
  Adventure: 'accion',
  War: 'accion',
  Western: 'accion',
  Thriller: 'suspenso',
  Crime: 'suspenso',
  Mystery: 'suspenso',
  Horror: 'suspenso',
  'Film-Noir': 'suspenso',
  'Sci-Fi': 'fantastico',
  Fantasy: 'fantastico',
  Animation: 'fantastico',
  Family: 'familia',
  Musical: 'familia',
  Music: 'familia',
}

/** Gradient of each family: white text on top has a contrast of 5.4:1 or more. */
export const COLORS: Record<Family, [string, string]> = {
  drama: ['#4a5d7a', '#151c27'],
  comedia: ['#9a5b0f', '#2e1a05'],
  romance: ['#a23e62', '#2c0f1b'],
  accion: ['#8e3b2e', '#250d09'],
  suspenso: ['#2f3b3a', '#0a0f0f'],
  fantastico: ['#2f6b58', '#0a2019'],
  familia: ['#6a4c93', '#1c1330'],
  otros: ['#6b6255', '#1d1a15'],
}

export type Template = 'gradient' | 'frame' | 'circle' | 'bands'
const TEMPLATES: Template[] = ['gradient', 'frame', 'circle', 'bands']

export interface PosterDesign {
  template: Template
  family: Family
  colors: [string, string]
  angle: number
  /** Title size, in % of the poster width: shorter titles go bigger. */
  titleSize: number
}

/** FNV-1a: a small, stable hash of a string. */
export function hash(text: string): number {
  let value = 2166136261
  for (const char of text) {
    value ^= char.codePointAt(0)!
    value = Math.imul(value, 16777619)
  }
  return value >>> 0
}

export function familyOf(genres: string[]): Family {
  const genre = genres[0]
  return genre !== undefined && Object.hasOwn(FAMILY, genre) ? FAMILY[genre] : 'otros'
}

export function posterDesign(movie: { imdb_title_id: string; original_title: string; genres: string[] }): PosterDesign {
  const value = hash(movie.imdb_title_id)
  const family = familyOf(movie.genres)
  const length = movie.original_title.length
  const titleSize = length <= 8 ? 17 : length <= 14 ? 14 : length <= 22 ? 11.5 : length <= 34 ? 9.5 : length <= 50 ? 8 : 6.5
  return {
    template: TEMPLATES[value % TEMPLATES.length],
    family,
    colors: COLORS[family],
    angle: 150 + ((value >>> 4) % 60),
    titleSize,
  }
}
