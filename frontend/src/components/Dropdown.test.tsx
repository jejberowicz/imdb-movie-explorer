import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { Dropdown } from './Dropdown'

const OPTIONS = [
  { label: 'Todas', value: null },
  { label: '2000s', value: 2000 },
  { label: '1990s', value: 1990 },
]

function renderDropdown(selected: number | null = 1990) {
  const onSelect = vi.fn()
  render(
    <>
      <Dropdown label="Año" options={OPTIONS} selected={selected} onSelect={onSelect} />
      <p>Afuera</p>
    </>,
  )
  return { onSelect, user: userEvent.setup(), trigger: screen.getByRole('button', { name: 'Año' }) }
}

describe('dropdown menu', () => {
  it('opens on the chosen option and moves with the arrows', async () => {
    const { user, trigger } = renderDropdown()
    expect(trigger).toHaveAttribute('aria-expanded', 'false')

    await user.tab()
    await user.keyboard('{Enter}')

    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('menuitemradio', { name: '1990s' })).toHaveFocus()
    expect(screen.getByRole('menuitemradio', { name: '1990s' })).toHaveAttribute('aria-checked', 'true')
    await user.keyboard('{ArrowDown}')
    expect(screen.getByRole('menuitemradio', { name: 'Todas' })).toHaveFocus()
    await user.keyboard('{ArrowUp}')
    expect(screen.getByRole('menuitemradio', { name: '1990s' })).toHaveFocus()
    await user.keyboard('{Home}')
    expect(screen.getByRole('menuitemradio', { name: 'Todas' })).toHaveFocus()
    await user.keyboard('{End}')
    expect(screen.getByRole('menuitemradio', { name: '1990s' })).toHaveFocus()
  })

  it('chooses with Enter, closes and gives the focus back', async () => {
    const { onSelect, user, trigger } = renderDropdown()
    await user.click(trigger)
    await user.keyboard('{ArrowUp}{Enter}')

    expect(onSelect).toHaveBeenCalledWith(2000)
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('closes with Esc or a click outside, without choosing', async () => {
    const { onSelect, user, trigger } = renderDropdown(null)
    await user.click(trigger)
    expect(screen.getByRole('menuitemradio', { name: 'Todas' })).toHaveFocus()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()

    await user.click(trigger)
    await user.click(screen.getByText('Afuera'))
    expect(screen.queryByRole('menu')).not.toBeInTheDocument()
    expect(onSelect).not.toHaveBeenCalled()
  })
})
