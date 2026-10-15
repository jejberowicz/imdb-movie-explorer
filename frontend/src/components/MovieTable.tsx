import { useId } from 'react'
import { Link } from 'react-router'
import type { MovieSummary, SortField, SortOrder } from '../api/movies'
import { formatDuration, formatNumber, formatRating } from '../lib/format'
import { genreLabel } from '../lib/genres'
import styles from './MovieTable.module.css'

interface MovieTableProps {
  movies: MovieSummary[]
  sort?: SortField
  order?: SortOrder
  /** With a search and no order chosen, the API orders by relevance; without one, by rating. */
  searching: boolean
  /** The name of a country in Spanish, from GET /countries. */
  countryName?: (name: string) => string
  onSort: (sort: SortField, order: SortOrder) => void
}

const COLUMNS: { label: string; sort?: SortField; numeric?: boolean }[] = [
  { label: 'Título', sort: 'title' },
  { label: 'Año', sort: 'year' },
  { label: 'Géneros' },
  { label: 'País' },
  { label: 'Duración', sort: 'duration' },
  { label: 'Rating', sort: 'rating', numeric: true },
  { label: 'Votos', sort: 'votes', numeric: true },
]

const defaultOrder = (sort: SortField): SortOrder => (sort === 'title' ? 'asc' : 'desc')

/** The table view. A sortable header orders by its column; a second click reverses the order. */
export function MovieTable({ movies, sort, order, searching, countryName = (name) => name, onSort }: MovieTableProps) {
  const current = sort === 'relevance' ? undefined : sort
  const currentOrder = order ?? (current ? defaultOrder(current) : undefined)
  const byRating = sort === 'rating' || (!sort && !searching)
  const noteId = useId()

  return (
    <div className={styles.scroll}>
      {/* The column shows the IMDb average, the number people know, but the order is by the weighted rating
          (ADR 0008): without this note, a sort by rating looks out of order. */}
      {byRating && (
        <p id={noteId} className={styles.note}>
          El orden por rating tiene en cuenta la cantidad de votos: con pocos votos, una película no llega a los
          extremos aunque su promedio sea muy alto o muy bajo.
        </p>
      )}
      <table className={styles.table} aria-describedby={byRating ? noteId : undefined}>
        <thead>
          <tr>
            {COLUMNS.map((column) => {
              const active = column.sort !== undefined && column.sort === current
              const ariaSort = active ? (currentOrder === 'asc' ? 'ascending' : 'descending') : undefined
              return (
                <th
                  key={column.label}
                  scope="col"
                  aria-sort={column.sort ? (ariaSort ?? 'none') : undefined}
                  className={column.numeric ? styles.numeric : undefined}
                >
                  {column.sort ? (
                    <button
                      type="button"
                      className={styles.sortButton}
                      onClick={() => {
                        const next = active ? (currentOrder === 'asc' ? 'desc' : 'asc') : defaultOrder(column.sort!)
                        onSort(column.sort!, next)
                      }}
                    >
                      {column.label}
                      <span aria-hidden="true">{active ? (currentOrder === 'asc' ? ' ▲' : ' ▼') : ''}</span>
                    </button>
                  ) : (
                    column.label
                  )}
                </th>
              )
            })}
          </tr>
        </thead>
        <tbody>
          {movies.map((movie) => (
            <tr key={movie.imdb_title_id}>
              <td>
                <Link to={`/movies/${movie.imdb_title_id}`} className={styles.title} translate="no">
                  {movie.original_title}
                </Link>
              </td>
              <td>{movie.year}</td>
              <td>{movie.genres.map(genreLabel).join(', ')}</td>
              <td>{movie.countries?.map(countryName).join(', ') ?? '—'}</td>
              <td className={styles.nowrap}>{formatDuration(movie.duration)}</td>
              <td className={styles.numeric}>{formatRating(movie.avg_vote)}</td>
              <td className={styles.numeric}>{formatNumber(movie.votes)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
