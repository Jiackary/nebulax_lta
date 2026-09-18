import { Link } from 'react-router-dom'

import { JourneyTimeline } from './JourneyTimeline'
import { StatusPanel } from './StatusPanel'
import { useJourney } from './useJourney'
import { SaveOfflineButton } from '../offline/SaveOfflineButton'

export function JourneyPage({ tripId }: { tripId: string }) {
  const { phase, snapshot, message, refresh } = useJourney()
  if (phase === 'loading' && !snapshot) return <section className="content-panel" aria-live="polite"><p className="eyebrow">Journey</p><h1>Preparing your journey</h1><p className="lede">Loading your route and the latest status.</p></section>
  if (phase === 'missing') return <section className="content-panel"><p className="eyebrow">Journey unavailable</p><h1>This journey is no longer available</h1><p className="lede">It may have expired or been deleted.</p><Link className="button button-primary" to="/plan">Plan a new journey</Link></section>
  if (!snapshot) return <section className="content-panel"><p className="eyebrow">Journey unavailable</p><h1>We could not load this journey</h1><p className="lede">{message ?? 'Please try again.'}</p><Link className="button button-primary" to="/">Go home</Link></section>

  const { plan, status, routeConfirmed } = snapshot
  return (
    <div className="journey-layout">
      <section className="journey-hero" aria-labelledby="journey-heading">
        <p className="eyebrow">Hospital appointment</p>
        <h1 id="journey-heading">{plan.summary.leave_by_label}</h1>
        <p className="journey-arrival">{plan.summary.arrival_label}</p>
        <p className="journey-basis">{plan.summary.timing_basis}</p>
        <button className="text-button" type="button" onClick={() => void refresh()} disabled={phase === 'refreshing'}>{phase === 'refreshing' ? 'Checking…' : 'Check again'}</button>
      </section>
      {snapshot.source === 'saved' && <p className="offline-notice">Offline copy · {snapshot.receivedAt ? 'saved directions shown' : 'written directions shown'}</p>}
      {message && <p className="form-error" role="alert">{message}</p>}
      <StatusPanel status={status} routeConfirmed={routeConfirmed} />
      <section className="timeline-panel" aria-labelledby="steps-heading">
        <div className="section-heading"><div><p className="eyebrow">Your route</p><h2 id="steps-heading">Journey steps</h2></div><Link className="text-button" to={`/trip/${encodeURIComponent(tripId)}/options`}>See options</Link></div>
        <JourneyTimeline plan={plan} />
      </section>
      <SaveOfflineButton tripId={tripId} />
      <Link className="text-button" to="/settings">Journey settings</Link>
      <footer className="attribution">{plan.attribution.map((item) => <span key={item}>{item}</span>)}</footer>
    </div>
  )
}
