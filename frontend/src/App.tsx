import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { fetchMovies } from './api/movies'
import { useDebouncedValue } from './hooks/useDebouncedValue'

const votes = new Intl.NumberFormat('es-AR')
const rating = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

export default function App() {
  const [query, setQuery] = useState('')
  const [pages, setPages] = useState<Record<string, number>>({})
  const title = useDebouncedValue(query.trim(), 300)
  // Each search has its own page: a new search starts on page 1.
  const page = pages[title] ?? 1

  const { data, isPending, isError, refetch } = useQuery({
    queryKey: ['movies', { title, page }],
    queryFn: ({ signal }) => fetchMovies({ title, page }, signal),
    placeholderData: keepPreviousData,
  })

  return (
    <main className="app">
      <h1 className="logo">FakeIMDb</h1>
      <label className="search">
        Buscar película
        <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>

      {isPending && <p>Cargando películas…</p>}
      {isError && (
        <p role="alert">
          No pudimos cargar las películas. <button onClick={() => refetch()}>Reintentar</button>
        </p>
      )}
      {data && (
        <>
          <p aria-live="polite">
            {votes.format(data.total)} {data.total === 1 ? 'película' : 'películas'}
          </p>
          <table>
            <thead>
              <tr>
                <th scope="col">Título</th>
                <th scope="col">Año</th>
                <th scope="col">Rating</th>
                <th scope="col">Votos</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((movie) => (
                <tr key={movie.imdb_title_id}>
                  <td translate="no">{movie.original_title}</td>
                  <td>{movie.year}</td>
                  <td>{rating.format(movie.avg_vote)}</td>
                  <td>{votes.format(movie.votes)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <nav aria-label="Páginas">
            <button disabled={page <= 1} onClick={() => setPages({ ...pages, [title]: page - 1 })}>
              Anterior
            </button>
            <span>
              Página {page} de {Math.max(data.total_pages, 1)}
            </span>
            <button disabled={page >= data.total_pages} onClick={() => setPages({ ...pages, [title]: page + 1 })}>
              Siguiente
            </button>
          </nav>
        </>
      )}
    </main>
  )
}
