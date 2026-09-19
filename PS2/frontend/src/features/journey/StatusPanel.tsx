import type { RouteStatus } from '../../api/types'
import { formatSingaporeDateTime } from '../../lib/singaporeTime'
import type { StatusFreshness } from './journeyCoordinator'

/** A labelled control in the status region, beside the time it refreshes. The bare "↻"
 *  it replaces said neither what it did nor what it would cost to press. The icon turns
 *  only while a real request is in flight. */
function RefreshButton({ onRefresh, refreshing }: { onRefresh: () => void; refreshing: boolean }) {
  return (
    <button className="refresh-button" type="button" data-pending={refreshing} onClick={onRefresh} disabled={refreshing}>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M20 11a8 8 0 1 0-.7 4.3" />
        <path d="M20 5v6h-6" />
      </svg>
      {refreshing ? 'Checking…' : 'Refresh'}
    </button>
  )
}

export function StatusPanel({ status, routeConfirmed, statusFreshness, onRefresh, refreshing }: {
  status: RouteStatus | null
  routeConfirmed: boolean
  statusFreshness?: StatusFreshness
  onRefresh: () => void
  refreshing: boolean
}) {
  if (!status) {
    return (
      <section className="status-panel status-pending" aria-live="polite">
        <p className="status-kicker">Journey status</p>
        <h2>Current status unavailable</h2>
        <p>Check again when you have a connection.</p>
        <div className="status-foot">
          <span className="status-checked">Not checked yet</span>
          <RefreshButton onRefresh={onRefresh} refreshing={refreshing} />
        </div>
      </section>
    )
  }

  const simulated = status.lift_alerts.some((alert) => alert.source === 'simulated') || status.disruption?.source === 'simulated'
  const freshness = statusFreshness ?? (status.stale ? 'stale' : 'current')

  if (status.replan_failed) {
    return (
      <section className="status-panel status-critical" aria-live="assertive">
        <p className="status-kicker">Important route warning</p>
        <h2>Previous plan — may not be usable</h2>
        <p>{status.overall.detail}</p>
        <div className="status-foot">
          <span className="status-checked">Last checked {formatSingaporeDateTime(status.observed_at)}</span>
          <RefreshButton onRefresh={onRefresh} refreshing={refreshing} />
        </div>
      </section>
    )
  }

  return (
    <section className={`status-panel status-${status.overall.severity}`} aria-live="polite">
      <p className="status-kicker">{freshness === 'failed' ? 'Status update unavailable' : freshness === 'stale' ? 'Last reported status' : 'Journey status'}</p>
      <h2>{status.overall.headline}</h2>
      <p>{status.overall.detail}</p>
      {freshness === 'failed' && <p className="status-qualification">Current conditions could not be updated. The time below is from the last successful check.</p>}
      {!routeConfirmed && <p className="status-qualification">The directions below have not been confirmed against this check.</p>}
      <div className="status-foot">
        <span className="status-checked">
          {freshness === 'current' ? 'Checked' : 'Last checked'} {formatSingaporeDateTime(status.observed_at)}
          {simulated && <span className="status-simulated"> Simulation</span>}
        </span>
        <RefreshButton onRefresh={onRefresh} refreshing={refreshing} />
      </div>
    </section>
  )
}
