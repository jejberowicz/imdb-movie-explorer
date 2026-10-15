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
    children: [
      { index: true, element: <BrowsePage /> },
      { path: 'movies/:id', element: <MoviePage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]
