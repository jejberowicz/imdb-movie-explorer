import { screen } from '@testing-library/react'
import { http } from 'msw'
import { describe, expect, it } from 'vitest'
import { renderApp } from '../test/render'
import { problem, server } from '../test/server'

/** The value next to a label of the facts list. */
const fact = (label: string) => screen.getByText(label, { selector: 'dt' }).nextElementSibling as HTMLElement

describe('movie page', () => {
  it('shows the data of the movie, formatted for Argentina', async () => {
    renderApp('/movies/tt0111161')

    expect(await screen.findByRole('heading', { level: 1, name: 'The Shawshank Redemption' })).toHaveAttribute(
      'translate',
      'no',
    )
    expect(screen.getByText('1994 · Drama · 2 h 22 min')).toBeInTheDocument()
    expect(screen.getByText(/2\.278\.845 votos/)).toBeInTheDocument()
    expect(screen.getByText(/Two imprisoned men bond/)).toHaveAttribute('lang', 'en')
    expect(fact('Dirección')).toHaveTextContent('Frank Darabont')
    expect(fact('Guion')).toHaveTextContent('Stephen King, Frank Darabont')
    expect(fact('Países')).toHaveTextContent('Estados Unidos')
    expect(fact('Presupuesto')).toHaveTextContent(/^US\$\s25\.000\.000$/)
    expect(fact('Recaudación mundial')).toHaveTextContent(/^US\$\s28\.815\.245$/)
    expect(document.title).toBe('The Shawshank Redemption (1994) · FakeIMDb')
  })

  it('links to IMDb in a new tab, without giving it access to this page', async () => {
    renderApp('/movies/tt0111161')
    const link = await screen.findByRole('link', { name: /Ver en IMDb/ })
    expect(link).toHaveAttribute('href', 'https://www.imdb.com/title/tt0111161/')
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')
  })

  it('marks the missing data, and «None» as a movie without dialogue', async () => {
    renderApp('/movies/tt1084680')
    await screen.findByRole('heading', { level: 1, name: 'Egon & Dönci' })

    expect(fact('Idiomas')).toHaveTextContent('Sin diálogos')
    // On screen a dash; for a screen reader, «Sin datos».
    expect(fact('Elenco')).toHaveTextContent('—Sin datos')
    expect(fact('Productora')).toHaveTextContent('—Sin datos')
    expect(fact('Presupuesto')).toHaveTextContent('—Sin datos')
    expect(screen.queryByText(/Metascore/)).not.toBeInTheDocument()
  })

  it('says when the movie is not in the catalog', async () => {
    renderApp('/movies/tt9999999')
    expect(await screen.findByText('Esa película no está en el catálogo.')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Ir al inicio' })).toHaveAttribute('href', '/')
  })

  it('offers to retry when the API fails', async () => {
    server.use(http.get('/api/movies/:id', () => problem(503, 'The database is not available.'), { once: true }))
    const { user } = renderApp('/movies/tt0111161')

    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar la película.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))
    expect(await screen.findByRole('heading', { level: 1, name: 'The Shawshank Redemption' })).toBeInTheDocument()
  })
})
