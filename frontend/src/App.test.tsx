import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import App from './App'

function renderApp() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  )
}

describe('App', () => {
  it('lists the movies that the API returns', async () => {
    renderApp()
    expect(await screen.findByText('The Shawshank Redemption')).toBeInTheDocument()
    expect(screen.getByText('The Godfather')).toBeInTheDocument()
    expect(screen.getByText('2 películas')).toBeInTheDocument()
  })

  it('searches by title as the user types', async () => {
    renderApp()
    await screen.findByText('The Shawshank Redemption')
    await userEvent.type(screen.getByLabelText('Buscar película'), 'godf')
    expect(await screen.findByText('1 película')).toBeInTheDocument()
    expect(screen.queryByText('The Shawshank Redemption')).not.toBeInTheDocument()
  })
})
