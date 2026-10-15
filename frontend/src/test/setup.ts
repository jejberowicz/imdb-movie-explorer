import '@testing-library/jest-dom/vitest'
import { cleanup, configure } from '@testing-library/react'
import { afterAll, afterEach, beforeAll } from 'vitest'
import { server } from './server'

// findBy* waits 1 s by default. The first test of a file renders cold (and the map loads 170 KB of shapes), which
// on a busy machine or a CI runner can take longer: a slow machine is not a failing test.
configure({ asyncUtilTimeout: 5000 })

// jsdom doesn't scroll; the router and the pagination call it.
window.scrollTo = () => {}

// Any request without a handler fails the test: nothing reaches a real network.
beforeAll(() => server.listen({ onUnhandledFrame: 'error' }))
afterEach(() => {
  cleanup()
  server.resetHandlers()
  localStorage.clear()
})
afterAll(() => server.close())
