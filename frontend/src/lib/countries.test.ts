import { describe, expect, it } from 'vitest'
import { COUNTRIES } from '../test/fixtures'
import { countryLabel, regions } from './countries'
import { fold } from './text'

const country = (name: string) => COUNTRIES.find((item) => item.name === name)!

describe('country names', () => {
  it('says the current countries in Spanish, from their ISO code', () => {
    expect(countryLabel(country('USA'))).toBe('Estados Unidos')
    expect(countryLabel(country('UK'))).toBe('Reino Unido')
    expect(countryLabel(country('Germany'))).toBe('Alemania')
  })

  it('keeps the countries that no longer exist with their own name', () => {
    expect(countryLabel(country('Soviet Union'))).toBe('Unión Soviética')
    expect(countryLabel(country('West Germany'))).toBe('Alemania Occidental')
  })

  it('uses the CSV name when there is no code', () => {
    expect(countryLabel({ name: 'Atlantis', map_code: null, former: false })).toBe('Atlantis')
  })
})

describe('map regions', () => {
  it('paints the former countries on their successor', () => {
    const byCode = regions(COUNTRIES)
    const germany = byCode.get('DE')!
    expect(germany.name).toBe('Alemania')
    expect(germany.members.map((member) => member.name).sort()).toEqual(['East Germany', 'Germany', 'West Germany'])
    expect(germany.movies).toBe(3721 + 1114 + 74)
    expect(byCode.get('RU')!.members.map((member) => member.name).sort()).toEqual(['Russia', 'Soviet Union'])
    expect(byCode.get('US')!.members).toHaveLength(1)
  })
})

describe('fold', () => {
  it('ignores case and accents', () => {
    expect(fold('  Unión SOVIÉTICA ')).toBe('union sovietica')
    expect(fold('Pokémon')).toBe(fold('pokemon'))
  })
})
