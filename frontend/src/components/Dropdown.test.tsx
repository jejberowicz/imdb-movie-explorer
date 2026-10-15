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

  it('offers commands as plain menu items, with none checked', async () => {
    const onSelect = vi.fn()
    render(
      <Dropdown
        label="País"
        actions
        options={[
          { label: 'Ver el mapa de países', value: 'map' },
          { label: 'Quitar el país elegido', value: 'clear' },
        ]}
        onSelect={onSelect}
      />,
    )
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'País' }))

    expect(screen.queryByRole('menuitemradio')).not.toBeInTheDocument()
    expect(screen.getByRole('menuitem', { name: 'Ver el mapa de países' })).toHaveFocus()
    expect(screen.getByRole('menuitem', { name: 'Ver el mapa de países' })).not.toHaveAttribute('aria-checked')
    await user.keyboard('{ArrowDown}{Enter}')
    expect(onSelect).toHaveBeenCalledWith('clear')
  })

  it('tells apart two options with the same label', async () => {
    const errors = vi.spyOn(console, 'error').mockImplementation(() => {})
    const onSelect = vi.fn()
    render(
      <Dropdown
        label="Género"
        options={[
          { label: 'Drama', value: 'Drama' },
          { label: 'Drama', value: 'drama' },
        ]}
        onSelect={onSelect}
      />,
    )
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Género' }))
    await user.click(screen.getAllByRole('menuitemradio', { name: 'Drama' })[1])

    expect(onSelect).toHaveBeenCalledWith('drama')
    // React warns about two children with the same key.
    expect(errors).not.toHaveBeenCalled()
    errors.mockRestore()
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
