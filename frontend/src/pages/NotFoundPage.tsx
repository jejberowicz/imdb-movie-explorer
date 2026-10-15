import { Link } from 'react-router'
import { useDocumentTitle } from '../hooks/useDocumentTitle'
import styles from './NotFoundPage.module.css'

export default function NotFoundPage() {
  useDocumentTitle('Página no encontrada')
  return (
    <div className={styles.box}>
      <h1 className={styles.title}>No encontramos esa página</h1>
      <Link to="/">Ir al inicio</Link>
    </div>
  )
}
