// Journey states derived from the frozen payloads. Each one is a state the user can actually
// reach; the names match the phases in `journeyCoordinator.ts`.
import type { Alternatives, OfflineBundle, RouteStatus, TripPlan } from '../../src/api/types'
import { alternatives, offlineBundle, okStatus, readyPlan } from './payloads'

function clone<T>(value: T): T {
  return structuredClone(value)
}

export const planReady: TripPlan = clone(readyPlan)

export const statusCurrent: RouteStatus = clone(okStatus)

export const statusStale: RouteStatus = {
  ...clone(okStatus),
  stale: true,
  checks: {
    ...clone(okStatus).checks,
    label: 'Last checked 08:41. We could not reach the live feed since.',
  },
}

// A real disruption on her leg: the status panel, the route overview and the map all have to
// agree that the East-West Line portion is the affected one.
export const statusDisrupted: RouteStatus = {
  ...clone(okStatus),
  overall: {
    severity: 'critical',
    headline: 'Lift out of service at Outram Park Exit 6.',
    detail: 'The lift you use to reach street level is under maintenance. Use Exit 4 and allow ten more minutes.',
    action: { kind: 'view_alternatives', label: 'See other ways to get there' },
  },
  lift_alerts: [
    {
      ...clone(okStatus).lift_alerts[0],
      station_code: 'EW16',
      station_name: 'Outram Park',
      station_id: 'EW16',
      line: 'EWL',
      exit_code: 'Exit 6',
      blocked_exit_refs: ['6'],
      resolution: 'matched_exit',
      parsed_exits: ['6'],
      severity: 'critical',
      detail: "Exit 6's lift is under maintenance.",
      affects_route: true,
    },
  ],
  disruption: {
    line: 'EWL',
    severity: 'warn',
    headline: 'East-West Line trains are running slower than usual.',
    detail: 'Trains are about eight minutes slower between Bugis and Outram Park while a signalling fault is repaired.',
    delay_min: 8,
    delay_basis: 'Reported by LTA at 09:05.',
    affected_stations: ['EW12', 'EW13', 'EW14', 'EW15', 'EW16'],
    on_her_route: true,
    free_bus_available: true,
    free_bus_islandwide: false,
    source: 'live',
    observed_at: '2026-09-19T09:05:00+08:00',
    stale: false,
  },
}

export const statusReplanFailed: RouteStatus = {
  ...clone(statusDisrupted),
  replan_failed: true,
}

export const planReplanFailed: TripPlan = { ...clone(readyPlan), replan_failed: true }

// The single-leg and no-leg shapes the route diagram has to survive.
export const planSingleLeg: TripPlan = { ...clone(readyPlan), legs: [clone(readyPlan).legs[1]] }

export const planNoOverview: TripPlan = {
  ...clone(readyPlan),
  legs: [],
  map: { bbox: [], geometry: { type: 'FeatureCollection', features: [] } },
}

// Long names and long labels: the overflow candidates the plan asks us to cover explicitly.
const LONG_DESTINATION =
  'Singapore General Hospital Outram Campus, Block 3 Specialist Outpatient Clinic, Level 4 Counter B'

export const planLongNames: TripPlan = (() => {
  const plan = clone(readyPlan)
  const last = plan.legs[plan.legs.length - 1]
  last.to.name = LONG_DESTINATION
  last.instruction =
    'Leave by Exit 6 and take the lift to street level, then follow the covered walkway to ' +
    `${LONG_DESTINATION}. Sheltered most of the way.`
  plan.legs[1].to.name = 'Outram Park Interchange (East-West, North-East and Thomson-East Coast Lines)'
  plan.summary.timing_basis =
    plan.summary.timing_basis +
    ' This estimate assumes no lift queue at Outram Park and that the covered walkway to Block 3 is open.'
  return plan
})()

export const alternativesReady: Alternatives = clone(alternatives)

export const alternativesEmpty: Alternatives = {
  ...clone(alternatives),
  options: [],
  not_offered: [
    {
      label: 'Any other route',
      why_not: 'No step-free alternative reaches the hospital in time for this appointment.',
    },
  ],
}

export const savedBundle: OfflineBundle = clone(offlineBundle)
