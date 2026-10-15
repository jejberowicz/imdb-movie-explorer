import { act, screen, waitFor, within } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { DETAILS } from '../test/fixtures'
import { findLegend, renderApp, searchOf } from '../test/render'
import { listMovies, problem, recordMovieRequests, server, summary } from '../test/server'

const card = (name: string) => screen.queryByRole('link', { name })
const cardNames = () => screen.getAllByRole('link', { name: /\(\d{4}\)$/ }).map((link) => link.getAttribute('aria-label'))
const searchBox = () => screen.getByRole('searchbox', { name: 'Buscar película' })
const wait = (ms: number) => act(() => new Promise((resolve) => setTimeout(resolve, ms)))

describe('browse page', () => {
  it('shows the best rated movies as posters', async () => {
    renderApp()
    expect(await screen.findByRole('link', { name: 'The Shawshank Redemption (1994)' })).toHaveAttribute(
      'href',
      '/movies/tt0111161',
    )
    expect(cardNames()).toEqual([
      'The Shawshank Redemption (1994)',
      'The Godfather (1972)',
      'The Godfather: Part II (1974)',
      'Il buono, il brutto, il cattivo (1966)',
      'Sen to Chihiro no kamikakushi (2001)',
      'Stalker (1979)',
      'La tortue rouge (2016)',
      'Egon & Dönci (2007)',
    ])
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Mejor valoradas')
    expect(screen.getByText('8 películas')).toBeInTheDocument()
    expect(document.title).toBe('FakeIMDb')
  })

  it('searches as the user types, with one request when the typing stops', async () => {
    const seen = recordMovieRequests()
    const { router, user } = renderApp()
    await screen.findByRole('link', { name: 'The Shawshank Redemption (1994)' })

    await user.type(searchBox(), 'padrino')

    // «padrino» is in the Italian title: the search covers both titles (ADR 0004).
    expect(await screen.findByRole('heading', { name: 'Resultados para «padrino»' })).toBeInTheDocument()
    await waitFor(() => expect(cardNames()).toEqual(['The Godfather (1972)', 'The Godfather: Part II (1974)']))
    expect(seen.map((url) => url.searchParams.get('title'))).toEqual([null, 'padrino'])
    expect(searchOf(router)).toEqual({ q: ['padrino'] })
    expect(document.title).toBe('Resultados para «padrino» · FakeIMDb')
  })

  it('never lets a slow old answer replace a newer one', async () => {
    server.use(
      http.get('/api/movies', async ({ request }) => {
        const url = new URL(request.url)
        if (url.searchParams.get('title') === 'stalker') await delay(400)
        return HttpResponse.json(listMovies(url))
      }),
    )
    const { user } = renderApp('/?q=stalker')

    await user.clear(searchBox())
    await user.type(searchBox(), 'chihiro')
    expect(await screen.findByRole('link', { name: 'Sen to Chihiro no kamikakushi (2001)' })).toBeInTheDocument()

    await wait(500)
    expect(card('Stalker (1979)')).not.toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Resultados para «chihiro»')
  })

  it('keeps the results on screen while the next page loads', async () => {
    const pages = [DETAILS.slice(0, 4), DETAILS.slice(4)]
    server.use(
      http.get('/api/movies', async ({ request }) => {
        const page = Number(new URL(request.url).searchParams.get('page'))
        if (page === 2) await delay(300)
        return HttpResponse.json({
          items: pages[page - 1].map(summary),
          page,
          page_size: 24,
          total: 30,
          total_pages: 2,
        })
      }),
    )
    const { router, user } = renderApp()
    await screen.findByRole('link', { name: 'The Shawshank Redemption (1994)' })
    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Siguiente →' }))

    // Still the first page, without a blank screen in between.
    expect(card('The Shawshank Redemption (1994)')).toBeInTheDocument()
    expect(await screen.findByRole('link', { name: 'Stalker (1979)' })).toBeInTheDocument()
    expect(card('The Shawshank Redemption (1994)')).not.toBeInTheDocument()
    expect(screen.getByText('Página 2 de 2')).toBeInTheDocument()
    expect(searchOf(router)).toEqual({ page: ['2'] })
  })

  it('keeps the keyboard focus on «Siguiente» when it reaches the last page', async () => {
    server.use(
      http.get('/api/movies', ({ request }) => {
        const page = Number(new URL(request.url).searchParams.get('page'))
        const items = DETAILS.slice((page - 1) * 4, page * 4).map(summary)
        return HttpResponse.json({ items, page, page_size: 24, total: 30, total_pages: 2 })
      }),
    )
    const { router, user } = renderApp()
    await screen.findByRole('link', { name: 'The Shawshank Redemption (1994)' })
    const next = screen.getByRole('button', { name: 'Siguiente →' })

    next.focus()
    await user.keyboard('{Enter}')

    expect(await screen.findByText('Página 2 de 2')).toBeInTheDocument()
    expect(next).toHaveFocus()
    expect(next).toHaveAttribute('aria-disabled', 'true')
    // On the last page it does nothing.
    await user.keyboard('{Enter}')
    expect(searchOf(router)).toEqual({ page: ['2'] })
  })

  it('goes to the last page from a page past the end', async () => {
    const seen = recordMovieRequests()
    const { router } = renderApp('/?genre=Drama&page=5000')

    expect(await screen.findByRole('link', { name: 'Stalker (1979)' })).toBeInTheDocument()
    expect(searchOf(router)).toEqual({ genre: ['Drama'] })
    expect(seen.map((url) => url.searchParams.get('page'))).toEqual(['5000', '1'])
    expect(screen.queryByText(/No encontramos películas/)).not.toBeInTheDocument()
    // The empty page is replaced, not left behind in the history.
    expect(router.state.historyAction).toBe('REPLACE')
  })

  it('says when nothing matches and clears the filters', async () => {
    const { router, user } = renderApp('/?q=zzzz&genre=Drama')
    const empty = (await screen.findByText('No encontramos películas para «zzzz».')).parentElement!

    await user.click(within(empty).getByRole('button', { name: 'Limpiar filtros' }))

    expect(await screen.findByRole('link', { name: 'Stalker (1979)' })).toBeInTheDocument()
    expect(router.state.location.search).toBe('')
    expect(searchBox()).toHaveValue('')
  })

  it('shows an error with a way to retry', async () => {
    server.use(http.get('/api/movies', () => problem(500, 'Unexpected error.'), { once: true }))
    const { user } = renderApp()

    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos cargar las películas.')
    await user.click(screen.getByRole('button', { name: 'Reintentar' }))

    expect(await screen.findByRole('link', { name: 'Stalker (1979)' })).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('offers to clear the filters when the API rejects them, since retrying would fail again', async () => {
    server.use(http.get('/api/movies', () => problem(400, 'Invalid request parameters.'), { once: true }))
    const { router, user } = renderApp('/?genre=Drama')

    expect(await screen.findByRole('alert')).toHaveTextContent('No pudimos buscar con estos filtros.')
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument()
    await user.click(within(screen.getByRole('alert')).getByRole('button', { name: 'Limpiar filtros' }))

    expect(await screen.findByRole('link', { name: 'Stalker (1979)' })).toBeInTheDocument()
    expect(router.state.location.search).toBe('')
  })

  it('stops ordering by relevance when the search is cleared', async () => {
    const seen = recordMovieRequests()
    const { router, user } = renderApp('/?q=godfather&sort=relevance')
    await screen.findByRole('link', { name: 'The Godfather (1972)' })

    await user.clear(searchBox())

    await waitFor(() => expect(cardNames()).toHaveLength(8))
    expect(seen.at(-1)?.searchParams.get('sort')).toBeNull()
    expect(searchOf(router)).toEqual({})
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('filters with the «Explorar por» menus, several decades at once', async () => {
    const { router, user } = renderApp()
    await screen.findByRole('link', { name: 'Stalker (1979)' })

    await user.click(screen.getByRole('button', { name: 'Género' }))
    await user.click(screen.getByRole('menuitemcheckbox', { name: 'Animación' }))
    expect(await findLegend('Hay 3 películas del género Animación.')).toBeInTheDocument()
    // The menu stays open to choose more; Esc closes it.
    expect(screen.getByRole('menuitemcheckbox', { name: 'Animación' })).toHaveAttribute('aria-checked', 'true')
    await user.keyboard('{Escape}')

    await user.click(screen.getByRole('button', { name: 'Año' }))
    await user.click(screen.getByRole('menuitemcheckbox', { name: '2000s' }))
    await user.click(screen.getByRole('menuitemcheckbox', { name: '2010s' }))
    expect(await findLegend('Hay 3 películas del género Animación, estrenadas en los 2000s y 2010s.')).toBeInTheDocument()

    // Choosing a chosen one again takes it out.
    await user.click(screen.getByRole('menuitemcheckbox', { name: '2000s' }))
    expect(await findLegend('Hay 1 película del género Animación, estrenada en los 2010s.')).toBeInTheDocument()
    await waitFor(() => expect(cardNames()).toEqual(['La tortue rouge (2016)']))
    expect(searchOf(router)).toEqual({ genre: ['Animation'], decade: ['2010'] })
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Mejor valoradas')
    expect(document.title).toBe('Mejor valoradas · Animación · 2010s · FakeIMDb')

    await user.click(screen.getByRole('menuitemcheckbox', { name: 'Todas' }))
    await waitFor(() => expect(searchOf(router)).toEqual({ genre: ['Animation'] }))
  })

  it('keeps the legend of the movies on screen while the next ones load', async () => {
    const { user } = renderApp('/?genre=Drama')
    expect(await findLegend('Hay 4 películas del género Drama.')).toBeInTheDocument()
    server.use(
      http.get('/api/movies', async ({ request }) => {
        await delay(300)
        return HttpResponse.json(listMovies(new URL(request.url)))
      }),
    )

    await user.click(screen.getByRole('button', { name: 'Género' }))
    await user.click(screen.getByRole('menuitemcheckbox', { name: 'Policial' }))

    // The count of the four dramas never goes with the words of the next filters.
    expect(await findLegend('Hay 4 películas del género Drama.')).toBeInTheDocument()
    expect(await findLegend('Hay 2 películas de los géneros Drama y Policial.')).toBeInTheDocument()
  })

  it('stacks genres: the movies that have all of them', async () => {
    const { router, user } = renderApp('/?genre=Animation')
    await screen.findByRole('link', { name: 'Egon & Dönci (2007)' })

    await user.click(screen.getByRole('button', { name: 'Género' }))
    await user.click(screen.getByRole('menuitemcheckbox', { name: 'Familiar' }))

    expect(await findLegend('Hay 2 películas de los géneros Animación y Familiar.')).toBeInTheDocument()
    await waitFor(() =>
      expect(cardNames()).toEqual(['Sen to Chihiro no kamikakushi (2001)', 'La tortue rouge (2016)']),
    )
    expect(searchOf(router)).toEqual({ genre: ['Animation', 'Family'] })
  })

  it('narrows a decade to one of its years with the strip below the bar', async () => {
    const { router, user } = renderApp('/?decade=2000')
    const strip = await screen.findByRole('group', { name: 'Años de los 2000s' })
    // Only the years with movies.
    await waitFor(() =>
      expect(within(strip).getAllByRole('button').map((button) => button.textContent)).toEqual(['2000s', '2001', '2007']),
    )
    expect(within(strip).getByRole('button', { name: '2000s' })).toHaveAttribute('aria-pressed', 'true')

    await user.click(within(strip).getByRole('button', { name: '2007' }))
    expect(await findLegend('Hay 1 película estrenada en 2007.')).toBeInTheDocument()
    expect(searchOf(router)).toEqual({ decade: ['2000'], year_from: ['2007'], year_to: ['2007'] })
    expect(within(strip).getByRole('button', { name: '2007' })).toHaveAttribute('aria-pressed', 'true')

    // The chosen year again goes back to the whole decade.
    await user.click(within(strip).getByRole('button', { name: '2007' }))
    expect(await findLegend('Hay 2 películas estrenadas en los 2000s.')).toBeInTheDocument()
    expect(searchOf(router)).toEqual({ decade: ['2000'] })

    // A second decade has no strip: its years would be two lists.
    await user.click(screen.getByRole('button', { name: 'Año' }))
    await user.click(screen.getByRole('menuitemcheckbox', { name: '1990s' }))
    await waitFor(() => expect(screen.queryByRole('group', { name: /^Años de/ })).not.toBeInTheDocument())
  })

  it('takes out an order chosen again, back to the default', async () => {
    const { router, user } = renderApp()
    await screen.findByRole('link', { name: 'Stalker (1979)' })

    await user.click(screen.getByRole('button', { name: 'Rating' }))
    await user.click(screen.getByRole('menuitemradio', { name: 'Más bajo primero' }))
    await waitFor(() => expect(searchOf(router)).toEqual({ sort: ['rating'], order: ['asc'] }))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Peor valoradas')

    await user.click(screen.getByRole('button', { name: 'Rating' }))
    expect(screen.getByRole('menuitemradio', { name: 'Más bajo primero' })).toHaveAttribute('aria-checked', 'true')
    await user.click(screen.getByRole('menuitemradio', { name: 'Más bajo primero' }))
    await waitFor(() => expect(searchOf(router)).toEqual({}))
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Mejor valoradas')
  })

  it('shows an odd genre of the URL as it comes, not as code', async () => {
    renderApp('/?genre=constructor')
    expect(await screen.findByText('No encontramos películas.')).toBeInTheDocument()
    expect(document.title).toBe('Mejor valoradas · constructor · FakeIMDb')
  })

  it('reads the state from the URL, so a search can be shared', async () => {
    const seen = recordMovieRequests()
    renderApp('/?genre=Crime&sort=year&order=asc')

    expect(await screen.findByRole('heading', { name: 'Más viejas' })).toBeInTheDocument()
    expect(await findLegend('Hay 2 películas del género Policial.')).toBeInTheDocument()
    await waitFor(() => expect(cardNames()).toEqual(['The Godfather (1972)', 'The Godfather: Part II (1974)']))
    const params = seen[0].searchParams
    expect([params.get('genre'), params.get('sort'), params.get('order'), params.get('page_size')]).toEqual([
      'Crime',
      'year',
      'asc',
      '24',
    ])
  })

  it('keeps the space when the user pauses between two words', async () => {
    const { router, user } = renderApp()
    await screen.findByRole('link', { name: 'Stalker (1979)' })

    await user.type(searchBox(), 'the ')
    await wait(400)
    await user.type(searchBox(), 'god')

    expect(searchBox()).toHaveValue('the god')
    await waitFor(() => expect(searchOf(router)).toEqual({ q: ['the god'] }))
  })

  it('undoes a typed search with the back button, back to the list from before', async () => {
    const { router, user } = renderApp('/?genre=Drama')
    await screen.findByRole('link', { name: 'Stalker (1979)' })

    await user.type(searchBox(), 'stal')
    await waitFor(() => expect(searchOf(router)).toEqual({ q: ['stal'], genre: ['Drama'] }))
    await user.type(searchBox(), 'ker')
    await waitFor(() => expect(searchOf(router)).toEqual({ q: ['stalker'], genre: ['Drama'] }))

    // One entry for the whole search, not one per pause.
    await act(() => router.navigate(-1))
    expect(router.state.location.search).toBe('?genre=Drama')
    await waitFor(() => expect(searchBox()).toHaveValue(''))
  })

  it('changes the URL once per search: Enter and the back button don\'t make it bounce', async () => {
    const { router, user } = renderApp()
    await screen.findByRole('link', { name: 'Stalker (1979)' })
    const urls: string[] = []
    router.subscribe(({ location }) => {
      if (urls.at(-1) !== location.search) urls.push(location.search)
    })

    await user.type(searchBox(), 'stalker{Enter}')
    await waitFor(() => expect(cardNames()).toEqual(['Stalker (1979)']))
    await wait(400) // the typed text settles, as when someone reads the results before going back
    await act(() => router.navigate(-1))
    await wait(400)

    expect(urls).toEqual(['?q=stalker', ''])
    expect(searchBox()).toHaveValue('')
    await waitFor(() => expect(cardNames()).toHaveLength(8))
  })
})

describe('table view', () => {
  afterEach(() => {
    Reflect.deleteProperty(window, 'matchMedia')
  })

  it('sorts by a column and remembers the view', async () => {
    const { router, user } = renderApp()
    await screen.findByRole('link', { name: 'Stalker (1979)' })

    await user.click(screen.getByRole('button', { name: 'Tabla' }))
    const table = screen.getByRole('table')
    // The default order is by rating, and the header says so before anything is chosen.
    expect(within(table).getByRole('columnheader', { name: /Rating/ })).toHaveAttribute('aria-sort', 'descending')
    expect(within(table).getAllByRole('row')).toHaveLength(9)
    expect(localStorage.getItem('fakeimdb:view')).toBe('table')

    await user.click(within(table).getByRole('button', { name: 'Duración' }))
    await waitFor(() => expect(searchOf(router)).toEqual({ sort: ['duration'], order: ['desc'] }))
    expect(screen.getByRole('columnheader', { name: 'Duración' })).toHaveAttribute('aria-sort', 'descending')
    await waitFor(() =>
      expect(within(screen.getAllByRole('row')[1]).getByRole('link')).toHaveTextContent('The Godfather: Part II'),
    )

    await user.click(screen.getByRole('button', { name: 'Duración' }))
    await waitFor(() => expect(searchOf(router)).toEqual({ sort: ['duration'], order: ['asc'] }))
    expect(screen.getByRole('columnheader', { name: 'Duración' })).toHaveAttribute('aria-sort', 'ascending')
  })

  it('shows where each movie is from, in Spanish', async () => {
    localStorage.setItem('fakeimdb:view', 'table')
    renderApp()
    const table = await screen.findByRole('table')
    expect(within(table).getByRole('columnheader', { name: 'País' })).toBeInTheDocument()
    const row = (title: string) => within(table).getByRole('link', { name: title }).closest('tr')!
    await waitFor(() => expect(row('Stalker')).toHaveTextContent('Unión Soviética'))
    expect(row('Il buono, il brutto, il cattivo')).toHaveTextContent('Italia, España, Alemania Occidental')
  })

  it('says that the order by rating weighs the votes, since the column shows the plain average', async () => {
    localStorage.setItem('fakeimdb:view', 'table')
    const { user } = renderApp()
    const table = await screen.findByRole('table')
    const note = /El orden por rating tiene en cuenta la cantidad de votos/

    // The default order is the weighted rating too (ADR 0008).
    expect(table).toHaveAccessibleDescription(note)
    await user.click(within(table).getByRole('button', { name: 'Votos' }))
    await waitFor(() => expect(screen.queryByText(note)).not.toBeInTheDocument())
    await user.click(within(screen.getByRole('table')).getByRole('button', { name: 'Rating' }))
    expect(await screen.findByText(note)).toBeInTheDocument()
  })

  it('always shows the posters on a phone', async () => {
    localStorage.setItem('fakeimdb:view', 'table')
    window.matchMedia = (query: string) =>
      ({ matches: true, media: query, addEventListener() {}, removeEventListener() {} }) as unknown as MediaQueryList
    renderApp()

    expect(await screen.findByRole('link', { name: 'Stalker (1979)' })).toBeInTheDocument()
    expect(screen.queryByRole('table')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tabla' })).not.toBeInTheDocument()
  })
})
