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
