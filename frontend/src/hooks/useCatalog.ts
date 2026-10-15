import { useQuery } from '@tanstack/react-query'
import { fetchCountries, fetchGenres, fetchYears } from '../api/movies'

// Genres, countries and years only change with a new load: one request per session is enough.
const HOUR = 60 * 60 * 1000

export function useGenres() {
  return useQuery({ queryKey: ['genres'], queryFn: ({ signal }) => fetchGenres(signal), staleTime: HOUR })
}

export function useCountries() {
  return useQuery({ queryKey: ['countries'], queryFn: ({ signal }) => fetchCountries(signal), staleTime: HOUR })
}

export function useYears() {
  return useQuery({ queryKey: ['years'], queryFn: ({ signal }) => fetchYears(signal), staleTime: HOUR })
}
