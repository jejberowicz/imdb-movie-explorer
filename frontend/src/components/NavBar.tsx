import { Link } from 'react-router'
import styles from './NavBar.module.css'

export function NavBar() {
  return (
    <header className={styles.nav}>
      <div className={`wrap ${styles.inner}`}>
        <Link to="/" className={styles.logo}>
          <span className={styles.dot} aria-hidden="true" />
          FakeIMDb
        </Link>
      </div>
    </header>
  )
}
