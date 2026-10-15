import { http, HttpResponse } from 'msw'
import { setupServer } from 'msw/node'
import type { MovieSummary, Page } from '../api/movies'

export const MOVIES: MovieSummary[] = [
  {
    imdb_title_id: 'tt0111161',
    original_title: 'The Shawshank Redemption',
    year: 1994,
    genres: ['Drama'],
    directors: ['Frank Darabont'],
    duration: 142,
    avg_vote: 9.3,
    votes: 2278845,
    weighted_rating: 9.29,
  },
  {
    imdb_title_id: 'tt0068646',
    original_title: 'The Godfather',
    year: 1972,
    genres: ['Crime', 'Drama'],
    directors: ['Francis Ford Coppola'],
    duration: 175,
    avg_vote: 9.2,
    votes: 1572674,
    weighted_rating: 9.18,
  },
]

export function page(items: MovieSummary[], current = 1, size = 20): Page<MovieSummary> {
  return { items, page: current, page_size: size, total: items.length, total_pages: Math.ceil(items.length / size) }
}

/** Default handlers: GET /api/movies filters the two sample movies by title, like the real API. */
export const server = setupServer(
  http.get('/api/movies', ({ request }) => {
    const title = new URL(request.url).searchParams.get('title')?.toLowerCase() ?? ''
    return HttpResponse.json(page(MOVIES.filter((movie) => movie.original_title.toLowerCase().includes(title))))
  }),
)
