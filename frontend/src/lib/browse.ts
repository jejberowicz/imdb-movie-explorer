/**
 * The browse state lives in the URL (?q=&page=&genre=&country=&year_from=&year_to=&sort=&order=), so a search
 * can be shared, reloaded and undone with the back button.
 */

import type { MovieQuery, SortField, SortOrder } from '../api/movies'

export const PAGE_SIZE = 24
export const DECADES = Array.from({ length: 14 }, (_, index) => 2020 - index * 10)

const SORTS: SortField[] = ['relevance', 'rating', 'year', 'votes', 'duration', 'title']

export interface BrowseState {
  q: string
  page: number
  genre?: string
  countries: string[]
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
const MAX_COUNTRY = 60
const MAX_COUNTRIES = 20

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

export function readBrowseState(params: URLSearchParams): BrowseState {
  const sort = params.get('sort') as SortField | null
  const order = params.get('order')
  const q = Array.from(text(params.get('q') ?? ''))
    .slice(0, MAX_QUERY)
    .join('')
  const genre = text(params.get('genre') ?? '')
  const countries = params
    .getAll('country')
    .map((country) => text(country).trim())
    .filter((country) => country && length(country) <= MAX_COUNTRY)
    .slice(0, MAX_COUNTRIES)
  let yearFrom = year(params.get('year_from'))
  let yearTo = year(params.get('year_to'))
  // A reversed range is still a range: 1999 to 1990 means the 1990s.
  if (yearFrom !== undefined && yearTo !== undefined && yearFrom > yearTo) [yearFrom, yearTo] = [yearTo, yearFrom]
  return {
    q,
    page: clamp(integer(params.get('page')) ?? 1, 1, MAX_PAGE),
    genre: genre && length(genre) <= MAX_GENRE ? genre : undefined,
    countries,
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
  if (state.genre) params.set('genre', state.genre)
  for (const country of state.countries) params.append('country', country)
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
    genre: state.genre,
    countries: state.countries.length ? state.countries : undefined,
    yearFrom: state.yearFrom,
    yearTo: state.yearTo,
  }
}

/** The decade chosen in the Año menu, if the year range is exactly one. */
export function decadeOf(state: BrowseState): number | undefined {
  const { yearFrom, yearTo } = state
  return yearFrom !== undefined && yearFrom % 10 === 0 && yearTo === yearFrom + 9 ? yearFrom : undefined
}

export function hasFilters(state: BrowseState): boolean {
  return Boolean(
    state.q.trim() ||
      state.genre ||
      state.countries.length ||
      state.yearFrom !== undefined ||
      state.yearTo !== undefined ||
      state.sort,
  )
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

/** The title of the results: what is being shown, in words. */
export function sectionTitle(state: BrowseState, labels: { genre?: string; countries?: string }): string {
  const parts: string[] = []
  const query = state.q.trim()
  if (query) parts.push(`Resultados para «${query}»`)
  // A search is ordered by relevance unless another order is chosen: that one needs no words.
  if (!query || (state.sort && state.sort !== 'relevance')) {
    const sort = state.sort && state.sort !== 'relevance' ? state.sort : 'rating'
    const order = state.order ?? (sort === 'title' ? 'asc' : 'desc')
    parts.push(ORDER_TITLES[`${sort}-${order}`])
  }
  if (labels.genre) parts.push(labels.genre)
  const decade = decadeOf(state)
  if (decade !== undefined) parts.push(`${decade}s`)
  else if (state.yearFrom !== undefined || state.yearTo !== undefined)
    parts.push(`${state.yearFrom ?? '…'}–${state.yearTo ?? '…'}`)
  if (labels.countries) parts.push(labels.countries)
  return parts.join(' · ')
}
