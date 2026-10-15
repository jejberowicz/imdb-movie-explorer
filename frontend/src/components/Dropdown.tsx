import { type KeyboardEvent, useEffect, useId, useRef, useState } from 'react'
import styles from './Dropdown.module.css'

export interface Option<T> {
  label: string
  value: T
}

interface DropdownProps<T> {
  label: string
  options: Option<T>[]
  selected?: T
  active?: boolean
  /** The options are commands (open the map), not a choice among values: plain menu items, none checked. */
  actions?: boolean
  onSelect: (value: T) => void
}

const ITEMS = '[role="menuitem"], [role="menuitemradio"]'

/** A menu button: arrows move between the options, Enter chooses, Esc closes and returns the focus. */
export function Dropdown<T>({ label, options, selected, active = false, actions = false, onSelect }: DropdownProps<T>) {
  const [open, setOpen] = useState(false)
  const root = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  const menu = useRef<HTMLDivElement>(null)
  const id = useId()

  useEffect(() => {
    if (!open) return
    const items = menu.current?.querySelectorAll<HTMLButtonElement>(ITEMS)
    const current = Array.from(items ?? []).find((item) => item.getAttribute('aria-checked') === 'true')
    ;(current ?? items?.[0])?.focus()
    const closeOutside = (event: MouseEvent) => {
      if (!root.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', closeOutside)
    return () => document.removeEventListener('mousedown', closeOutside)
  }, [open])

  function close() {
    setOpen(false)
    button.current?.focus()
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const items = Array.from(menu.current?.querySelectorAll<HTMLButtonElement>(ITEMS) ?? [])
    const index = items.indexOf(document.activeElement as HTMLButtonElement)
    const moves: Record<string, number> = { ArrowDown: index + 1, ArrowUp: index - 1, Home: 0, End: items.length - 1 }
    if (event.key in moves) {
      event.preventDefault()
      items[(moves[event.key] + items.length) % items.length]?.focus()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      close()
    } else if (event.key === 'Tab') {
      setOpen(false)
    }
  }

  return (
    <div className={styles.dropdown} ref={root}>
      <button
        ref={button}
        type="button"
        className={active ? `${styles.trigger} ${styles.active}` : styles.trigger}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={() => setOpen(!open)}
      >
        {label}
        <span className={styles.chevron} aria-hidden="true">
          ▾
        </span>
      </button>
      {open && (
        <div ref={menu} id={id} role="menu" aria-label={label} className={styles.menu} onKeyDown={onKeyDown}>
          {/* The value as key, unique in each menu: two options may share a label, and the genres can arrive from
              the API while the menu is open, which must not move the focus. */}
          {options.map((option) => (
            <button
              key={String(option.value)}
              type="button"
              role={actions ? 'menuitem' : 'menuitemradio'}
              aria-checked={actions ? undefined : option.value === selected}
              className={styles.item}
              onClick={() => {
                onSelect(option.value)
                close()
              }}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
