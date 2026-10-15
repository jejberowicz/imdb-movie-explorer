import { describe, expect, it } from 'vitest'
import {
  browsePath,
  chosenYear,
  documentTitle,
  hasChoices,
  hasFilters,
  inWords,
  type LegendPart,
  legend,
  readBrowseState,
  sectionTitle,
  toggle,
  toMovieQuery,
  writeBrowseState,
} from './browse'

const read = (search: string) => readBrowseState(new URLSearchParams(search))

describe('browse state in the URL', () => {
  it('reads every parameter', () => {
    expect(
      read(
        'q=godfather&genre=Crime&genre=Drama&country=USA&country=Italy&decade=1960&decade=1970' +
          '&year_from=1970&year_to=1979&sort=votes&order=asc&page=3',
      ),
    ).toEqual({
        q: 'godfather',
        genres: ['Crime', 'Drama'],
        countries: ['USA', 'Italy'],
        decades: [1970, 1960],
        yearFrom: 1970,
        yearTo: 1979,
        sort: 'votes',
        order: 'asc',
        page: 3,
      })
  })

  it('ignores values that the API would reject, instead of failing', () => {
    expect(read('page=-2&sort=drop&order=up&year_from=19x0&decade=1995&decade=1870&decade=x')).toEqual({
      q: '',
      page: 1,
      genres: [],
      countries: [],
      decades: [],
    })
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
    expect(read(`genre=${'g'.repeat(41)}&genre=Drama`).genres).toEqual(['Drama'])
    expect(read('genre=Drama&genre=Drama&decade=1990&decade=1990')).toMatchObject({ genres: ['Drama'], decades: [1990] })
    expect(read(Array.from({ length: 12 }, (_, index) => `genre=G${index}`).join('&')).genres).toHaveLength(10)
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
    const search =
      'q=matrix&genre=Action&genre=Sci-Fi&country=USA&decade=1990&year_from=1999&year_to=1999&sort=rating&order=desc&page=2'
    expect(writeBrowseState(read(search)).toString()).toBe(search)
  })

  it('turns the state into the parameters of the API', () => {
    expect(toMovieQuery(read('q= matrix &country=USA&page=2'))).toEqual({
      title: 'matrix',
      page: 2,
      pageSize: 24,
      sort: undefined,
      order: undefined,
      genres: undefined,
      countries: ['USA'],
      decades: undefined,
      yearFrom: undefined,
      yearTo: undefined,
    })
    expect(toMovieQuery(read('genre=Crime&genre=Drama&decade=1970'))).toMatchObject({
      genres: ['Crime', 'Drama'],
      decades: [1970],
    })
  })

  it('knows the year chosen in the strip, only inside the single decade chosen', () => {
    expect(chosenYear(read('decade=1990&year_from=1994&year_to=1994'))).toBe(1994)
    expect(chosenYear(read('decade=1990'))).toBeUndefined()
    expect(chosenYear(read('decade=1990&year_from=2004&year_to=2004'))).toBeUndefined()
    expect(chosenYear(read('decade=1990&decade=2000&year_from=1994&year_to=1994'))).toBeUndefined()
    expect(chosenYear(read('decade=1990&year_from=1990&year_to=1999'))).toBeUndefined()
  })

  it('knows when something is chosen', () => {
    expect(hasFilters(read(''))).toBe(false)
    expect(hasFilters(read('page=4'))).toBe(false)
    expect(hasFilters(read('q=x'))).toBe(true)
    expect(hasFilters(read('decade=1990'))).toBe(true)
    // The order alone is no filter, but it can be cleared.
    expect(hasFilters(read('sort=votes'))).toBe(false)
    expect(hasChoices(read('sort=votes'))).toBe(true)
    expect(hasChoices(read(''))).toBe(false)
  })

  it('adds a value to a list, or takes it out if it is there', () => {
    expect(toggle([1990], 2000)).toEqual([1990, 2000])
    expect(toggle([1990, 2000], 1990)).toEqual([2000])
  })
})

describe('the title of the results', () => {
  it('says the search and the order', () => {
    expect(sectionTitle(read(''))).toBe('Mejor valoradas')
    expect(sectionTitle(read('q=godfather'))).toBe('Resultados para «godfather»')
    expect(sectionTitle(read('q=godfather&sort=year&order=asc'))).toBe('Resultados para «godfather» · Más viejas')
    expect(sectionTitle(read('q=matrix&sort=relevance'))).toBe('Resultados para «matrix»')
    expect(sectionTitle(read('q=matrix&sort=relevance&order=asc'))).toBe('Resultados para «matrix»')
    expect(sectionTitle(read('sort=title'))).toBe('De la A a la Z')
    // The filters go in the legend.
    expect(sectionTitle(read('genre=Drama&decade=1990'))).toBe('Mejor valoradas')
  })

  it('puts every filter in the title of the browser tab', () => {
    expect(documentTitle(read('genre=Drama&decade=1990&decade=2000'), { genres: ['Drama'], countries: [] })).toBe(
      'Mejor valoradas · Drama · 1990s y 2000s',
    )
    expect(
      documentTitle(read('country=Russia&country=Soviet+Union'), { genres: [], countries: ['Rusia', 'Unión Soviética'] }),
    ).toBe('Mejor valoradas · Rusia o Unión Soviética')
  })
})

/** The legend as the reader sees it, with the bold parts between asterisks. */
const said = (parts: LegendPart[]) => parts.map((part) => (typeof part === 'string' ? part : `*${part.strong}*`)).join('')

describe('the legend of the filters', () => {
  it('says what the filters leave, in a sentence', () => {
    const none = { genres: [], countries: [] }
    expect(said(legend(read('decade=2020'), 1474, none))).toBe(
      'Hay *1.474 películas* estrenadas en los *2020s*.',
    )
    expect(
      said(
        legend(read('genre=Comedy&genre=Romance&country=Italy&country=France&decade=2010&decade=1990'), 12, {
          genres: ['Comedia', 'Romance'],
          countries: ['Italia', 'Francia'],
        }),
      ),
    ).toBe(
      'Hay *12 películas* de los géneros *Comedia y Romance*, hechas en *Italia o Francia*, estrenadas en los ' +
        '*1990s y 2010s*.',
    )
    expect(said(legend(read('genre=Drama&decade=1990&year_from=1994&year_to=1994'), 1, { genres: ['Drama'], countries: [] }))).toBe(
      'Hay *1 película* del género *Drama*, estrenada en *1994*.',
    )
    expect(said(legend(read('q=padrino'), 3, none))).toBe('Hay *3 películas* con *«padrino»* en el título.')
    expect(said(legend(read('year_from=1950&year_to=1960'), 9, none))).toBe(
      'Hay *9 películas* estrenadas entre *1950 y 1960*.',
    )
    expect(said(legend(read('year_from=1950'), 9, none))).toBe('Hay *9 películas* estrenadas desde *1950*.')
  })

  it('lists in words', () => {
    expect(inWords([])).toBe('')
    expect(inWords(['A'])).toBe('A')
    expect(inWords(['A', 'B', 'C'])).toBe('A, B y C')
    expect(inWords(['A', 'B'], 'o')).toBe('A o B')
  })
})
