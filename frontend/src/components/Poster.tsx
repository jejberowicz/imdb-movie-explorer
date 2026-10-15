import type { CSSProperties } from 'react'
import { genreLabel } from '../lib/genres'
import { posterDesign } from '../lib/poster'
import styles from './Poster.module.css'

interface PosterProps {
  movie: { imdb_title_id: string; original_title: string; year: number; genres: string[]; directors: string[] | null }
}

/** A poster made from the movie's data (ADR 0010). The title is real text, never translated. */
export function Poster({ movie }: PosterProps) {
  const design = posterDesign(movie)
  const genre = genreLabel(movie.genres[0] ?? '')
  const director = movie.directors?.[0]
  const style = {
    '--c1': design.colors[0],
    '--c2': design.colors[1],
    '--angle': `${design.angle}deg`,
    '--title-size': design.titleSize,
  } as CSSProperties
  const title = (
    <span className={styles.title} translate="no">
      {movie.original_title}
    </span>
  )
  return (
    <div className={`${styles.poster} ${styles[design.template]}`} style={style} data-template={design.template}>
      {design.template === 'frame' ? (
        <>
          <span className={styles.meta}>{genre}</span>
          {title}
          <span className={styles.credit}>{movie.year}</span>
        </>
      ) : (
        <>
          <span className={styles.meta}>
            {genre} · {movie.year}
          </span>
          {title}
          {design.template === 'bands' && <span className={styles.stripe} aria-hidden="true" />}
          {director && <span className={styles.credit}>{director}</span>}
        </>
      )}
    </div>
  )
}
