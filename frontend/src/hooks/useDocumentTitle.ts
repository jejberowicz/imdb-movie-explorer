import { useEffect } from 'react'

/** The title of the tab, and of the entry in the browser history. */
export function useDocumentTitle(title?: string) {
  useEffect(() => {
    document.title = title ? `${title} · FakeIMDb` : 'FakeIMDb'
  }, [title])
}
