import { describe, expect, it } from 'vitest'
import { COLORS, familyOf, posterDesign } from './poster'

const movie = (id: string, title = 'The Godfather', genres = ['Crime', 'Drama']) => ({
  imdb_title_id: id,
  original_title: title,
  genres,
})

describe('generated posters', () => {
  it('always gives the same poster to the same movie', () => {
    expect(posterDesign(movie('tt0068646'))).toEqual(posterDesign(movie('tt0068646')))
  })

  it('varies the design between movies', () => {
    const ids = Array.from({ length: 40 }, (_, index) => `tt${String(68646 + index).padStart(7, '0')}`)
    const designs = ids.map((id) => posterDesign(movie(id)))
    expect(new Set(designs.map((design) => design.template)).size).toBe(4)
    expect(new Set(designs.map((design) => design.angle)).size).toBeGreaterThan(10)
    for (const design of designs) {
      expect(design.angle).toBeGreaterThanOrEqual(150)
      expect(design.angle).toBeLessThan(210)
    }
  })

  it('takes the colors from the first genre', () => {
    expect(familyOf(['Horror', 'Comedy'])).not.toBe(familyOf(['Comedy', 'Horror']))
    expect(posterDesign(movie('tt1', 'X', ['Comedy'])).colors).toEqual(COLORS.comedia)
    expect(familyOf(['Documentary-like genre that does not exist'])).toBe('otros')
  })

  it('makes the letters smaller as the title gets longer', () => {
    const sizes = ['Up', 'The Godfather', 'The Shawshank Redemption', 'Il buono, il brutto, il cattivo and more'].map(
      (title) => posterDesign(movie('tt1', title)).titleSize,
    )
    expect(sizes).toEqual([...sizes].sort((a, b) => b - a))
    expect(new Set(sizes).size).toBe(sizes.length)
  })
})
