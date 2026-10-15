import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import type { SortField, SortOrder } from '../api/movies'
import { useDebouncedValue } from '../hooks/useDebouncedValue'
import { type BrowseState, browsePath, DECADES, toggle } from '../lib/browse'
import { GENRES_ES, genreLabel } from '../lib/genres'
import styles from './BrowseBar.module.css'
import { Dropdown, type Option } from './Dropdown'

type SortChoice = `${SortField}-${SortOrder}`

interface BrowseBarProps {
  state: BrowseState
  genres: string[]
  /** The decades with movies, newest first; DECADES until the API answers. */
  decades?: number[]
  /** Change the state; `replace` keeps the history clean while typing. */
  onChange: (changes: Partial<BrowseState>, replace?: boolean) => void
}

const RATING: Option<SortChoice>[] = [
  { label: 'Más alto primero', value: 'rating-desc' },
  { label: 'Más bajo primero', value: 'rating-asc' },
]
const POPULARITY: Option<SortChoice>[] = [
  { label: 'Más votadas', value: 'votes-desc' },
  { label: 'Menos votadas', value: 'votes-asc' },
]
const NAME: Option<SortChoice>[] = [
  { label: 'De la A a la Z', value: 'title-asc' },
  { label: 'De la Z a la A', value: 'title-desc' },
]

/**
 * «Explorar por»: a menu per criterion, as in Letterboxd, and the search on the right (docs/ui.md). Año and Género
 * allow several; in every menu, choosing again what is chosen takes it out.
 */
export function BrowseBar({ state, genres, decades = DECADES, onChange }: BrowseBarProps) {
  const navigate = useNavigate()
  const sortChoice = state.sort ? (`${state.sort}-${state.order ?? (state.sort === 'title' ? 'asc' : 'desc')}` as SortChoice) : undefined
  const sortBy = (choice: SortChoice) => {
    if (choice === sortChoice) return onChange({ sort: undefined, order: undefined, page: 1 })
    const [sort, order] = choice.split('-') as [SortField, SortOrder]
    onChange({ sort, order, page: 1 })
  }
  const genreOptions: Option<string | null>[] = [
    { label: 'Todos', value: null },
    ...(genres.length ? genres : Object.keys(GENRES_ES))
      .map((genre) => ({ label: genreLabel(genre), value: genre }))
      .sort((a, b) => a.label.localeCompare(b.label, 'es')),
  ]
  const decadeOptions: Option<number | null>[] = [
    { label: 'Todas', value: null },
    ...decades.map((decade) => ({ label: `${decade}s`, value: decade })),
  ]
  const countryOptions: Option<string>[] = [
    { label: 'Ver el mapa de países', value: 'map' },
    ...(state.countries.length ? [{ label: 'Quitar el país elegido', value: 'clear' }] : []),
  ]

  return (
    <div className={styles.bar}>
      <span className="label" id="browse-label">
        Explorar por
      </span>
      <div className={styles.group} role="group" aria-labelledby="browse-label">
        <Dropdown
          label="Año"
          options={decadeOptions}
          multiple
          selected={state.decades.length ? state.decades : [null]}
          active={state.decades.length > 0 || state.yearFrom !== undefined || state.yearTo !== undefined}
          // The year chosen in the strip belongs to one decade: another set of decades starts without it.
          onSelect={(decade) =>
            onChange({
              decades: decade === null ? [] : toggle(state.decades, decade).sort((a, b) => b - a),
              yearFrom: undefined,
              yearTo: undefined,
              page: 1,
            })
          }
        />
        <Dropdown label="Rating" options={RATING} selected={sortChoice} active={state.sort === 'rating'} onSelect={sortBy} />
        <Dropdown label="Popularidad" options={POPULARITY} selected={sortChoice} active={state.sort === 'votes'} onSelect={sortBy} />
        <Dropdown
          label="Género"
          options={genreOptions}
          multiple
          selected={state.genres.length ? state.genres : [null]}
          active={state.genres.length > 0}
          onSelect={(genre) => onChange({ genres: genre === null ? [] : toggle(state.genres, genre), page: 1 })}
        />
        <Dropdown label="Nombre" options={NAME} selected={sortChoice} active={state.sort === 'title'} onSelect={sortBy} />
        <Dropdown
          label="País"
          options={countryOptions}
          actions
          active={state.countries.length > 0}
          onSelect={(choice) =>
            choice === 'map'
              ? navigate(browsePath({ ...state, page: 1 }, '/countries'))
              : onChange({ countries: [], page: 1 })
          }
        />
      </div>
      <SearchBox
        value={state.q}
        // While typing, the first search adds an entry to the history, so the back button returns to the list
        // from before; the next ones replace it, so the history doesn't fill up with every pause.
        onSearch={(q, typing) => onChange({ q, page: 1 }, typing && state.q.trim() !== '')}
      />
    </div>
  )
}

interface SearchBoxProps {
  value: string
  /** `typing` is true when the search comes from a pause while typing, false for Enter. */
  onSearch: (q: string, typing: boolean) => void
}

/** Searches 300 ms after the last key; Enter searches right away and Esc clears. */
function SearchBox({ value, onSearch }: SearchBoxProps) {
  const [text, setText] = useState(value)
  const debounced = useDebouncedValue(text, 300)
  // The last value this box sent: a different one in the URL comes from outside (back button, «Limpiar»).
  const sent = useRef(value)

  // The URL keeps the text trimmed: "the " sent and "the" back is the same search, not a change from outside
  // (comparing them as they are erased the space while the user paused between two words).
  useEffect(() => {
    if (value.trim() !== sent.current.trim()) {
      sent.current = value
      setText(value)
    }
  }, [value])

  // Search only when the typed text settles, not on every render: after the back button the old text is still
  // debounced for 300 ms and must not bring the old search back.
  const settled = useRef(debounced)
  useEffect(() => {
    if (debounced === settled.current) return
    settled.current = debounced
    if (debounced.trim() !== sent.current.trim()) {
      sent.current = debounced
      onSearch(debounced, true)
    }
  }, [debounced, onSearch])

  return (
    <form
      className={styles.search}
      role="search"
      onSubmit={(event) => {
        event.preventDefault()
        sent.current = text
        onSearch(text, false)
      }}
    >
      <label className="label" htmlFor="search-input">
        Buscar película
      </label>
      <input
        id="search-input"
        type="search"
        value={text}
        autoComplete="off"
        maxLength={200}
        onChange={(event) => setText(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === 'Escape') setText('')
        }}
      />
    </form>
  )
}
