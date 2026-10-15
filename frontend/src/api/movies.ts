import { getJson } from './client'

export interface MovieSummary {
  imdb_title_id: string
  original_title: string
  year: number
  genres: string[]
  directors: string[]
  duration: number
  avg_vote: number
  votes: number
  weighted_rating: number
}

export interface Page<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface MovieQuery {
  title?: string
  page?: number
  pageSize?: number
}

export function fetchMovies(query: MovieQuery, signal?: AbortSignal): Promise<Page<MovieSummary>> {
  return getJson('/movies', { title: query.title, page: query.page, page_size: query.pageSize }, signal)
}
