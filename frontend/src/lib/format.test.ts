import { describe, expect, it } from 'vitest'
import { countMovies, formatCompact, formatDuration, formatMoney, formatNumber, formatRating } from './format'

// Intl separates the currency with a non-breaking space.
const plain = (text: string) => text.replace(/\s/g, ' ')

describe('es-AR formats', () => {
  it('separates thousands with a dot and decimals with a comma', () => {
    expect(formatNumber(2278845)).toBe('2.278.845')
    expect(formatRating(9.3)).toBe('9,3')
    expect(formatRating(9)).toBe('9,0')
  })

  it('abbreviates the votes of the cards', () => {
    expect(plain(formatCompact(2278845))).toBe('2,3 M')
    expect(plain(formatCompact(350500))).toBe('350,5 k')
    expect(plain(formatCompact(3000))).toBe('3 k')
    expect(plain(formatCompact(999999))).toBe('1 M')
    expect(formatCompact(681)).toBe('681')
  })

  it('writes the duration in hours and minutes', () => {
    expect(formatDuration(142)).toBe('2 h 22 min')
    expect(formatDuration(120)).toBe('2 h')
    expect(formatDuration(45)).toBe('45 min')
  })

  it('shows each amount in its own currency, without converting it', () => {
    expect(plain(formatMoney({ amount: 25000000, currency: 'USD' }))).toBe('US$ 25.000.000')
    expect(plain(formatMoney({ amount: 6000000, currency: 'EUR' }))).toBe('EUR 6.000.000')
    // A code that Intl doesn't know still shows, with the number formatted.
    expect(plain(formatMoney({ amount: 6000000, currency: 'RUR' }))).toMatch(/RUR 6\.000\.000/)
  })

  it('counts movies in singular and plural', () => {
    expect(countMovies(1)).toBe('1 película')
    expect(countMovies(0)).toBe('0 películas')
    expect(countMovies(85855)).toBe('85.855 películas')
  })
})
