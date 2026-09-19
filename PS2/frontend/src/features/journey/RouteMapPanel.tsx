import { Suspense, lazy, useMemo } from 'react'

import { deriveLegImpacts, type ImpactLeg, type ImpactStatus } from './legImpact'
import type { RouteGeometry } from './RouteMap'

// MapLibre is far and away the heaviest thing the app loads. Splitting it out keeps the
// departure time, which is what she actually opens this for, on the first paint.
const RouteMap = lazy(() => import('./RouteMap').then((module) => ({ default: module.RouteMap })))

type PanelLeg = ImpactLeg & { from: { name?: string | null }; to: { name?: string | null } }

export function RouteMapPanel({ legs, map, status }: {
  legs: PanelLeg[]
  map?: { bbox?: number[] | null; geometry?: RouteGeometry | null } | null
  status: ImpactStatus
}) {
  const impacts = useMemo(() => deriveLegImpacts(legs, status), [legs, status])

  const label = useMemo(() => {
    const origin = legs[0]?.from.name ?? 'your starting point'
    const destination = legs[legs.length - 1]?.to.name ?? 'your destination'
    const reasons = [...new Set(legs.map((leg) => impacts.get(leg.leg_id)?.reason).filter(Boolean))]
    const affected = reasons.length
      ? ` The dashed section is affected: ${reasons.join('. ')}.`
      : ' No disruption is affecting this route.'
    return `Map of your route from ${origin} to ${destination}.${affected}`
  }, [legs, impacts])

  const bbox = map?.bbox
  const geometry = map?.geometry
  if (!geometry?.features?.length || !bbox || bbox.length !== 4) {
    return (
      <section className="route-map route-map-unavailable">
        <strong>The route map is not available for this journey.</strong>
        <span>Your written steps below are complete and do not need the map.</span>
      </section>
    )
  }

  return (
    <Suspense fallback={<div className="route-map route-map-loading" role="status">Loading your route map…</div>}>
      <RouteMap geometry={geometry} bbox={bbox as [number, number, number, number]} impacts={impacts} label={label} />
    </Suspense>
  )
}
