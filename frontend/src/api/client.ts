/** Base path of the API: nginx (and Vite in development) proxy /api to Flask, so there is no CORS. */
export const API_BASE = '/api'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

type Params = Record<string, string | number | readonly string[] | undefined>

/** GET a JSON resource. Empty parameters are left out; arrays repeat the parameter. */
export async function getJson<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === '') continue
    for (const item of Array.isArray(value) ? value : [value]) url.searchParams.append(key, String(item))
  }
  const response = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  if (!response.ok) throw new ApiError(response.status, `GET ${path} failed with ${response.status}`)
  return (await response.json()) as T
}
