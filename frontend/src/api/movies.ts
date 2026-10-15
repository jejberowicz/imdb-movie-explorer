import { getJson } from './client'

export type SortField = 'relevance' | 'rating' | 'year' | 'votes' | 'duration' | 'title'
export type SortOrder = 'asc' | 'desc'

export interface MovieSummary {
  imdb_title_id: string
  original_title: string
  year: number
  genres: string[]
  directors: string[] | null
  countries: string[] | null
  duration: number
  avg_vote: number
  votes: number
  weighted_rating: number
}

export interface Money {
  amount: number
  currency: string
}

export interface MovieDetail extends MovieSummary {
  italian_title: string
  languages: string[] | null
  writers: string[] | null
  production_company: string | null
  actors: string[] | null
  description: string | null
  metascore: number | null
  reviews_from_users: number | null
  reviews_from_critics: number | null
  budget: Money | null
  usa_gross_income: Money | null
  worldwide_gross_income: Money | null
  imdb_url: string
}

export interface Page<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface GenreCount {
  name: string
  movies: number
}

export interface CountryCount {
  name: string
  movies: number
  map_code: string | null
  former: boolean
}

export interface YearCount {
  year: number
  movies: number
}

export interface MovieQuery {
  title?: string
  page?: number
  pageSize?: number
  sort?: SortField
  order?: SortOrder
  genres?: string[]
  countries?: string[]
  decades?: number[]
  yearFrom?: number
  yearTo?: number
}

export function fetchMovies(query: MovieQuery, signal?: AbortSignal): Promise<Page<MovieSummary>> {
  return getJson(
    '/movies',
    {
      title: query.title,
      page: query.page,
      page_size: query.pageSize,
      sort: query.sort,
      order: query.order,
      genre: query.genres,
      country: query.countries,
      decade: query.decades,
      year_from: query.yearFrom,
      year_to: query.yearTo,
    },
    signal,
  )
}

export function fetchMovie(id: string, signal?: AbortSignal): Promise<MovieDetail> {
  return getJson(`/movies/${encodeURIComponent(id)}`, {}, signal)
}

export function fetchGenres(signal?: AbortSignal): Promise<{ items: GenreCount[] }> {
  return getJson('/genres', {}, signal)
}

export function fetchCountries(signal?: AbortSignal): Promise<{ items: CountryCount[] }> {
  return getJson('/countries', {}, signal)
}

export function fetchYears(signal?: AbortSignal): Promise<{ items: YearCount[] }> {
  return getJson('/years', {}, signal)
}
