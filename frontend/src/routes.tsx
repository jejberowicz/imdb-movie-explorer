import type { RouteObject } from 'react-router'
import { Layout } from './components/Layout'
import BrowsePage from './pages/BrowsePage'
import ErrorPage from './pages/ErrorPage'
import MoviePage from './pages/MoviePage'
import NotFoundPage from './pages/NotFoundPage'

export const routes: RouteObject[] = [
  {
    element: <Layout />,
    errorElement: <ErrorPage />,
    // Opening /countries directly waits for its code; meanwhile, the frame of the page.
    hydrateFallbackElement: (
      <Layout>
        <p className="loading">Cargando…</p>
      </Layout>
    ),
    children: [
      { index: true, element: <BrowsePage /> },
      { path: 'movies/:id', element: <MoviePage /> },
      {
        path: 'countries',
        // The map (d3 and the shapes) downloads only when someone opens this page.
        lazy: async () => ({ Component: (await import('./pages/CountriesPage')).default }),
      },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
