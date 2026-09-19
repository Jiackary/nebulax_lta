import { BrowserRouter, Link, Route, Routes, useParams } from 'react-router-dom'

import { AlternativesPage } from './features/alternatives/AlternativesPage'
import { DemoPage } from './features/demo/DemoPage'
import { AppointmentForm } from './features/planning/AppointmentForm'
import { JourneyPage } from './features/journey/JourneyPage'
import { JourneyProvider } from './features/journey/JourneyProvider'
import { getActiveTripId } from './features/planning/activeTrip'
import { SettingsPage } from './features/settings/SettingsPage'
import { PageShell } from './components/PageShell'
import './styles/index.css'

const HOME = { to: '/', label: 'Home' }

function HomePage() {
  const tripId = getActiveTripId()
  return (
    <PageShell>
      <h1 id="home-heading">Your journey</h1>
      <section className="route-ticket" aria-label="Your usual route">
        <div className="ticket-top"><span>Your usual route</span><span className="route-chip">Hospital visit</span></div>
        <div className="route-endpoints">
          <div className="endpoint"><span className="endpoint-dot" /><div><span className="endpoint-label">From home</span><h2>Bedok</h2><p>Blk 208B New Upper Changi Road</p></div></div>
          <div className="endpoint"><span className="endpoint-dot destination-dot" /><div><span className="endpoint-label">To your appointment</span><h2>Singapore General Hospital</h2><p>Block 3 · Outram Park</p></div></div>
        </div>
        <div className="ticket-footer"><span>Walk</span><span aria-hidden="true">—</span><span className="line-pill">East–West Line</span><span aria-hidden="true">—</span><span>Walk</span></div>
      </section>
      {/* An active id proves a journey was saved on this device. It does not prove the journey
          is still on the server, still in the future, or still step-free, so this claims
          nothing beyond what the id actually establishes. */}
      <section className="appointment-preview">
        <span className="calendar-symbol" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><rect x="3" y="5" width="18" height="16" rx="3" /><path d="M8 3v4M16 3v4M3 10h18" /></svg>
        </span>
        <div>
          <h2>{tripId ? 'You have a saved journey' : 'When is your appointment?'}</h2>
          <p>{tripId ? 'Open it to check your departure and route.' : 'Add a time to find out when to leave.'}</p>
        </div>
      </section>
      <div className="home-action">
        <Link className="button button-primary" to={tripId ? `/trip/${encodeURIComponent(tripId)}` : '/plan'}>{tripId ? 'Open saved journey' : 'Plan journey'}<span aria-hidden="true">→</span></Link>
        {tripId && <Link className="text-button" to="/plan">New appointment</Link>}
      </div>
      <p className="scope-note">Currently available for your Bedok → SGH journey.</p>
    </PageShell>
  )
}

function SettingsRoute() {
  return <PageShell title="Settings" back={HOME}><SettingsPage tripId={getActiveTripId()} /></PageShell>
}

function DemoRoute() {
  if (import.meta.env.VITE_ENABLE_DEMO !== 'true') return <NotFoundPage />
  return <PageShell title="Demo" back={HOME}><DemoPage /></PageShell>
}

function PlanPage() {
  return (
    <PageShell title="New appointment" back={HOME}>
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
    <PageShell title="Not found" back={HOME}>
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
    <PageShell title="Your journey" back={HOME} wide>
      <JourneyProvider tripId={tripId}><JourneyPage tripId={tripId} /></JourneyProvider>
    </PageShell>
  )
}

function AlternativesRoute() {
  const { tripId } = useParams()
  if (!tripId) return <NotFoundPage />
  return (
    <PageShell title="Options" back={{ to: `/trip/${encodeURIComponent(tripId)}`, label: 'Journey' }}>
      <AlternativesPage tripId={tripId} />
    </PageShell>
  )
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
