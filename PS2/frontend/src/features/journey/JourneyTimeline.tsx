import type { TripPlan } from '../../api/types'
import { deriveLegImpacts, type ImpactStatus } from './legImpact'
import { placeName } from './placeName'

type Leg = TripPlan['legs'][number]

function accessLabel(stepFree: 'no' | 'unknown' | 'yes') {
  if (stepFree === 'unknown') return 'Step-free access not confirmed'
  if (stepFree === 'no') return 'Step-free access unavailable'
  return 'Step-free access checked'
}

/** Titles come from the structured `mode`, `to` and `line` fields. The instruction is prose
 *  written for a reader and is kept verbatim as body text; it is never parsed for facts. */
function title(leg: Leg) {
  if (leg.mode === 'rail') return `${leg.line.name} to ${placeName(leg.to.name)}`
  return `Walk to ${placeName(leg.to.name)}`
}

function duration(leg: Leg) {
  return typeof leg.duration_min === 'number' ? `${leg.duration_min} min` : null
}

/** The short, scannable facts under the title: the door she needs and how far she walks.
 *  Everything here is a field, not a phrase lifted out of the instruction. */
function facts(leg: Leg) {
  if (leg.mode === 'walk') {
    return [leg.to.exit_code, `${Math.round(leg.distance_m)} m`].filter(Boolean).join(' · ')
  }
  const board = leg.access.board_at.exit_code
  const alight = leg.access.alight_at.exit_code
  return [board && `Board at ${board}`, alight && `Alight at ${alight}`].filter(Boolean).join(' · ')
}

export function JourneyTimeline({ plan, status = null }: { plan: TripPlan; status?: ImpactStatus }) {
  // The instruction for the last walk says "take the lift to street level". When that lift is
  // the one that is out, the step she is standing at has to say so — the status panel at the
  // top of the page is three screens away by then.
  const impacts = deriveLegImpacts(plan.legs, status)
  // Repeating "Step-free access checked" on every step buries the one step where it is not
  // true. When the whole journey is confirmed it is stated once; the moment any step differs,
  // every step carries its own label again so the exception cannot hide.
  const allStepFree = plan.legs.every((leg) => leg.step_free === 'yes')

  return (
    <>
      {allStepFree && <p className="journey-access">Step-free access checked on every step.</p>}
      <ol className="journey-timeline" aria-label="Journey steps">
        {plan.legs.map((leg, index) => (
          <li key={leg.leg_id} className="journey-leg" data-mode={leg.mode}>
            <span className="journey-marker" aria-hidden="true">{index + 1}</span>
            <div className="journey-step">
              <p className="journey-mode"><span className={`mode-dot mode-${leg.mode}`} aria-hidden="true" />{leg.mode === 'rail' ? 'Train' : 'Walk'}</p>
              <div className="journey-step-head">
                <h3>{title(leg)}</h3>
                {duration(leg)
                  ? <span className="journey-duration">{duration(leg)}</span>
                  : <span className="journey-duration">Time not available</span>}
              </div>
              {facts(leg) && <p className="journey-detail">{facts(leg)}</p>}
              <p className="journey-detail">{leg.instruction}</p>
              {!allStepFree && <p className="journey-access">{accessLabel(leg.step_free)}</p>}
              {impacts.get(leg.leg_id)?.reason && <p className="journey-warning" data-impact={impacts.get(leg.leg_id)?.level}>{impacts.get(leg.leg_id)?.reason}</p>}
              {leg.mode === 'walk' && leg.surface_warnings.map((warning) => <p className="journey-warning" key={warning}>{warning}</p>)}
            </div>
          </li>
        ))}
      </ol>
    </>
  )
}
