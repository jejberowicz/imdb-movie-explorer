import { screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderApp } from './test/render'

describe('navigation', () => {
  it('opens a movie from the list, and «Volver» returns to the same list', async () => {
    const { router, user } = renderApp('/?genre=Crime')
    await user.click(await screen.findByRole('link', { name: 'The Godfather (1972)' }))

    expect(await screen.findByRole('heading', { level: 1, name: 'The Godfather' })).toBeInTheDocument()
    expect(router.state.location.pathname).toBe('/movies/tt0068646')
    // The focus goes to the new page, so a screen reader starts reading there.
    expect(screen.getByRole('main')).toHaveFocus()

    await user.click(screen.getByRole('button', { name: '← Volver' }))
    await waitFor(() => expect(router.state.location.search).toBe('?genre=Crime'))
    expect(await screen.findByRole('link', { name: 'The Godfather: Part II (1974)' })).toBeInTheDocument()
  })

  it('goes to the home page from a movie opened directly', async () => {
    const { router, user } = renderApp('/movies/tt0068646')
    await user.click(await screen.findByRole('button', { name: '← Volver' }))
    await waitFor(() => expect(router.state.location.pathname).toBe('/'))
  })

  it('says when a page does not exist', async () => {
    renderApp('/peliculas')
    expect(await screen.findByRole('heading', { name: 'No encontramos esa página' })).toBeInTheDocument()
    expect(document.title).toBe('Página no encontrada · FakeIMDb')
  })

  it('has a link to skip to the content', async () => {
    const { user } = renderApp()
    await screen.findByRole('link', { name: 'Stalker (1979)' })
    await user.tab()
    expect(screen.getByRole('link', { name: 'Saltar al contenido' })).toHaveFocus()
    await user.keyboard('{Enter}')
    expect(screen.getByRole('main')).toHaveFocus()
  })
})
