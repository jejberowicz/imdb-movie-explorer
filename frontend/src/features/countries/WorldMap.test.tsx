import { fireEvent, render, screen } from '@testing-library/react'
import { Profiler } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { regions } from '../../lib/countries'
import { COUNTRIES } from '../../test/fixtures'
import { WorldMap } from './WorldMap'

describe('world map', () => {
  it('follows the mouse with the tooltip, without rendering again for a move of a pixel', () => {
    const commits = vi.fn()
    const { container } = render(
      <Profiler id="map" onRender={commits}>
        <WorldMap regions={regions(COUNTRIES)} onSelect={() => {}} />
      </Profiler>,
    )
    const russia = container.querySelector('[data-code="RU"]')!
    const tooltip = () => screen.getByText('Rusia: 1.083 películas').parentElement!

    fireEvent.mouseMove(russia, { clientX: 100, clientY: 50 })
    expect(tooltip()).toHaveStyle({ left: '100px', top: '50px' })
    const rendered = commits.mock.calls.length

    fireEvent.mouseMove(russia, { clientX: 101, clientY: 51 })
    expect(commits).toHaveBeenCalledTimes(rendered)
    expect(tooltip()).toHaveStyle({ left: '100px', top: '50px' })

    fireEvent.mouseMove(russia, { clientX: 140, clientY: 60 })
    expect(commits).toHaveBeenCalledTimes(rendered + 1)
    expect(tooltip()).toHaveStyle({ left: '140px', top: '60px' })

    fireEvent.mouseLeave(russia.closest('svg')!)
    expect(screen.queryByText('Rusia: 1.083 películas')).not.toBeInTheDocument()
  })
})
