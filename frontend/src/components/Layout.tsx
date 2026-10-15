import { type ReactNode, useEffect, useRef } from 'react'
import { Outlet, ScrollRestoration, useLocation } from 'react-router'
import styles from './Layout.module.css'
import { NavBar } from './NavBar'

/** The frame of every page. `children` replaces the routed page (the error and loading pages use it). */
export function Layout({ children }: { children?: ReactNode }) {
  const { pathname } = useLocation()
  const main = useRef<HTMLElement>(null)
  const previous = useRef(pathname)

  // On a new page, the focus goes to its content, so a screen reader starts there and not at the old link.
  // Only the path counts: typing in the search changes the query string and must not move the focus.
  useEffect(() => {
    if (previous.current === pathname) return
    previous.current = pathname
    main.current?.focus({ preventScroll: true })
  }, [pathname])

  return (
    <>
      <a
        href="#main"
        className="skip-link"
        onClick={(event) => {
          event.preventDefault()
          main.current?.focus()
        }}
      >
        Saltar al contenido
      </a>
      <NavBar />
      <main id="main" ref={main} tabIndex={-1} className={`wrap ${styles.main}`}>
        {children ?? <Outlet />}
      </main>
      <footer className={styles.footer}>
        <div className="wrap">
          <p>
            Datos: el CSV de IMDb del desafío, con 85.855 películas hasta 2020. Mapa:{' '}
            <a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener noreferrer">
              Natural Earth
            </a>
            , de dominio público.
          </p>
          <p>FakeIMDb no está relacionado con IMDb.</p>
        </div>
      </footer>
      {/* Back from a movie returns to the same place in the list */}
      {!children && <ScrollRestoration />}
    </>
  )
}
