import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { OptionCard } from './OptionCard'

describe('OptionCard', () => {
  it('shows missing bus timing and accessibility as unknown', () => {
    render(<OptionCard option={{
      option_id: 'bus-1', label: 'Bus 10', mode: 'bus', why: 'Rail disruption', delta_min: null,
      step_free: 'unknown', severity: 'warn', timing_basis: 'Arrival time not available', legs: [], rank: 1,
      duration_min: null, bus: { service_no: '10', board_stop: 'Bedok', board_stop_code: '1', alight_stop: 'SGH', alight_stop_code: '2', stops: null, distance_km: null, walk_min: null, ride_min: null, eta_min: null, eta_is_scheduled: null, load: null, load_label: null, wheelchair_accessible: null, not_running: null, first_bus: null, last_bus: null, observed_at: null, stale: null },
    } as never} />)

    expect(screen.getByText(/travel time not available/i)).toBeVisible()
    expect(screen.getByText(/step-free access not confirmed/i)).toBeVisible()
    expect(screen.queryByRole('button', { name: /use this route/i })).toBeNull()
  })
})
