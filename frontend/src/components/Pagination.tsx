import { formatNumber } from '../lib/format'
import styles from './Pagination.module.css'

interface PaginationProps {
  page: number
  totalPages: number
  onPage: (page: number) => void
}

export function Pagination({ page, totalPages, onPage }: PaginationProps) {
  if (totalPages <= 1) return null
  const first = page <= 1
  const last = page >= totalPages
  // aria-disabled, not disabled: a disabled button drops the focus, and Enter on «Siguiente» up to the last page
  // would leave the keyboard at the start of the document.
  return (
    <nav className={styles.pagination} aria-label="Páginas">
      <button type="button" className="button" aria-disabled={first} onClick={() => first || onPage(page - 1)}>
        ← Anterior
      </button>
      <span>
        Página {formatNumber(page)} de {formatNumber(totalPages)}
      </span>
      <button type="button" className="button" aria-disabled={last} onClick={() => last || onPage(page + 1)}>
        Siguiente →
      </button>
    </nav>
  )
}
