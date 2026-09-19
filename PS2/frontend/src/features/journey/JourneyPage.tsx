import { Link } from 'react-router-dom'

import { formatSingaporeClock, formatSingaporeDateTime } from '../../lib/singaporeTime'
import { JourneyTimeline } from './JourneyTimeline'
import { StatusPanel } from './StatusPanel'
import { useJourney } from './useJourney'
import { SaveOfflineButton } from '../offline/SaveOfflineButton'
import { AsyncFeedback } from '../../components/AsyncFeedback'
import { JourneySkeleton } from './JourneySkeleton'
import { RouteOverview } from './RouteOverview'
import { RouteMapPanel } from './RouteMapPanel'

export function JourneyPage({ tripId }: { tripId: string }) {
  const { phase, snapshot, message, refresh, operation } = useJourney()
  if (phase === 'loading' && !snapshot) return <JourneySkeleton />
  if (phase === 'missing') return <section className="content-panel"><p className="eyebrow">Journey unavailable</p><h1>This journey is no longer available</h1><p className="lede">It may have expired or been deleted.</p><Link className="button button-primary" to="/plan">Plan a new journey</Link></section>
  if (!snapshot) return <section className="content-panel"><p className="eyebrow">Journey unavailable</p><h1>We could not load this journey</h1><p className="lede">{message ?? 'Please try again.'}</p><Link className="button button-primary" to="/">Go home</Link></section>

  const { plan, status, routeConfirmed } = snapshot
  const summary = plan.summary
  // The clock face is derived from the ISO instant the backend sends. The previous code
  // stripped "Leave at " off the label with a regex, which is a time parser built out of
  // English copy. The full label is still what assistive technology announces.
  const clock = formatSingaporeClock(summary.leave_by)

  // Five named regions, each with its own grid area. Optional notices used to sit directly in
  // the layout grid and auto-place, so a failed status check pushed the route map 119px down a
  // column it has nothing to do with. An empty region now collapses where it stands.
  return (
    <div className="journey-layout">
      <div className="journey-summary">
        {/* The backend label already says "appointment"; repeating it on the left pushed the
            line onto two rows at 320px for no extra meaning. */}
        <div className="journey-kicker">
          <span>Hospital visit</span>
          <span className="journey-kicker-date">{summary.appointment_label}</span>
        </div>
        <section className="departure-card" aria-labelledby="journey-heading">
          <p className="departure-label">Leave by</p>
          <h1 className="departure-time" id="journey-heading">
            <span aria-hidden="true">{clock ?? summary.leave_by_label}</span>
            <span className="visually-hidden">{summary.leave_by_label}</span>
          </h1>
          <span className="departure-rule" aria-hidden="true" />
          <p className="departure-arrival">{summary.arrival_label}</p>
          <p className="departure-metrics">{summary.duration_min} min journey · {summary.walk_distance_m} m walking</p>
        </section>
        <div className="journey-notices">
          {snapshot.source === 'saved' && <p className="offline-notice">Offline copy · saved {formatSingaporeDateTime(snapshot.receivedAt)}{snapshot.generatedAt ? ` · plan generated ${formatSingaporeDateTime(snapshot.generatedAt)}` : ''}</p>}
          {message && <p className="form-error" role="alert">{message}</p>}
          <AsyncFeedback operation={operation} label={operation === 'loading-effective-plan' ? 'Updating your directions…' : operation === 'preparing-offline' ? 'Preparing offline steps…' : 'Checking current conditions…'} />
        </div>
        <StatusPanel
          status={status}
          routeConfirmed={routeConfirmed}
          statusFreshness={snapshot.statusFreshness}
          onRefresh={() => void refresh()}
          refreshing={phase === 'refreshing'}
        />
        {snapshot.warnings.map((warning) => <p className="journey-warning journey-route-warning" role="alert" key={warning}>{warning}</p>)}
      </div>
      <div className="journey-overview">
        <RouteOverview legs={plan.legs} status={status} />
        <RouteMapPanel legs={plan.legs} map={plan.map} status={status} offline={snapshot.source === 'saved'} />
      </div>
      <section className="journey-directions" aria-labelledby="steps-heading">
        <div className="section-heading">
          <h2 id="steps-heading">Journey steps</h2>
          <Link className="text-button" to={`/trip/${encodeURIComponent(tripId)}/options`}>See options</Link>
        </div>
        <JourneyTimeline plan={plan} status={status} />
        {/* The hero traded this away for two metrics. It is the only place the interface
            explains why the departure time is what it is, so it comes back — folded away,
            but never behind anything about uncertainty or safety. */}
        <details className="disclosure">
          <summary>How this time was worked out</summary>
          <div className="disclosure-body">
            <p>{summary.timing_basis}</p>
            <p>Planned to arrive between {summary.range_min[0]} and {summary.range_min[1]} minutes from leaving, with {summary.buffer_min} minutes spare before the appointment.</p>
          </div>
        </details>
      </section>
      <div className="journey-actions">
        <SaveOfflineButton />
        <Link className="text-button" to="/settings">Journey settings</Link>
        <footer className="attribution">{plan.attribution.map((item) => <span key={item}>{item}</span>)}</footer>
      </div>
    </div>
  )
}
