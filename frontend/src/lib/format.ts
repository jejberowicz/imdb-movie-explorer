/** es-AR formats with Intl: the API sends raw numbers and the interface decides how they look (ADR 0003). */

import type { Money } from '../api/movies'

const integer = new Intl.NumberFormat('es-AR')
const compact = new Intl.NumberFormat('es-AR', { notation: 'compact', maximumFractionDigits: 1 })
const oneDecimal = new Intl.NumberFormat('es-AR', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

/** 2278845 -> "2.278.845" */
export const formatNumber = (value: number): string => integer.format(value)

/** 2278845 -> "2,3 M", for the cards */
export const formatCompact = (value: number): string => compact.format(value)

/** 9.3 -> "9,3" */
export const formatRating = (value: number): string => oneDecimal.format(value)

/** 142 -> "2 h 22 min"; 120 -> "2 h"; 45 -> "45 min" */
export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  if (!hours) return `${rest} min`
  return rest ? `${hours} h ${rest} min` : `${hours} h`
}

/** An amount in its own currency, never converted: {25000000, USD} -> "US$ 25.000.000" */
export function formatMoney({ amount, currency }: Money): string {
  try {
    return new Intl.NumberFormat('es-AR', { style: 'currency', currency, maximumFractionDigits: 0 }).format(amount)
  } catch {
    return `${currency} ${formatNumber(amount)}`
  }
}

/** "1 película", "2 películas" */
export function countMovies(total: number): string {
  return `${formatNumber(total)} ${total === 1 ? 'película' : 'películas'}`
}
