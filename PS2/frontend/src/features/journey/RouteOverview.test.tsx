import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RouteOverview } from './RouteOverview'

const legs = [
  { leg_id: 'l1', mode: 'walk' as const, from: { name: 'Home' }, to: { name: 'Bedok MRT', exit_code: 'Exit B', station_code: 'EW5' }, duration_min: 7 },
  { leg_id: 'l2', mode: 'rail' as const, from: { name: 'Bedok MRT', station_code: 'EW5' }, to: { name: 'Outram Park', exit_code: 'Exit 6', station_code: 'EW16' }, line: { name: 'East–West Line', code: 'EWL' }, duration_min: 31 },
  { leg_id: 'l3', mode: 'walk' as const, from: { name: 'Outram Park', station_code: 'EW16' }, to: { name: 'Singapore General Hospital, Block 3' }, duration_min: 10 },
]

describe('RouteOverview', () => {
  it('ties a label to every node instead of joining the stop names into a paragraph', () => {
    render(<RouteOverview legs={legs} />)

    const labels = screen.getAllByRole('listitem').map((item) => item.textContent)
    expect(labels).toEqual(expect.arrayContaining([
      expect.stringContaining('Home'),
      expect.stringContaining('Bedok MRT'),
      expect.stringContaining('Exit B'),
      expect.stringContaining('Singapore General'),
    ]))
    expect(screen.getByText(/schematic.*not to scale/i)).toBeVisible()
  })

  it('describes the whole route for a reader who cannot see the trace', () => {
    render(<RouteOverview legs={legs} />)

    expect(screen.getByRole('img', { name: /route from Home to Singapore General Hospital, Block 3/i })).toBeInTheDocument()
  })

  it('marks the affected leg and says why, so the diagram agrees with the map', () => {
    render(<RouteOverview legs={legs} status={{
      lift_alerts: [{ station_code: 'EW16', station_name: 'Outram Park', affects_route: true, severity: 'critical', label: 'Lift out of service' }],
    }} />)

    // A lift outage touches both legs that meet at the station, but it is one outage, so the
    // trace states it once rather than beside each of them.
    expect(screen.getByText(/dashed section affected: lift out of service at outram park/i)).toBeVisible()
    expect(screen.getByRole('img', { name: /affected: lift out of service at outram park/i })).toBeInTheDocument()
  })

  it('says so plainly when there are no legs to draw', () => {
    render(<RouteOverview legs={[]} />)

    expect(screen.getByText(/route overview unavailable/i)).toBeVisible()
  })
})
