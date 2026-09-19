import { useEffect, useRef } from 'react'
import { BrowserRouter, Link, Route, Routes, useParams, useLocation } from 'react-router-dom'

import { AlternativesPage } from './features/alternatives/AlternativesPage'
import { DemoPage } from './features/demo/DemoPage'
import { AppointmentForm } from './features/planning/AppointmentForm'
import { JourneyPage } from './features/journey/JourneyPage'
import { JourneyProvider } from './features/journey/JourneyProvider'
import { getActiveTripId } from './features/planning/activeTrip'
import { SettingsPage } from './features/settings/SettingsPage'
import './styles/global.css'
import './styles/native.css'
import './styles/feedback.css'

function PageShell({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()
  const mainRef = useRef<HTMLElement>(null)
  const parent = pathname.endsWith('/options') ? pathname.replace(/\/options$/, '') : '/'
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
    mainRef.current?.focus({ preventScroll: true })
  }, [pathname])
  return (
    <div className="app-shell">
      <header className="site-header">
        {pathname !== '/' && <Link className="header-control" to={parent} aria-label="Back to previous screen">←</Link>}
        <Link className="wordmark" to="/" aria-label="Nusa journey home">
          <span aria-hidden="true">N</span>
          Nusa
        </Link>
        {pathname !== '/settings' && <Link className="header-control settings-control" to="/settings" aria-label="Journey settings"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" aria-hidden="true"><path d="M4 7h16M4 17h16"/><circle cx="9" cy="7" r="3" fill="currentColor" stroke="none"/><circle cx="16" cy="17" r="3" fill="currentColor" stroke="none"/></svg></Link>}
      </header>
      <main ref={mainRef} tabIndex={-1}>{children}</main>
    </div>
  )
}

function HomePage() {
  const tripId = getActiveTripId()
  return (
    <PageShell>
      <section className="hero-panel" aria-labelledby="home-heading">
        <p className="eyebrow">Your day, at your pace</p>
        <h1 id="home-heading">Your journey</h1>
        <p className="home-intro">A little preparation. A calmer trip.</p>
      </section>
      <section className="route-ticket" aria-label="Your usual route">
        <div className="ticket-top"><span>Your usual route</span><span className="route-chip">Hospital visit</span></div>
        <div className="route-endpoints">
          <div className="endpoint"><span className="endpoint-dot"/><div><span className="endpoint-label">From home</span><h2>Bedok</h2><p>Blk 208B New Upper Changi Road</p></div></div>
          <div className="endpoint"><span className="endpoint-dot destination-dot"/><div><span className="endpoint-label">To your appointment</span><h2>Singapore General Hospital</h2><p>Block 3 · Outram Park</p></div></div>
        </div>
        <div className="ticket-footer"><span>Walk</span><span aria-hidden="true">—</span><span className="line-pill">East–West Line</span><span aria-hidden="true">—</span><span>Walk</span></div>
      </section>
      <section className="appointment-preview"><span className="calendar-symbol" aria-hidden="true">▦</span><div><h2>{tripId ? 'Your saved journey is ready' : 'When is your appointment?'}</h2><p>{tripId ? 'Open it to check your departure and route.' : 'Add a time to find out when to leave.'}</p></div></section>
      <div className="home-action"><Link className="button button-primary" to={tripId ? `/trip/${encodeURIComponent(tripId)}` : '/plan'}>{tripId ? 'Open journey' : 'Plan journey'}<span aria-hidden="true">→</span></Link>{tripId && <Link className="text-button" to="/plan">New appointment</Link>}</div>
      <p className="scope-note">Currently available for your Bedok → SGH journey.</p>
    </PageShell>
  )
}

function SettingsRoute() {
  return <PageShell><SettingsPage tripId={getActiveTripId()} /></PageShell>
}

function DemoRoute() {
  if (import.meta.env.VITE_ENABLE_DEMO !== 'true') return <NotFoundPage />
  return <PageShell><DemoPage /></PageShell>
}

function PlanPage() {
  return (
    <PageShell>
      <section className="content-panel">
        <p className="eyebrow">New appointment</p>
        <h1>Appointment details</h1>
        <p className="lede">Bedok → SGH, Block 3</p>
        {getActiveTripId() && <p className="replacement-note">This becomes your active journey. Your previous server journey is not deleted.</p>}
        <AppointmentForm />
      </section>
    </PageShell>
  )
}

function NotFoundPage() {
  return (
    <PageShell>
      <section className="content-panel">
        <p className="eyebrow">Journey companion</p>
        <h1>Page not found</h1>
        <p className="lede">This link is not available. Return home to plan or open a journey.</p>
        <Link className="button button-primary" to="/">Go home</Link>
      </section>
    </PageShell>
  )
}

function TripRoute() {
  const { tripId } = useParams()
  if (!tripId) return <NotFoundPage />
  return (
    <PageShell>
      <JourneyProvider tripId={tripId}><JourneyPage tripId={tripId} /></JourneyProvider>
    </PageShell>
  )
}

function AlternativesRoute() {
  const { tripId } = useParams()
  if (!tripId) return <NotFoundPage />
  return <PageShell><AlternativesPage tripId={tripId} /></PageShell>
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/plan" element={<PlanPage />} />
        <Route path="/trip/:tripId" element={<TripRoute />} />
        <Route path="/trip/:tripId/options" element={<AlternativesRoute />} />
        <Route path="/settings" element={<SettingsRoute />} />
        <Route path="/demo" element={<DemoRoute />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
