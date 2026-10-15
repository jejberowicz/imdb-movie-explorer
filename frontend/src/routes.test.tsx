import { screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { renderApp } from './test/render'

describe('navigation', () => {
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
