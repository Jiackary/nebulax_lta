import { deriveLegImpacts, type ImpactLeg, type ImpactStatus, type LegImpact } from './legImpact'
import { shortPlaceName } from './placeName'

type OverviewLeg = ImpactLeg & {
  from: { name: string; exit_code?: string | null; station_code?: string | null }
  to: { name: string; exit_code?: string | null; station_code?: string | null }
  line?: { name: string; code?: string | null } | null
  duration_min?: number | null
}

type Node = { name: string; label: string; meta: string | null; endpoint: boolean }

// A stop column is about 64px wide at 320px. Two short lines is all it can carry before it
// stops being something you take in at a glance.
const LABEL_BUDGET = 20

function metaFor(point: { exit_code?: string | null; station_code?: string | null }) {
  return point.exit_code ?? point.station_code ?? null
}

function legLabel(leg: OverviewLeg) {
  return leg.mode === 'rail' ? leg.line?.name ?? 'Train' : 'Walk'
}

/**
 * A schematic route trace: an SVG connector per leg, dotted for walking and solid for rail,
 * with HTML labels sitting under the node each one names. It is deliberately not to scale
 * and needs no map tiles, so it still draws when the basemap cannot load, offline, or when
 * the backend sent no geometry at all.
 *
 * The connectors are drawn in a viewBox that is stretched horizontally to the available
 * width. Stroke width is held constant with `vector-effect`, and the dash pattern is
 * expressed against `pathLength` so it stays proportional at any width instead of turning
 * into one long dash on a wide screen.
 */
export function RouteOverview({ legs, status = null }: { legs: OverviewLeg[]; status?: ImpactStatus }) {
  if (legs.length === 0) {
    return (
      <section className="route-trace-unavailable">
        <strong>Route overview unavailable.</strong>
        <span>Your written steps below are complete and do not need it.</span>
      </section>
    )
  }

  const nodes: Node[] = [
    { name: legs[0].from.name, label: shortPlaceName(legs[0].from.name, LABEL_BUDGET), meta: metaFor(legs[0].from), endpoint: true },
    ...legs.map((leg, index) => ({
      name: leg.to.name,
      label: shortPlaceName(leg.to.name, LABEL_BUDGET),
      meta: metaFor(leg.to),
      endpoint: index === legs.length - 1,
    })),
  ]

  // Nodes sit at the centre of equal columns, so the label grid below lines up with them
  // without measuring anything.
  const at = (index: number) => ((index + 0.5) / nodes.length) * 100

  // The brief requires the affected portion of the route to be distinguished. The map does
  // that too, and both read the same mapping, so the diagram and the map can never disagree
  // about which leg is in trouble — and the diagram still says so when the map cannot draw.
  const impacts = deriveLegImpacts(legs, status)
  const impactOf = (leg: OverviewLeg): LegImpact => impacts.get(leg.leg_id) ?? { level: 'none', reason: null }

  const affectedReasons = [...new Set(legs
    .map((leg) => impactOf(leg).reason)
    .filter((reason): reason is string => Boolean(reason)))]
  const worst = legs.some((leg) => impactOf(leg).level === 'critical')
    ? 'critical'
    : legs.some((leg) => impactOf(leg).level === 'warn') ? 'warn' : 'none'
  const description = `Route from ${nodes[0].name} to ${nodes[nodes.length - 1].name}, via ${
    legs.map((leg) => `${legLabel(leg)} to ${leg.to.name}`).join(', then ')
  }. ${affectedReasons.length ? `Affected: ${affectedReasons.join('. ')}.` : 'Nothing is affecting this route.'} Schematic, not to scale.`

  return (
    <section className="route-trace" data-worst={worst} aria-labelledby="route-trace-heading">
      <h2 id="route-trace-heading" className="eyebrow">Your route</h2>
      <div className="route-trace-figure" role="img" aria-label={description}>
        <div className="route-trace-rail">
          <svg className="route-trace-line" viewBox="0 0 100 12" preserveAspectRatio="none" aria-hidden="true" focusable="false">
            {legs.map((leg, index) => (
              <line
                key={leg.mode + index}
                className="route-trace-seg"
                data-mode={leg.mode}
                data-impact={impactOf(leg).level}
                x1={at(index)}
                y1={6}
                x2={at(index + 1)}
                y2={6}
                pathLength={100}
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </svg>
          {nodes.map((node, index) => (
            <span
              key={`${node.name}-${index}`}
              className="route-node"
              data-endpoint={node.endpoint}
              style={{ '--at': `${at(index)}%` } as React.CSSProperties}
            />
          ))}
        </div>
        <ol className="route-trace-labels" style={{ '--nodes': nodes.length } as React.CSSProperties}>
          {nodes.map((node, index) => (
            <li key={`${node.name}-label-${index}`}>
              <span className="route-node-name">{node.label}</span>
              {node.meta && <span className="route-node-meta">{node.meta}</span>}
            </li>
          ))}
        </ol>
      </div>
      <ul className="route-trace-modes">
        {legs.map((leg, index) => {
          const impact = impactOf(leg)
          return (
            <li key={`${leg.mode}-key-${index}`} data-impact={impact.level}>
              <span className="route-trace-key" data-mode={leg.mode} data-impact={impact.level} aria-hidden="true" />
              {legLabel(leg)}
              {typeof leg.duration_min === 'number' ? ` · ${leg.duration_min} min` : ''}
            </li>
          )
        })}
      </ul>
      {/* Colour is never the only carrier. One outage usually touches two legs — the ride
          that ends at the station and the walk that starts there — so the reasons are stated
          once rather than repeated beside each of them. */}
      {affectedReasons.length > 0 && (
        <p className="route-trace-affected">Dashed section affected: {affectedReasons.join('. ')}.</p>
      )}
      <p className="route-trace-note">Schematic · not to scale</p>
    </section>
  )
}
