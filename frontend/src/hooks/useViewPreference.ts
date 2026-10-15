import { useCallback, useState } from 'react'

export type View = 'cards' | 'table'
const KEY = 'fakeimdb:view'

function read(): View {
  try {
    return localStorage.getItem(KEY) === 'table' ? 'table' : 'cards'
  } catch {
    // Storage can be blocked (private mode, settings): the default view still works.
    return 'cards'
  }
}

/** Cards or table, remembered between visits. */
export function useViewPreference(): [View, (view: View) => void] {
  const [view, setView] = useState<View>(read)
  const choose = useCallback((next: View) => {
    setView(next)
    try {
      localStorage.setItem(KEY, next)
    } catch {
      // Not remembered, but the view still changes.
    }
  }, [])
  return [view, choose]
}
