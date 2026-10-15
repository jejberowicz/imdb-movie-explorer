import { Link } from 'react-router'
import type { MovieSummary } from '../api/movies'
import { formatCompact, formatRating } from '../lib/format'
import styles from './MovieGrid.module.css'
import { Poster } from './Poster'

/** The cards: a poster per movie and its stats below, as in Letterboxd. */
export function MovieGrid({ movies }: { movies: MovieSummary[] }) {
  return (
    <ul className={styles.grid}>
      {movies.map((movie) => (
        <li key={movie.imdb_title_id}>
          <Link
            to={`/movies/${movie.imdb_title_id}`}
            className={styles.card}
            aria-label={`${movie.original_title} (${movie.year})`}
          >
            <Poster movie={movie} />
          </Link>
          <p className={styles.stats}>
            <span>
              <span className={styles.star} aria-hidden="true">
                ★
              </span>
              <span className="sr-only">Rating </span>
              {formatRating(movie.avg_vote)}
            </span>
            <span>{formatCompact(movie.votes)} votos</span>
          </p>
        </li>
      ))}
    </ul>
  )
}
