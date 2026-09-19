// The brief requires the affected portion of the route to be distinguished from the
// unaffected portion. The plan says which legs exist; the status says what is wrong and
// where. This maps one onto the other so the map and the timeline can agree.

export type LegImpactLevel = 'none' | 'warn' | 'critical'

export type LegImpact = { level: LegImpactLevel; reason: string | null }

export type ImpactLeg = {
  leg_id: string
  mode: 'rail' | 'walk'
  from: { station_code?: string | null }
  to: { station_code?: string | null }
  line?: { code?: string | null } | null
}

export type ImpactStatus = {
  disruption?: {
    line?: string | null
    severity?: string | null
    headline?: string | null
    on_her_route?: boolean | null
    affected_stations?: string[] | null
  } | null
  lift_alerts?: {
    station_code?: string | null
    station_name?: string | null
    affects_route?: boolean | null
    severity?: string | null
    label?: string | null
  }[] | null
  weather?: {
    affects_route?: boolean | null
    rain_expected?: boolean | null
    severity?: string | null
    label?: string | null
  } | null
} | null

const RANK: Record<LegImpactLevel, number> = { none: 0, warn: 1, critical: 2 }

function levelFrom(severity: string | null | undefined): LegImpactLevel {
  return severity === 'critical' ? 'critical' : 'warn'
}

function stationsOf(leg: ImpactLeg) {
  return [leg.from.station_code, leg.to.station_code].filter((code): code is string => Boolean(code))
}

export function deriveLegImpacts(legs: ImpactLeg[], status: ImpactStatus): Map<string, LegImpact> {
  const impacts = new Map<string, LegImpact>(legs.map((leg) => [leg.leg_id, { level: 'none', reason: null }]))
  if (!status) return impacts

  const raise = (legId: string, level: LegImpactLevel, reason: string) => {
    const current = impacts.get(legId)
    if (!current || RANK[level] <= RANK[current.level]) return
    impacts.set(legId, { level, reason })
  }

  const { disruption, weather } = status
  for (const leg of legs) {
    const stations = stationsOf(leg)

    // A line disruption only touches the legs actually riding that line.
    if (disruption?.on_her_route && leg.mode === 'rail') {
      const sameLine = Boolean(disruption.line) && leg.line?.code === disruption.line
      const touchesAffected = (disruption.affected_stations ?? []).some((code) => stations.includes(code))
      if (sameLine || touchesAffected) raise(leg.leg_id, levelFrom(disruption.severity), disruption.headline ?? 'Delays on this line')
    }

    // A lift outage is a property of a station, so it touches every leg that ends or
    // starts there: the walk to the gantry as much as the ride itself.
    for (const alert of status.lift_alerts ?? []) {
      if (!alert.affects_route || !alert.station_code || !stations.includes(alert.station_code)) continue
      const where = alert.station_name ? ` at ${alert.station_name}` : ''
      raise(leg.leg_id, levelFrom(alert.severity), `${alert.label ?? 'Lift out of service'}${where}`)
    }

    // Rain is only a problem where she is outside.
    if (leg.mode === 'walk' && weather?.affects_route && weather.rain_expected) {
      raise(leg.leg_id, levelFrom(weather.severity), weather.label ?? 'Rain expected')
    }
  }

  return impacts
}
