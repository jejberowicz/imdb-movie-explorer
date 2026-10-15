import { useEffect } from 'react'
import { useRouteError } from 'react-router'
import { Layout } from '../components/Layout'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import styles from './NotFoundPage.module.css'

/** An unexpected error while showing a page, or a part of the app that didn't download (a new deploy). */
export default function ErrorPage() {
  const error = useRouteError()
  useDocumentTitle('Error')
  useEffect(() => console.error(error), [error])
  return (
    <Layout>
      <div className={styles.box} role="alert">
        <h1 className={styles.title}>Algo salió mal</h1>
        <p className={styles.text}>No pudimos mostrar esta página.</p>
        <button type="button" className="button" onClick={() => window.location.reload()}>
          Recargar
        </button>
      </div>
    </Layout>
  )
}
