import { useEffect, useRef, type ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'

import wobbleMark from '../assets/wobble-mark.png'

type Back = { to: string; label: string }

/**
 * The app shell and its contextual header. Each screen states its own name and its own back
 * destination rather than having them inferred from the URL, so a route added later cannot
 * silently inherit a back link that points somewhere the reader never came from.
 */
export function PageShell({ title, back, wide = false, children }: {
  title?: string
  back?: Back
  wide?: boolean
  children: ReactNode
}) {
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
    mainRef.current?.focus({ preventScroll: true })
  }, [pathname])

  return (
    <div className="app-shell" data-layout={wide ? 'wide' : 'reading'}>
      <header className="site-header">
        {back
          ? (
            <Link className="header-back" to={back.to}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M15 5l-7 7 7 7" /></svg>
              <span>{back.label}</span>
            </Link>
          )
          : (
            <Link className="wordmark" to="/" aria-label="Wobble journey home">
              <img src={wobbleMark} alt="" width="160" height="160" />
              Wobble
            </Link>
          )}
        <p className="header-title">{title ?? ''}</p>
        {pathname === '/settings'
          ? <span />
          : (
            <Link className="header-control" to="/settings" aria-label="Journey settings">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden="true"><path d="M4 7h16M4 17h16" /><circle cx="9" cy="7" r="3" fill="currentColor" stroke="none" /><circle cx="16" cy="17" r="3" fill="currentColor" stroke="none" /></svg>
            </Link>
          )}
      </header>
      <main className="page" ref={mainRef} tabIndex={-1}>{children}</main>
    </div>
  )
}
