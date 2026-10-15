import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { createMemoryRouter, RouterProvider } from 'react-router'
import { routes } from '../routes'

/**
 * The whole app at a URL, with the API of server.ts. The router lets a test check the URL or go back. The client
 * doesn't retry, unless a test passes the one of the app.
 */
export function renderApp(path = '/', client = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
  const router = createMemoryRouter(routes, { initialEntries: [path] })
  const user = userEvent.setup()
  render(
    <QueryClientProvider client={client}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  )
  return { router, user }
}

/** The query string of the current URL, as an object of arrays. */
export function searchOf(router: ReturnType<typeof createMemoryRouter>): Record<string, string[]> {
  const params = new URLSearchParams(router.state.location.search)
  const result: Record<string, string[]> = {}
  for (const key of new Set(params.keys())) result[key] = params.getAll(key)
  return result
}

/** The legend of the filters, by its whole sentence: the values in bold split it in several text nodes. */
export function findLegend(sentence: string) {
  return screen.findByText((_, element) => element?.tagName === 'P' && element.textContent === sentence)
}
