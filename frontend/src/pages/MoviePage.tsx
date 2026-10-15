import { useQuery } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { ApiError } from '../api/client'
import { type CountryCount, fetchMovie, type Money, type MovieDetail } from '../api/movies'
import { Poster } from '../components/Poster'
import { ErrorState, NoData } from '../components/States'
import { useCountries } from '../hooks/useCatalog'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { countryLabel } from '../lib/countries'
import { formatDuration, formatMoney, formatNumber, formatRating } from '../lib/format'
import { genreLabel } from '../lib/genres'
import styles from './MoviePage.module.css'

export default function MoviePage() {
  const { id = '' } = useParams()
  const movie = useQuery({ queryKey: ['movie', id], queryFn: ({ signal }) => fetchMovie(id, signal), retry: false })
  // The Spanish names of the countries come from /countries: waiting for it avoids a flash of «USA». It is
  // usually cached already; if it fails, the names stay as in the CSV.
  const countries = useCountries()

  useDocumentTitle(movie.data && `${movie.data.original_title} (${movie.data.year})`)

  if (movie.isPending || countries.isPending) return <p className={styles.loading}>Cargando la película…</p>
  if (movie.isError) {
    const missing = movie.error instanceof ApiError && [400, 404].includes(movie.error.status)
    return (
      <>
        <BackLink />
        {missing ? (
          <div className={styles.missing}>
            <p>Esa película no está en el catálogo.</p>
            <Link to="/">Ir al inicio</Link>
          </div>
        ) : (
          <ErrorState message="No pudimos cargar la película." onRetry={() => movie.refetch()} />
        )}
      </>
    )
  }
  return <Detail movie={movie.data} countries={countries.data?.items ?? []} />
}

/** Back to the list with its filters and scroll; to the home page if the detail was opened directly. */
function BackLink() {
  const navigate = useNavigate()
  const location = useLocation()
  return (
    <button
      type="button"
      className={`link-button ${styles.back}`}
      onClick={() => (location.key === 'default' ? navigate('/') : navigate(-1))}
    >
      ← Volver
    </button>
  )
}

function Detail({ movie, countries }: { movie: MovieDetail; countries: CountryCount[] }) {
  const countryNames = movie.countries?.map((name) => {
    const country = countries.find((item) => item.name === name)
    return country ? countryLabel(country) : name
  })
  const languages = movie.languages?.map((language) => (language === 'None' ? 'Sin diálogos' : language))

  return (
    <article className={styles.detail}>
      <BackLink />
      <div className={styles.top}>
        <div className={styles.poster}>
          <Poster movie={movie} />
        </div>
        <div>
          <h1 className={styles.title} translate="no">
            {movie.original_title}
          </h1>
          <p className={styles.meta}>
            {movie.year} · {movie.genres.map(genreLabel).join(', ')} · {formatDuration(movie.duration)}
          </p>
          <p className={styles.rating}>
            <span className={styles.star} aria-hidden="true">
              ★
            </span>
            <span className="sr-only">Rating </span>
            {formatRating(movie.avg_vote)} <span className={styles.muted}>({formatNumber(movie.votes)} votos)</span>
            {movie.metascore !== null && <span className={styles.muted}> · Metascore {movie.metascore}</span>}
          </p>
          {movie.description && (
            <p className={styles.description} lang="en">
              {movie.description}
            </p>
          )}
          <a href={movie.imdb_url} target="_blank" rel="noopener noreferrer" className={styles.imdb}>
            Ver en IMDb <span aria-hidden="true">↗</span>
            <span className="sr-only"> (se abre en otra pestaña)</span>
          </a>
        </div>
      </div>

      <dl className={styles.facts}>
        <Fact label="Dirección">{list(movie.directors)}</Fact>
        <Fact label="Guion">{list(movie.writers)}</Fact>
        <Fact label="Elenco" wide>
          {list(movie.actors)}
        </Fact>
        <Fact label="Países">{list(countryNames)}</Fact>
        <Fact label="Idiomas">{list(languages)}</Fact>
        <Fact label="Productora">{movie.production_company ?? <NoData />}</Fact>
        <Fact label="Presupuesto">{money(movie.budget)}</Fact>
        <Fact label="Recaudación en EE. UU.">{money(movie.usa_gross_income)}</Fact>
        <Fact label="Recaudación mundial">{money(movie.worldwide_gross_income)}</Fact>
        <Fact label="Reseñas de usuarios">{count(movie.reviews_from_users)}</Fact>
        <Fact label="Reseñas de críticos">{count(movie.reviews_from_critics)}</Fact>
      </dl>
    </article>
  )
}

function Fact({ label, wide = false, children }: { label: string; wide?: boolean; children: ReactNode }) {
  return (
    <div className={wide ? `${styles.fact} ${styles.wide}` : styles.fact}>
      <dt>{label}</dt>
      <dd>{children}</dd>
    </div>
  )
}

const list = (items: string[] | null | undefined): ReactNode => (items?.length ? items.join(', ') : <NoData />)
const money = (value: Money | null): ReactNode => (value ? formatMoney(value) : <NoData />)
const count = (value: number | null): ReactNode => (value === null ? <NoData /> : formatNumber(value))
