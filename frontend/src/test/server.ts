import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import type { MovieDetail, MovieSummary, Page } from '../api/movies'
import { fold } from '../lib/text'
import { COUNTRIES, DETAILS, GENRES } from './fixtures'

export function summary(movie: MovieDetail): MovieSummary {
  const { imdb_title_id, original_title, year, genres, directors, duration, avg_vote, votes, weighted_rating } = movie
  return { imdb_title_id, original_title, year, genres, directors, duration, avg_vote, votes, weighted_rating }
}

const SORT_KEYS: Record<string, (movie: MovieDetail) => number | string> = {
  relevance: (movie) => movie.votes,
  rating: (movie) => movie.weighted_rating,
  votes: (movie) => movie.votes,
  year: (movie) => movie.year,
  duration: (movie) => movie.duration,
  title: (movie) => movie.original_title,
}

/** GET /movies over the fixtures, like the API: search in both titles, filters, order and pages. */
export function listMovies(url: URL): Page<MovieSummary> {
  const params = url.searchParams
  const title = fold(params.get('title') ?? '')
  const genre = params.get('genre')
  const countries = params.getAll('country')
  const from = Number(params.get('year_from') ?? 0)
  const to = Number(params.get('year_to') ?? 9999)
  const sort = params.get('sort') ?? (title ? 'relevance' : 'rating')
  const order = params.get('order') ?? (sort === 'title' ? 'asc' : 'desc')
  const page = Number(params.get('page') ?? 1)
  const size = Number(params.get('page_size') ?? 20)
  const key = SORT_KEYS[sort]
  const found = DETAILS.filter(
    (movie) =>
      (!title || fold(movie.original_title).includes(title) || fold(movie.italian_title).includes(title)) &&
      (!genre || movie.genres.includes(genre)) &&
      (!countries.length || countries.some((country) => movie.countries?.includes(country))) &&
      movie.year >= from &&
      movie.year <= to,
  ).sort((a, b) => {
    const compared = key(a) < key(b) ? -1 : key(a) > key(b) ? 1 : 0
    return order === 'asc' ? compared : -compared
  })
  return {
    items: found.slice((page - 1) * size, page * size).map(summary),
    page,
    page_size: size,
    total: found.length,
    total_pages: Math.ceil(found.length / size),
  }
}

export function problem(status: number, detail: string) {
  return HttpResponse.json(
    { type: 'about:blank', title: 'Error', status, detail },
    { status, headers: { 'Content-Type': 'application/problem+json' } },
  )
}

/** Records the URL of each GET /movies, still answered from the fixtures. */
export function recordMovieRequests(): URL[] {
  const seen: URL[] = []
  server.use(
    http.get('/api/movies', ({ request }) => {
      const url = new URL(request.url)
      seen.push(url)
      return HttpResponse.json(listMovies(url))
    }),
  )
  return seen
}

export const server = setupServer(
  http.get('/api/movies', ({ request }) => HttpResponse.json(listMovies(new URL(request.url)))),
  http.get('/api/movies/:id', ({ params }) => {
    const movie = DETAILS.find((item) => item.imdb_title_id === params.id)
    return movie ? HttpResponse.json(movie) : problem(404, `Movie ${String(params.id)} not found.`)
  }),
  http.get('/api/genres', () => HttpResponse.json({ items: GENRES })),
  http.get('/api/countries', () => HttpResponse.json({ items: COUNTRIES })),
)
