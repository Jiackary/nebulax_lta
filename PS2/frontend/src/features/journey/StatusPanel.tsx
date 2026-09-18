import type { RouteStatus } from '../../api/types'
import { formatSingaporeDateTime } from '../../lib/singaporeTime'

export function StatusPanel({ status, routeConfirmed }: { status: RouteStatus | null; routeConfirmed: boolean }) {
  if (!status) return <section className="status-panel status-pending" aria-live="polite"><strong>Status not checked yet.</strong><span>Checking for route disruptions.</span></section>

  const simulated = status.lift_alerts.some((alert) => alert.source === 'simulated') || status.disruption?.source === 'simulated'
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
      <p className="status-kicker">{status.stale ? 'Last reported status' : 'Journey status'}</p>
      <h2>{status.overall.headline}</h2>
      <p>{status.overall.detail}</p>
      {!routeConfirmed && <p className="status-qualification">The directions below have not been confirmed against this check.</p>}
      <div className="status-meta">
        <span>{status.stale ? 'Observed' : 'Checked'} {formatSingaporeDateTime(status.observed_at)}</span>
        {simulated && <span>Simulation</span>}
      </div>
    </section>
  )
}
