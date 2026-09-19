import { Component, Suspense, lazy, useMemo, type ReactNode } from 'react'

import { deriveLegImpacts, type ImpactLeg, type ImpactStatus } from './legImpact'
import type { RouteGeometry } from './RouteMap'

// MapLibre is far and away the heaviest thing the app loads. Splitting it out keeps the
// departure time, which is what she actually opens this for, on the first paint.
const RouteMap = lazy(() => import('./RouteMap').then((module) => ({ default: module.RouteMap })))

function MapUnavailable({ reason }: { reason: string }) {
  return (
    <section className="route-map route-map-unavailable">
      <strong>{reason}</strong>
      <span>Your written steps below are complete and do not need the map.</span>
    </section>
  )
}

// The map chunk is deliberately not precached, so offline it cannot load at all, and a
// failed dynamic import throws during render. With no error boundary anywhere in the app
// that throw blanks the entire page — including the written steps she saved precisely
// because she expected to be offline. Contain it to the map.
class MapBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }

  static getDerivedStateFromError() {
    return { failed: true }
  }

  render() {
    if (this.state.failed) return <MapUnavailable reason="The map could not be loaded." />
    return this.props.children
  }
}

type PanelLeg = ImpactLeg & { from: { name?: string | null }; to: { name?: string | null } }

export function RouteMapPanel({ legs, map, status, offline = false }: {
  legs: PanelLeg[]
  map?: { bbox?: number[] | null; geometry?: RouteGeometry | null } | null
  status: ImpactStatus
  offline?: boolean
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

  // Offline tile caching is parked on licensing grounds, so there is no basemap to draw on
  // and no point downloading a megabyte of map code to prove it.
  if (offline) return <MapUnavailable reason="The map is not available offline." />

  const bbox = map?.bbox
  const geometry = map?.geometry
  if (!geometry?.features?.length || !bbox || bbox.length !== 4) {
    return <MapUnavailable reason="The route map is not available for this journey." />
  }

  return (
    <MapBoundary>
      <Suspense fallback={<div className="route-map route-map-loading" role="status">Loading your route map…</div>}>
        <RouteMap geometry={geometry} bbox={bbox as [number, number, number, number]} impacts={impacts} label={label} />
      </Suspense>
    </MapBoundary>
  )
}
