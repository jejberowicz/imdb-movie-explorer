import { describe, expect, it } from 'vitest'
import { browsePath, decadeOf, hasFilters, readBrowseState, sectionTitle, toMovieQuery, writeBrowseState } from './browse'

const read = (search: string) => readBrowseState(new URLSearchParams(search))

describe('browse state in the URL', () => {
  it('reads every parameter', () => {
    expect(read('q=godfather&genre=Crime&country=USA&country=Italy&year_from=1970&year_to=1979&sort=votes&order=asc&page=3'))
      .toEqual({
        q: 'godfather',
        genre: 'Crime',
        countries: ['USA', 'Italy'],
        yearFrom: 1970,
        yearTo: 1979,
        sort: 'votes',
        order: 'asc',
        page: 3,
      })
  })

  it('ignores values that the API would reject, instead of failing', () => {
    expect(read('page=-2&sort=drop&order=up&year_from=19x0')).toEqual({ q: '', page: 1, countries: [] })
    expect(read('page=0').page).toBe(1)
  })

  it('keeps every value within the limits of the API, so a shared URL never ends in a 400', () => {
    expect(read('page=100001').page).toBe(100000)
    // Number('1000…000') is 1e+23, which the URL would carry as is.
    expect(read(`page=1${'0'.repeat(23)}`).page).toBe(100000)
    expect(read('year_from=1700&year_to=3000')).toMatchObject({ yearFrom: 1880, yearTo: 2100 })
    expect(read('year_from=1999&year_to=1990')).toMatchObject({ yearFrom: 1990, yearTo: 1999 })
    expect(read(`q=${'a'.repeat(250)}`).q).toHaveLength(200)
    expect(read('q=ma%00trix').q).toBe('matrix')
    expect(read(`genre=${'g'.repeat(41)}`).genre).toBeUndefined()
    expect(read('genre=Drama').genre).toBe('Drama')
    const many = Array.from({ length: 25 }, (_, index) => `country=C${index}`).join('&')
    expect(read(many).countries).toHaveLength(20)
    expect(read(`country=${'x'.repeat(61)}&country=+USA+&country=+`).countries).toEqual(['USA'])
  })

  it('drops the order by relevance without a search', () => {
    expect(read('sort=relevance').sort).toBeUndefined()
    expect(read('q=+&sort=relevance').sort).toBeUndefined()
    expect(read('q=matrix&sort=relevance').sort).toBe('relevance')
    // Clearing the search of a URL ordered by relevance.
    expect(writeBrowseState({ ...read('q=matrix&sort=relevance'), q: '' }).toString()).toBe('')
  })

  it('writes only what differs from the default, so the start page is just "/"', () => {
    expect(writeBrowseState(read('')).toString()).toBe('')
    expect(browsePath(read(''))).toBe('/')
    expect(browsePath(read('q=  alien '))).toBe('/?q=alien')
    expect(browsePath(read('country=USA&page=2'), '/countries')).toBe('/countries?country=USA&page=2')
  })

  it('round-trips through the URL', () => {
    const search = 'q=matrix&genre=Action&country=USA&year_from=1990&year_to=1999&sort=rating&order=desc&page=2'
    expect(writeBrowseState(read(search)).toString()).toBe(search)
  })

  it('turns the state into the parameters of the API', () => {
    expect(toMovieQuery(read('q= matrix &country=USA&page=2'))).toEqual({
      title: 'matrix',
      page: 2,
      pageSize: 24,
      sort: undefined,
      order: undefined,
      genre: undefined,
      countries: ['USA'],
      yearFrom: undefined,
      yearTo: undefined,
    })
  })

  it('knows when a year range is a decade', () => {
    expect(decadeOf(read('year_from=1990&year_to=1999'))).toBe(1990)
    expect(decadeOf(read('year_from=1990&year_to=2000'))).toBeUndefined()
    expect(decadeOf(read('year_from=1995&year_to=2004'))).toBeUndefined()
  })

  it('knows when something is chosen', () => {
    expect(hasFilters(read(''))).toBe(false)
    expect(hasFilters(read('page=4'))).toBe(false)
    expect(hasFilters(read('q=x'))).toBe(true)
    expect(hasFilters(read('sort=votes'))).toBe(true)
  })
})

describe('the title of the results', () => {
  it('says what is shown', () => {
    expect(sectionTitle(read(''), {})).toBe('Mejor valoradas')
    expect(sectionTitle(read('q=godfather'), {})).toBe('Resultados para «godfather»')
    expect(sectionTitle(read('q=godfather&sort=year&order=asc'), {})).toBe('Resultados para «godfather» · Más viejas')
    expect(sectionTitle(read('sort=title'), {})).toBe('De la A a la Z')
    expect(sectionTitle(read('genre=Drama&year_from=1990&year_to=1999'), { genre: 'Drama' })).toBe(
      'Mejor valoradas · Drama · 1990s',
    )
    expect(sectionTitle(read('year_from=1950'), {})).toBe('Mejor valoradas · 1950–…')
    expect(sectionTitle(read('country=Russia&country=Soviet+Union'), { countries: 'Rusia y Unión Soviética' })).toBe(
      'Mejor valoradas · Rusia y Unión Soviética',
    )
  })
})
