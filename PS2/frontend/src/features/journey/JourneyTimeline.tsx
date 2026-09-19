import type { TripPlan } from '../../api/types'

function accessLabel(stepFree: 'no' | 'unknown' | 'yes') {
  if (stepFree === 'unknown') return 'Step-free access not confirmed'
  if (stepFree === 'no') return 'Step-free access unavailable'
  return 'Step-free access checked'
}

export function JourneyTimeline({ plan }: { plan: TripPlan }) {
  return (
    <ol className="journey-timeline" aria-label="Journey steps">
      {plan.legs.map((leg, index) => (
        <li key={leg.leg_id} className="journey-leg">
          <span className="journey-marker" aria-hidden="true">{index + 1}</span>
          <div className="journey-step">
            <p className="journey-mode"><span className={`mode-dot mode-${leg.mode}`} aria-hidden="true" />{leg.mode === 'rail' ? leg.line.name : 'Walk'}</p>
            <h3>{leg.instruction}</h3>
            <p className="journey-detail">
              {leg.duration_min === null ? 'Travel time not available' : `About ${leg.duration_min} minutes`}
              {leg.mode === 'walk' && ` · ${Math.round(leg.distance_m)} metres`}
            </p>
            <p className="journey-access">{accessLabel(leg.step_free)}</p>
            {leg.mode === 'walk' && leg.surface_warnings.map((warning) => <p className="journey-warning" key={warning}>{warning}</p>)}
            {leg.mode === 'rail' && <p className="journey-access">Board at {leg.access.board_at.exit_code}; alight at {leg.access.alight_at.exit_code}.</p>}
          </div>
        </li>
      ))}
    </ol>
  )
}
