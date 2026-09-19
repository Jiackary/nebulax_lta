import type { RouteStatus } from '../../api/types'
import { formatSingaporeDateTime } from '../../lib/singaporeTime'
import type { StatusFreshness } from './journeyCoordinator'

export function StatusPanel({ status, routeConfirmed, statusFreshness }: {
  status: RouteStatus | null
  routeConfirmed: boolean
  statusFreshness?: StatusFreshness
}) {
  if (!status) return <section className="status-panel status-pending" aria-live="polite"><strong>Current status unavailable.</strong><span>Check again when you have a connection.</span></section>

  const simulated = status.lift_alerts.some((alert) => alert.source === 'simulated') || status.disruption?.source === 'simulated'
  const freshness = statusFreshness ?? (status.stale ? 'stale' : 'current')
  if (status.replan_failed) {
    return (
      <section className="status-panel status-critical" aria-live="assertive">
        <p className="status-kicker">Important route warning</p>
        <h2>Previous plan — may not be usable</h2>
        <p>{status.overall.detail}</p>
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
      <div className="status-meta">
        <span>{freshness === 'current' ? 'Checked' : 'Last checked'} {formatSingaporeDateTime(status.observed_at)}</span>
        {simulated && <span>Simulation</span>}
      </div>
    </section>
  )
}
