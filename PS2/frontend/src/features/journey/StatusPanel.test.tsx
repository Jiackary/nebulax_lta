import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { StatusPanel } from './StatusPanel'

const status = {
  overall: { severity: 'ok', headline: 'Your usual route is clear.', detail: 'No known problems.' },
  observed_at: '2026-10-20T09:00:00+08:00',
  stale: true,
  replan_failed: false,
  lift_alerts: [],
  disruption: null,
}

describe('StatusPanel', () => {
  it('qualifies a stale all-clear as last reported', () => {
    render(<StatusPanel status={status as never} routeConfirmed onRefresh={() => {}} refreshing={false} />)

    expect(screen.getByText(/last reported status/i)).toBeVisible()
    expect(screen.getByText(/your usual route is clear/i)).toBeVisible()
  })

  it('puts the unsafe retained-route warning ahead of a failed replan', () => {
    render(<StatusPanel status={{ ...status, replan_failed: true } as never} routeConfirmed={false} onRefresh={() => {}} refreshing={false} />)

    expect(screen.getByText(/previous plan.*may not be usable/i)).toBeVisible()
  })

  it('does not present retained all-clear status as current after a failed refresh', () => {
    render(<StatusPanel status={{ ...status, stale: false } as never} routeConfirmed={false} statusFreshness="failed" onRefresh={() => {}} refreshing={false} />)

    expect(screen.getByText(/could not be updated/i)).toBeVisible()
    expect(screen.getByText(/directions below have not been confirmed/i)).toBeVisible()
  })
})
