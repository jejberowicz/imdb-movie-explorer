import styles from './States.module.css'

/** First load: placeholders with the shape of the posters. */
export function PosterSkeleton({ count = 12 }: { count?: number }) {
  return (
    <ul className={styles.skeletonGrid} aria-hidden="true">
      {Array.from({ length: count }, (_, index) => (
        <li key={index} className={styles.skeletonPoster} />
      ))}
    </ul>
  )
}

export function EmptyState({ query, onClear }: { query?: string; onClear?: () => void }) {
  return (
    <div className={styles.message}>
      <p>No encontramos películas{query ? ` para «${query}»` : ''}.</p>
      {onClear && (
        <button type="button" className="button" onClick={onClear}>
          Limpiar filtros
        </button>
      )}
    </div>
  )
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className={styles.message} role="alert">
      <p>{message}</p>
      {onRetry && (
        <button type="button" className="button" onClick={onRetry}>
          Reintentar
        </button>
      )}
    </div>
  )
}

/** A field without data: a dash on screen, «Sin datos» for screen readers (ADR 0003). */
export function NoData() {
  return (
    <>
      <span aria-hidden="true">—</span>
      <span className="sr-only">Sin datos</span>
    </>
  )
}

/** A thin bar while new results load and the previous ones stay on screen. */
export function LoadingBar({ visible }: { visible: boolean }) {
  return <div className={visible ? `${styles.loadingBar} ${styles.visible}` : styles.loadingBar} aria-hidden="true" />
}
