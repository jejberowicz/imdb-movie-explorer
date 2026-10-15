/**
 * The browse state lives in the URL (?q=&page=&genre=&country=&decade=&year=&year_from=&year_to=&sort=&order=), so
 * a search can be shared, reloaded and undone with the back button. Genre, country, decade and year can repeat.
 */

import type { MovieQuery, SortField, SortOrder } from '../api/movies'
import { countMovies } from './format'

export const PAGE_SIZE = 24
/** The decades of the Año menu until GET /years answers. */
export const DECADES = Array.from({ length: 14 }, (_, index) => 2020 - index * 10)

const SORTS: SortField[] = ['relevance', 'rating', 'year', 'votes', 'duration', 'title']

export interface BrowseState {
  q: string
  page: number
  /** Movies with all of them. */
  genres: string[]
  /** Movies of any of them. */
  countries: string[]
  /** Movies of any of them: the first year of each decade, newest first. */
  decades: number[]
  /** Movies of any of them, oldest first: the years chosen in the strip of the only decade. */
  years: number[]
  yearFrom?: number
  yearTo?: number
  sort?: SortField
  order?: SortOrder
}

// The limits of GET /movies (backend/app/schemas/movies.py): past them the API answers 400, and a shared or
// edited URL must not leave the page on an error that no retry can fix.
const MAX_PAGE = 100_000
const FIRST_YEAR = 1880
const LAST_YEAR = 2100
const MAX_QUERY = 200
const MAX_GENRE = 40
const MAX_GENRES = 10
const MAX_COUNTRY = 60
const MAX_COUNTRIES = 20
const MAX_YEARS = 50

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max)

function integer(value: string | null): number | undefined {
  if (value === null || !/^[0-9]+$/.test(value)) return undefined
  return Number(value)
}

function year(value: string | null): number | undefined {
  const number = integer(value)
  return number === undefined ? undefined : clamp(number, FIRST_YEAR, LAST_YEAR)
}

/** The API rejects control characters; none is in a title, a genre or a country. */
const text = (value: string) => value.replace(/\p{Cc}/gu, '')
/** Length as the API counts it: characters, not UTF-16 units. */
const length = (value: string) => Array.from(value).length

/** Each value once, in the order it came, up to `max`. */
function list(values: string[], maxLength: number, max: number): string[] {
  const kept = values.map((value) => text(value).trim()).filter((value) => value && length(value) <= maxLength)
  return [...new Set(kept)].slice(0, max)
}

export function readBrowseState(params: URLSearchParams): BrowseState {
  const sort = params.get('sort') as SortField | null
  const order = params.get('order')
  const q = Array.from(text(params.get('q') ?? ''))
    .slice(0, MAX_QUERY)
    .join('')
  const decades = params
    .getAll('decade')
    .map(integer)
    .filter((decade): decade is number => decade !== undefined && decade % 10 === 0)
    .filter((decade) => decade >= FIRST_YEAR && decade <= LAST_YEAR)
  const years = params
    .getAll('year')
    .map(integer)
    .filter((year): year is number => year !== undefined && year >= FIRST_YEAR && year <= LAST_YEAR)
  let yearFrom = year(params.get('year_from'))
  let yearTo = year(params.get('year_to'))
  // A reversed range is still a range: 1999 to 1990 means the 1990s.
  if (yearFrom !== undefined && yearTo !== undefined && yearFrom > yearTo) [yearFrom, yearTo] = [yearTo, yearFrom]
  return {
    q,
    page: clamp(integer(params.get('page')) ?? 1, 1, MAX_PAGE),
    genres: list(params.getAll('genre'), MAX_GENRE, MAX_GENRES),
    countries: list(params.getAll('country'), MAX_COUNTRY, MAX_COUNTRIES),
    decades: [...new Set(decades)].sort((a, b) => b - a),
    years: [...new Set(years)].sort((a, b) => a - b).slice(0, MAX_YEARS),
    yearFrom,
    yearTo,
    // Relevance only means something with a search: without one, the default order (the rating).
    sort: sort && SORTS.includes(sort) && (sort !== 'relevance' || q.trim()) ? sort : undefined,
    order: order === 'asc' || order === 'desc' ? order : undefined,
  }
}

export function writeBrowseState(state: BrowseState): URLSearchParams {
  const params = new URLSearchParams()
  if (state.q.trim()) params.set('q', state.q.trim())
  for (const genre of state.genres) params.append('genre', genre)
  for (const country of state.countries) params.append('country', country)
  for (const decade of state.decades) params.append('decade', String(decade))
  for (const year of state.years) params.append('year', String(year))
  if (state.yearFrom !== undefined) params.set('year_from', String(state.yearFrom))
  if (state.yearTo !== undefined) params.set('year_to', String(state.yearTo))
  // Clearing the search leaves sort=relevance behind: the API rejects it without a title.
  if (state.sort && (state.sort !== 'relevance' || state.q.trim())) params.set('sort', state.sort)
  if (state.order) params.set('order', state.order)
  if (state.page > 1) params.set('page', String(state.page))
  return params
}

/** A path with the state in its query string: "/" or "/?genre=Drama". */
export function browsePath(state: BrowseState, pathname = '/'): string {
  const search = writeBrowseState(state).toString()
  return search ? `${pathname}?${search}` : pathname
}

/** What the API needs for this state. */
export function toMovieQuery(state: BrowseState): MovieQuery {
  return {
    title: state.q.trim() || undefined,
    page: state.page,
    pageSize: PAGE_SIZE,
    sort: state.sort,
    order: state.order,
    genres: state.genres.length ? state.genres : undefined,
    countries: state.countries.length ? state.countries : undefined,
    decades: state.decades.length ? state.decades : undefined,
    years: state.years.length ? state.years : undefined,
    yearFrom: state.yearFrom,
    yearTo: state.yearTo,
  }
}

/** A list in words: "A", "A y B", "A, B y C". */
export function inWords(items: string[], last = 'y'): string {
  return items.length < 2 ? (items[0] ?? '') : `${items.slice(0, -1).join(', ')} ${last} ${items.at(-1)}`
}

/** Adds the value if it isn't there and takes it out if it is: the menus that allow several. */
export function toggle<T>(values: T[], value: T): T[] {
  return values.includes(value) ? values.filter((item) => item !== value) : [...values, value]
}

/** A filter is chosen: genre, country, year or a search. The order alone isn't one. */
export function hasFilters(state: BrowseState): boolean {
  return Boolean(
    state.q.trim() ||
      state.genres.length ||
      state.countries.length ||
      state.decades.length ||
      state.years.length ||
      state.yearFrom !== undefined ||
      state.yearTo !== undefined,
  )
}

/** Something differs from the start page, so there is something to clear. */
export function hasChoices(state: BrowseState): boolean {
  return hasFilters(state) || Boolean(state.sort)
}

const ORDER_TITLES: Record<string, string> = {
  'rating-desc': 'Mejor valoradas',
  'rating-asc': 'Peor valoradas',
  'votes-desc': 'Más votadas',
  'votes-asc': 'Menos votadas',
  'title-asc': 'De la A a la Z',
  'title-desc': 'De la Z a la A',
  'year-desc': 'Más nuevas',
  'year-asc': 'Más viejas',
  'duration-desc': 'Más largas',
  'duration-asc': 'Más cortas',
}

/** The title of the results: the search and the order. The filters are told by the legend below. */
export function sectionTitle(state: BrowseState): string {
  const parts: string[] = []
  const query = state.q.trim()
  if (query) parts.push(`Resultados para «${query}»`)
  // A search is ordered by relevance unless another order is chosen: that one needs no words.
  if (!query || (state.sort && state.sort !== 'relevance')) {
    const sort = state.sort && state.sort !== 'relevance' ? state.sort : 'rating'
    const order = state.order ?? (sort === 'title' ? 'asc' : 'desc')
    parts.push(ORDER_TITLES[`${sort}-${order}`])
  }
  return parts.join(' · ')
}

export interface FilterLabels {
  /** The chosen genres and countries, in Spanish. */
  genres: string[]
  countries: string[]
}

/** When the movies were released, as [words, values]: ["en los ", "1990s y 2000s"], ["entre ", "1950 y 1960"]. */
function released(state: BrowseState): [string, string][] {
  const phrases: [string, string][] = []
  // The years chosen in the strip are already inside the decade: saying it too would be redundant.
  if (state.years.length) phrases.push(['en ', inWords(state.years.map(String))])
  else if (state.decades.length) phrases.push(['en los ', inWords([...state.decades].reverse().map((decade) => `${decade}s`))])
  const { yearFrom, yearTo } = state
  if (yearFrom !== undefined && yearFrom === yearTo) phrases.push(['en ', String(yearFrom)])
  else if (yearFrom !== undefined && yearTo !== undefined) phrases.push(['entre ', `${yearFrom} y ${yearTo}`])
  else if (yearFrom !== undefined) phrases.push(['desde ', String(yearFrom)])
  else if (yearTo !== undefined) phrases.push(['hasta ', String(yearTo)])
  return phrases
}

/** A piece of the legend: the values chosen go in bold. */
export type LegendPart = string | { strong: string }

/**
 * What the filters leave, in a sentence, as Letterboxd does: "Hay 1.474 películas del género Drama, hechas en
 * Italia, estrenadas en los 2010s".
 */
export function legend(state: BrowseState, total: number, labels: FilterLabels): LegendPart[] {
  const clauses: LegendPart[][] = []
  const plural = total === 1 ? '' : 's'
  const { genres, countries } = labels
  if (genres.length) clauses.push([genres.length === 1 ? 'del género ' : 'de los géneros ', { strong: inWords(genres) }])
  if (countries.length) clauses.push([`hecha${plural} en `, { strong: inWords(countries, 'o') }])
  released(state).forEach(([words, value], index) =>
    clauses.push([index ? words : `estrenada${plural} ${words}`, { strong: value }]),
  )
  if (state.q.trim()) clauses.push(['con ', { strong: `«${state.q.trim()}»` }, ' en el título'])
  return ['Hay ', { strong: countMovies(total) }, ...clauses.flatMap((clause, index) => [index ? ', ' : ' ', ...clause]), '.']
}

/** The page title of the browser: the order, then each filter. */
export function documentTitle(state: BrowseState, labels: FilterLabels): string {
  return [
    sectionTitle(state),
    inWords(labels.genres),
    ...released(state).map(([, value]) => value),
    inWords(labels.countries, 'o'),
  ]
    .filter(Boolean)
    .join(' · ')
}
