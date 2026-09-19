import { describe, expect, it } from 'vitest'

import { deriveLegImpacts, type ImpactLeg, type ImpactStatus } from './legImpact'

const legs: ImpactLeg[] = [
  { leg_id: 'l1', mode: 'walk', from: {}, to: { station_code: 'EW5' } },
  { leg_id: 'l2', mode: 'rail', from: { station_code: 'EW5' }, to: { station_code: 'EW16' }, line: { code: 'EWL' } },
  { leg_id: 'l3', mode: 'walk', from: { station_code: 'EW16' }, to: {} },
]

const disruption: NonNullable<ImpactStatus>['disruption'] = {
  line: 'EWL',
  severity: 'critical',
  headline: 'East-West Line delays towards Tuas Link',
  on_her_route: true,
  affected_stations: ['EW5', 'EW16'],
}

describe('deriveLegImpacts', () => {
  it('marks no leg when there is no status yet', () => {
    const impacts = deriveLegImpacts(legs, null)

    expect([...impacts.values()].every((impact) => impact.level === 'none')).toBe(true)
  })

  it('marks only the rail leg when its line is disrupted', () => {
    const impacts = deriveLegImpacts(legs, { disruption })

    expect(impacts.get('l2')).toEqual({ level: 'critical', reason: 'East-West Line delays towards Tuas Link' })
    expect(impacts.get('l1')?.level).toBe('none')
    expect(impacts.get('l3')?.level).toBe('none')
  })

  it('ignores a disruption on a line she does not travel on', () => {
    const impacts = deriveLegImpacts(legs, {
      disruption: { ...disruption, line: 'NEL', affected_stations: ['NE1'], on_her_route: false },
    })

    expect(impacts.get('l2')?.level).toBe('none')
  })

  it('marks the walk legs touching a station whose lift is out', () => {
    const impacts = deriveLegImpacts(legs, {
      lift_alerts: [
        { station_code: 'EW16', station_name: 'Outram Park', affects_route: true, severity: 'warn', label: 'Lift out of service' },
        { station_code: 'DT10', station_name: 'Stevens', affects_route: false, severity: 'warn', label: 'Lift out of service' },
      ],
    })

    expect(impacts.get('l3')).toEqual({ level: 'warn', reason: 'Lift out of service at Outram Park' })
    expect(impacts.get('l2')?.level).toBe('warn')
    expect(impacts.get('l1')?.level).toBe('none')
  })

  it('marks walk legs but not the train when rain is expected', () => {
    const impacts = deriveLegImpacts(legs, {
      weather: { affects_route: true, rain_expected: true, severity: 'warn', label: 'Rain expected' },
    })

    expect(impacts.get('l1')).toEqual({ level: 'warn', reason: 'Rain expected' })
    expect(impacts.get('l3')?.level).toBe('warn')
    expect(impacts.get('l2')?.level).toBe('none')
  })

  it('keeps the most severe reason when a leg is hit twice', () => {
    const impacts = deriveLegImpacts(legs, {
      disruption,
      lift_alerts: [{ station_code: 'EW5', station_name: 'Bedok', affects_route: true, severity: 'warn', label: 'Lift out of service' }],
    })

    expect(impacts.get('l2')).toEqual({ level: 'critical', reason: 'East-West Line delays towards Tuas Link' })
  })
})
