/**
 * Country names in Spanish and the regions of the map (ADR 0009). The API sends each country as it comes in
 * the CSV, with the ISO code of the country where the map paints it.
 */

import type { CountryCount } from '../api/movies'

/** Countries that no longer exist: Intl has no name for them. */
const FORMER_ES: Record<string, string> = {
  Burma: 'Birmania',
  Czechoslovakia: 'Checoslovaquia',
  'East Germany': 'Alemania Oriental',
  'Federal Republic of Yugoslavia': 'República Federal de Yugoslavia',
  Korea: 'Corea',
  'Netherlands Antilles': 'Antillas Neerlandesas',
  'North Vietnam': 'Vietnam del Norte',
  'Serbia and Montenegro': 'Serbia y Montenegro',
  'Soviet Union': 'Unión Soviética',
  Swaziland: 'Suazilandia',
  'West Germany': 'Alemania Occidental',
  Yugoslavia: 'Yugoslavia',
  Zaire: 'Zaire',
}

const regionNames = new Intl.DisplayNames('es', { type: 'region' })

export function regionName(code: string): string {
  try {
    return regionNames.of(code) ?? code
  } catch {
    return code
  }
}

/** The Spanish name of a country of the CSV. */
export function countryLabel(country: Pick<CountryCount, 'name' | 'map_code' | 'former'>): string {
  if (country.former) return FORMER_ES[country.name] ?? country.name
  return country.map_code ? regionName(country.map_code) : country.name
}

export interface Region {
  code: string
  name: string
  movies: number
  /** The CSV names painted here: the country itself and the former ones assigned to it. */
  members: CountryCount[]
}

/** The countries grouped by the region of the map where they are painted. */
export function regions(countries: CountryCount[]): Map<string, Region> {
  const byCode = new Map<string, Region>()
  for (const country of countries) {
    if (!country.map_code) continue
    const region = byCode.get(country.map_code) ?? {
      code: country.map_code,
      name: regionName(country.map_code),
      movies: 0,
      members: [],
    }
    region.movies += country.movies
    region.members.push(country)
    byCode.set(country.map_code, region)
  }
  return byCode
}
