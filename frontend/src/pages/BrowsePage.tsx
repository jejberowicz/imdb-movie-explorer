import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useCallback, useEffect, useMemo } from 'react'
import { useNavigate, useSearchParams } from 'react-router'
import { ApiError } from '../api/client'
import { fetchMovies } from '../api/movies'
import { BrowseBar } from '../components/BrowseBar'
import { Legend } from '../components/Legend'
import { MovieGrid } from '../components/MovieGrid'
import { MovieTable } from '../components/MovieTable'
import { Pagination } from '../components/Pagination'
import { EmptyState, ErrorState, LoadingBar, PosterSkeleton } from '../components/States'
import { YearStrip } from '../components/YearStrip'
import { useCountries, useGenres, useYears } from '../hooks/useCatalog'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { useMediaQuery } from '../hooks/useMediaQuery'
import { useViewPreference } from '../hooks/useViewPreference'
import {
  type BrowseState,
  documentTitle,
  hasChoices,
  hasFilters,
  legend,
  readBrowseState,
  sectionTitle,
  toggle,
  toMovieQuery,
  writeBrowseState,
} from '../lib/browse'
import { countryLabel } from '../lib/countries'
import { countMovies } from '../lib/format'
import { genreLabel } from '../lib/genres'
import styles from './BrowsePage.module.css'

export default function BrowsePage() {
  const [params, setParams] = useSearchParams()
  const navigate = useNavigate()
  const state = useMemo(() => readBrowseState(params), [params])
  const [preferred, setView] = useViewPreference()
  // A wide table doesn't fit on a phone: narrow screens always get the cards.
  const narrow = useMediaQuery('(max-width: 680px)')
  const view = narrow ? 'cards' : preferred
  const genres = useGenres()
  const countries = useCountries()
  const years = useYears()
  const decades = useMemo(() => {
    const items = years.data?.items
    return items && [...new Set(items.map((item) => Math.floor(item.year / 10) * 10))].sort((a, b) => b - a)
  }, [years.data])

  const query = toMovieQuery(state)
  // Each combination of parameters is its own query: a slow old response never replaces a newer one, and the
  // previous results stay on screen while the next ones load (no flicker).
  // The answer carries the state it answers: while the next one loads, the legend still describes the movies
  // on screen, not the filters just chosen.
  const movies = useQuery({
    queryKey: ['movies', query],
    queryFn: async ({ signal }) => ({ page: await fetchMovies(query, signal), state }),
    placeholderData: keepPreviousData,
  })

  const change = useCallback(
    (changes: Partial<BrowseState>, replace = false) => {
      setParams(writeBrowseState({ ...readBrowseState(params), ...changes }), { replace })
    },
    [params, setParams],
  )

  const countryName = useCallback(
    (name: string) => {
      const country = countries.data?.items.find((item) => item.name === name)
      return country ? countryLabel(country) : name
    },
    [countries.data],
  )
  const labelsOf = (of: BrowseState) => ({ genres: of.genres.map(genreLabel), countries: of.countries.map(countryName) })
  useDocumentTitle(hasChoices(state) ? documentTitle(state, labelsOf(state)) : undefined)
  const data = movies.data?.page
  const shown = movies.data?.state ?? state
  const decade = state.decades.length === 1 ? state.decades[0] : undefined
  const clear = () => navigate('/')

  // A page past the last one (an old link, or fewer movies after a new load) comes back empty: go to the last
  // page instead, replacing the entry so the back button doesn't return to the empty one.
  const lastPage =
    data && !movies.isPlaceholderData && data.items.length === 0 && data.total > 0 && state.page > data.total_pages
      ? data.total_pages
      : undefined
  useEffect(() => {
    if (lastPage !== undefined) change({ page: lastPage }, true)
  }, [lastPage, change])

  return (
    <>
      <BrowseBar
        state={state}
        genres={genres.data?.items.map((genre) => genre.name) ?? []}
        decades={decades}
        onChange={change}
      />
      <section aria-labelledby="results-title">
        <div className={styles.head}>
          <h1 id="results-title" className={styles.title}>
            {sectionTitle(state)}
          </h1>
          <div className={styles.tools}>
            {/* With filters, the legend below says how many. */}
            <span aria-live="polite">{data && !hasFilters(shown) ? countMovies(data.total) : ''}</span>
            {hasChoices(state) && (
              <button type="button" className="link-button" onClick={clear}>
                Limpiar filtros
              </button>
            )}
            {!narrow && (
              <div className={styles.toggle} role="group" aria-label="Vista">
                <button type="button" aria-pressed={view === 'cards'} onClick={() => setView('cards')}>
                  Tarjetas
                </button>
                <button type="button" aria-pressed={view === 'table'} onClick={() => setView('table')}>
                  Tabla
                </button>
              </div>
            )}
          </div>
        </div>
        <LoadingBar visible={movies.isFetching && movies.isPlaceholderData} />
        {decade !== undefined && (
          <YearStrip
            decade={decade}
            years={years.data?.items.map((item) => item.year).filter((year) => year >= decade && year <= decade + 9)}
            chosen={state.years}
            onChoose={(year) =>
              change({
                years: year === undefined ? [] : toggle(state.years, year).sort((a, b) => a - b),
                yearFrom: undefined,
                yearTo: undefined,
                page: 1,
              })
            }
          />
        )}
        <div aria-live="polite">
          {hasFilters(shown) && data && data.total > 0 && (
            <Legend parts={legend(shown, data.total, labelsOf(shown))} />
          )}
        </div>

        {movies.isPending && <PosterSkeleton />}
        {movies.isError &&
          !data &&
          // A 400 doesn't change by asking again: the way out is to start over.
          (movies.error instanceof ApiError && movies.error.status === 400 ? (
            <ErrorState message="No pudimos buscar con estos filtros." onClear={clear} />
          ) : (
            <ErrorState message="No pudimos cargar las películas." onRetry={() => movies.refetch()} />
          ))}
        {/* An empty page with movies in total is past the end: the effect above is already moving to the last. */}
        {data && data.total === 0 && (
          <EmptyState query={state.q.trim()} onClear={hasChoices(state) ? clear : undefined} />
        )}
        {data && data.items.length > 0 && (
          <>
            {view === 'cards' ? (
              <MovieGrid movies={data.items} />
            ) : (
              <MovieTable
                movies={data.items}
                // Without a chosen order the API sorts by relevance with a search and by rating without one
                sort={state.sort ?? (state.q.trim() ? 'relevance' : 'rating')}
                order={state.order}
                searching={Boolean(state.q.trim())}
                countryName={countryName}
                onSort={(sort, order) => change({ sort, order, page: 1 })}
              />
            )}
            <Pagination
              page={state.page}
              totalPages={data.total_pages}
              onPage={(page) => {
                change({ page })
                window.scrollTo({ top: 0 })
              }}
            />
          </>
        )}
      </section>
    </>
  )
}
