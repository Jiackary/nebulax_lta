import { Link } from 'react-router-dom'

import { JourneyTimeline } from './JourneyTimeline'
import { StatusPanel } from './StatusPanel'
import { useJourney } from './useJourney'
import { SaveOfflineButton } from '../offline/SaveOfflineButton'
import { AsyncFeedback } from '../../components/AsyncFeedback'
import { JourneySkeleton } from './JourneySkeleton'
import { RouteOverview } from './RouteOverview'

export function JourneyPage({ tripId }: { tripId: string }) {
  const { phase, snapshot, message, refresh, operation } = useJourney()
  if (phase === 'loading' && !snapshot) return <JourneySkeleton />
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
      {snapshot.source === 'saved' && <p className="offline-notice">Offline copy · saved {snapshot.receivedAt}{snapshot.generatedAt ? ` · plan generated ${snapshot.generatedAt}` : ''}</p>}
      {message && <p className="form-error" role="alert">{message}</p>}
      <AsyncFeedback operation={operation} label={operation === 'loading-effective-plan' ? 'Updating your directions…' : operation === 'preparing-offline' ? 'Preparing offline steps…' : 'Checking current conditions…'} />
      <StatusPanel status={status} routeConfirmed={routeConfirmed} statusFreshness={snapshot.statusFreshness} />
      {snapshot.warnings.map((warning) => <p className="journey-warning journey-route-warning" role="alert" key={warning}>{warning}</p>)}
      <RouteOverview legs={plan.legs} />
      <section className="timeline-panel" aria-labelledby="steps-heading">
        <div className="section-heading"><div><p className="eyebrow">Your route</p><h2 id="steps-heading">Journey steps</h2></div><Link className="text-button" to={`/trip/${encodeURIComponent(tripId)}/options`}>See options</Link></div>
        <JourneyTimeline plan={plan} />
      </section>
      <SaveOfflineButton />
      <Link className="text-button" to="/settings">Journey settings</Link>
      <footer className="attribution">{plan.attribution.map((item) => <span key={item}>{item}</span>)}</footer>
    </div>
  )
}
