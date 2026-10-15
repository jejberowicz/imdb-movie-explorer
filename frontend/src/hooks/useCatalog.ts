import { useQuery } from '@tanstack/react-query'
import { fetchCountries, fetchGenres } from '../api/movies'

// Genres and countries only change with a new load: one request per session is enough.
const HOUR = 60 * 60 * 1000

export function useGenres() {
  return useQuery({ queryKey: ['genres'], queryFn: ({ signal }) => fetchGenres(signal), staleTime: HOUR })
}

export function useCountries() {
  return useQuery({ queryKey: ['countries'], queryFn: ({ signal }) => fetchCountries(signal), staleTime: HOUR })
}
