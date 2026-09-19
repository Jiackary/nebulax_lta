import type { Alternatives } from '../../api/types'

type Option = Alternatives['options'][number]

function accessLabel(value: 'no' | 'unknown' | 'yes') {
  if (value === 'unknown') return 'Step-free access not confirmed'
  if (value === 'no') return 'Step-free access unavailable'
  return 'Step-free access checked'
}

export function OptionCard({ option }: { option: Option }) {
  // `duration_min` is absent, not null, on options the backend cannot time — a taxi has no
  // published journey time. Comparing against null alone rendered "About undefined minutes".
  const duration = typeof option.duration_min === 'number' ? `About ${option.duration_min} minutes` : 'Travel time not available'
  return (
    <article className="option-card">
      <div className="option-heading"><div><p className="journey-mode">Option {option.rank} · {option.mode}</p><h2>{option.label}</h2></div>{option.delta_min !== null && <span className="time-delta">{option.delta_min > 0 ? `+${option.delta_min}` : option.delta_min} min</span>}</div>
      <p>{option.why}</p>
      <p className="journey-detail">{duration}</p>
      <p className="journey-access">{accessLabel(option.step_free)}</p>
      {option.mode === 'bus' && <p className="journey-detail">Bus {option.bus.service_no}: {option.bus.board_stop} to {option.bus.alight_stop}. {option.bus.eta_min === null ? 'Arrival time not available.' : `Next bus in about ${option.bus.eta_min} minutes.`}</p>}
      {option.mode === 'taxi' && <p className="journey-detail">Taxi stand: {option.taxi_stand.name ?? 'Location not available'}.</p>}
      {option.mode === 'rail' && option.viable === false && <p className="journey-warning">This departure time has already passed.</p>}
      <p className="option-basis">{option.timing_basis}</p>
    </article>
  )
}
