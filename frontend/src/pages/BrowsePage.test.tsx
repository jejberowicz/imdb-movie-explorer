import { act, screen, waitFor, within } from '@testing-library/react'
import { delay, http, HttpResponse } from 'msw'
import { afterEach, describe, expect, it } from 'vitest'
import { DETAILS } from '../test/fixtures'
import { renderApp, searchOf } from '../test/render'
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

  it('filters with the «Explorar por» menus', async () => {
    const { router, user } = renderApp()
    await screen.findByRole('link', { name: 'Stalker (1979)' })

    await user.click(screen.getByRole('button', { name: 'Género' }))
    await user.click(screen.getByRole('menuitemradio', { name: 'Animación' }))
    expect(await screen.findByRole('heading', { name: 'Mejor valoradas · Animación' })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Año' }))
    await user.click(screen.getByRole('menuitemradio', { name: '2000s' }))
    expect(await screen.findByRole('heading', { name: 'Mejor valoradas · Animación · 2000s' })).toBeInTheDocument()
    await waitFor(() =>
      expect(cardNames()).toEqual(['Sen to Chihiro no kamikakushi (2001)', 'Egon & Dönci (2007)']),
    )
    expect(searchOf(router)).toEqual({ genre: ['Animation'], year_from: ['2000'], year_to: ['2009'] })
  })

  it('shows an odd genre of the URL as it comes, not as code', async () => {
    renderApp('/?genre=constructor')
    expect(await screen.findByText('No encontramos películas.')).toBeInTheDocument()
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Mejor valoradas · constructor')
  })

  it('reads the state from the URL, so a search can be shared', async () => {
    const seen = recordMovieRequests()
    renderApp('/?genre=Crime&sort=year&order=asc')

    expect(await screen.findByRole('heading', { name: 'Más viejas · Policial' })).toBeInTheDocument()
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
