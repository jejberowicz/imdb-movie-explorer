import { fireEvent, screen, waitFor } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { findLegend, renderApp, searchOf } from '../test/render'

const listNames = () =>
  screen
    .getAllByRole('listitem')
    .filter((item) => item.closest('ul'))
    .map((item) => item.querySelector('a')?.textContent)

async function openMap(path = '/countries') {
  const app = renderApp(path)
  const map = await screen.findByRole('img', { name: /Mapa del mundo/ })
  return { ...app, map }
}

describe('countries page', () => {
  it('lists the countries in Spanish and marks the ones that no longer exist', async () => {
    await openMap()

    const names = listNames()
    expect(names.slice(0, 4)).toEqual(['Alemania', 'Alemania Occidental', 'Alemania Oriental', 'Argentina'])
    expect(names).toContain('Estados Unidos')
    expect(screen.getByRole('link', { name: 'Unión Soviética' }).parentElement).toHaveTextContent(
      'Unión Soviética 866ya no existe',
    )
    expect(screen.getByRole('link', { name: 'Rusia' }).parentElement).not.toHaveTextContent('ya no existe')
    expect(document.title).toBe('Por país · FakeIMDb')
  })

  it('finds a country without accents, and by its name in the CSV', async () => {
    const { user } = await openMap()
    const search = screen.getByRole('searchbox', { name: 'Buscar un país' })

    await user.type(search, 'union sov')
    expect(listNames()).toEqual(['Unión Soviética'])

    await user.clear(search)
    await user.type(search, 'west germ')
    expect(listNames()).toEqual(['Alemania Occidental'])

    await user.clear(search)
    await user.type(search, 'zzz')
    expect(screen.getByText('Ningún país coincide con «zzz».')).toBeInTheDocument()
  })

  it('opens the movies of a country of the list, keeping the filters chosen before', async () => {
    const { router, user } = await openMap('/countries?genre=Drama')
    expect(screen.getByRole('link', { name: '← Volver a las películas' })).toHaveAttribute('href', '/?genre=Drama')

    await user.click(screen.getByRole('link', { name: 'Unión Soviética' }))

    expect(await findLegend('Hay 1 película del género Drama, hecha en Unión Soviética.')).toBeInTheDocument()
    expect(searchOf(router)).toEqual({ genre: ['Drama'], country: ['Soviet Union'] })
    expect(await screen.findByRole('link', { name: 'Stalker (1979)' })).toBeInTheDocument()
  })

  it('adds the former countries to their successor on the map', async () => {
    const { router, map } = await openMap()
    const russia = map.querySelector('[data-code="RU"]')!

    fireEvent.mouseMove(russia)
    expect(screen.getByText('Unión Soviética: 866 películas')).toBeInTheDocument()
    expect(screen.getByText('Rusia: 1.083 películas')).toBeInTheDocument()

    fireEvent.click(russia)
    await waitFor(() => expect(searchOf(router)).toEqual({ country: ['Russia', 'Soviet Union'] }))
    expect(await findLegend('Hay 1 película hecha en Rusia o Unión Soviética.')).toBeInTheDocument()
  })

  it('draws the countries too small for the map as dots', async () => {
    const { map } = await openMap()
    expect(map.querySelector('circle[data-code="HK"]')).toBeInTheDocument()
    // A country without movies is drawn, but not as a link.
    expect(map.querySelector('[data-code="BR"]')).not.toBeInTheDocument()
    expect(map.querySelectorAll('path').length).toBeGreaterThan(170)
  })
})
