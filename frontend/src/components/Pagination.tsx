import { formatNumber } from '../lib/format'
import styles from './Pagination.module.css'

interface PaginationProps {
  page: number
  totalPages: number
  onPage: (page: number) => void
}

export function Pagination({ page, totalPages, onPage }: PaginationProps) {
  if (totalPages <= 1) return null
  return (
    <nav className={styles.pagination} aria-label="Páginas">
      <button type="button" className="button" disabled={page <= 1} onClick={() => onPage(page - 1)}>
        ← Anterior
      </button>
      <span>
        Página {formatNumber(page)} de {formatNumber(totalPages)}
      </span>
      <button type="button" className="button" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>
        Siguiente →
      </button>
    </nav>
  )
}
