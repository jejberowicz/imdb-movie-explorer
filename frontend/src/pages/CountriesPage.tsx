import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { ErrorState } from '../components/States'
import { WorldMap } from '../features/countries/WorldMap'
import { useCountries } from '../hooks/useCatalog'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import { browsePath, readBrowseState } from '../lib/browse'
import { countryLabel, regions } from '../lib/countries'
import { formatNumber } from '../lib/format'
import { fold } from '../lib/text'
import styles from './CountriesPage.module.css'

/** The map and the list of countries (ADR 0009). It loads on its own, so d3 and the map only come here. */
export default function CountriesPage() {
  useDocumentTitle('Por país')
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const countries = useCountries()
  const [text, setText] = useState('')

  // The filters chosen before opening the map stay; the country replaces the one chosen before, if any.
  const browse = readBrowseState(params)
  const pathFor = (names: string[]) => browsePath({ ...browse, countries: names, page: 1 })

  const items = countries.data?.items
  const byRegion = useMemo(() => regions(items ?? []), [items])
  const list = useMemo(
    () =>
      (items ?? [])
        .map((country) => ({ ...country, label: countryLabel(country) }))
        .sort((a, b) => a.label.localeCompare(b.label, 'es')),
    [items],
  )
  const query = fold(text)
  const shown = list.filter((country) => fold(country.label).includes(query) || fold(country.name).includes(query))

  return (
    <section aria-labelledby="countries-title" className={styles.page}>
      <div className={styles.head}>
        <h1 id="countries-title" className={styles.title}>
          Por país
        </h1>
        <Link to={browsePath(browse)}>← Volver a las películas</Link>
      </div>

      {countries.isPending && <p className={styles.note}>Cargando los países…</p>}
      {countries.isError && <ErrorState message="No pudimos cargar los países." onRetry={() => countries.refetch()} />}
      {items && (
        <>
          <p className={styles.note}>
            Los países que ya no existen se pintan sobre el actual: la Unión Soviética sobre Rusia, Yugoslavia sobre
            Serbia. En la lista están con su nombre de entonces.
          </p>
          <WorldMap
            regions={byRegion}
            onSelect={(region) => navigate(pathFor(region.members.map((member) => member.name)))}
          />

          <label className="sr-only" htmlFor="country-search">
            Buscar un país
          </label>
          <input
            id="country-search"
            className={styles.search}
            type="search"
            placeholder="Buscar un país…"
            autoComplete="off"
            maxLength={60}
            value={text}
            onChange={(event) => setText(event.target.value)}
          />
          <p className="sr-only" aria-live="polite">
            {shown.length === 1 ? '1 país' : `${shown.length} países`}
          </p>
          {shown.length ? (
            <ul className={styles.list}>
              {shown.map((country) => (
                <li key={country.name}>
                  <Link to={pathFor([country.name])}>{country.label}</Link>{' '}
                  <span className={styles.count}>{formatNumber(country.movies)}</span>
                  {country.former && <span className={styles.former}>ya no existe</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p className={styles.note}>Ningún país coincide con «{text.trim()}».</p>
          )}
        </>
      )}
    </section>
  )
}
