import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import type { OfflineBundle, TripPlan } from '../../api/types'
import { JourneyPage } from './JourneyPage'
import { JourneyContext } from './journeyContext'
import type { JourneySnapshot } from './journeyCoordinator'

const plan = {
  trip_id: 't_test',
  appointment_at: '2026-09-21T10:30:00+08:00',
  summary: {
    leave_by: '2026-09-21T09:22:00+08:00',
    leave_by_label: 'Leave at 09:22',
    arrival_window: ['2026-09-21T10:06:32+08:00', '2026-09-21T10:14:48+08:00'],
    arrival_label: 'arrive 10:06–10:14',
    appointment_label: 'appointment 10:30',
    buffer_min: 15,
    duration_min: 49,
    range_min: [45, 53],
    timing_basis: 'Train ride is a scheduled 31 min.',
    step_free: 'yes',
    sheltered_pct: 60,
    walk_distance_m: 707,
  },
  legs: [],
  map: { bbox: [], geometry: { type: 'FeatureCollection', features: [] } },
  attribution: ['© OpenStreetMap contributors'],
} as unknown as TripPlan

function renderSaved(snapshot: Partial<JourneySnapshot>) {
  const value = {
    phase: 'degraded' as const,
    operation: 'idle' as const,
    message: null,
    snapshot: {
      tripId: 't_test',
      plan,
      status: null,
      receivedAt: '2026-09-19T05:16:14.011Z',
      source: 'saved' as const,
      routeConfirmed: false,
      statusFreshness: 'unavailable' as const,
      warnings: [],
      ...snapshot,
    },
    refresh: () => Promise.resolve(),
    prepareOffline: () => Promise.resolve({} as OfflineBundle),
  }
  return render(
    <MemoryRouter>
      <JourneyContext.Provider value={value}>
        <JourneyPage tripId="t_test" />
      </JourneyContext.Provider>
    </MemoryRouter>,
  )
}

describe('journey page offline notice', () => {
  beforeEach(() => {
    vi.stubEnv('TZ', 'UTC')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  // A raw ISO stamp is not a time Mdm Lim can read, and `2026-09-19T05:16:14.011Z` is a single
  // token with no wrap opportunity, which widened the whole journey grid past the viewport.
  it('states when the copy was saved in plain Singapore time, not as an ISO string', async () => {
    renderSaved({ generatedAt: '2026-09-19T13:16:13+08:00' })

    const notice = await screen.findByText(/offline copy/i)
    expect(notice).toHaveTextContent('13:16')
    expect(notice.textContent).not.toMatch(/\d{4}-\d{2}-\d{2}T/)
  })

  it('leaves out the generated time when the saved copy does not carry one', async () => {
    renderSaved({})

    await waitFor(() => expect(screen.getByText(/offline copy/i)).toBeVisible())
    expect(screen.getByText(/offline copy/i).textContent).not.toMatch(/plan generated/i)
  })
})
