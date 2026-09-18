import { describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../api/client'
import { JourneyCoordinator, type JourneyApi } from './journeyCoordinator'

const plan = { trip_id: 'trip-1', summary: { leave_by_label: 'Leave by 08:00' }, legs: [], attribution: [] }
const status = { trip_id: 'trip-1', overall: { severity: 'warn', headline: 'A lift is out.', detail: 'Use another exit.' }, rerouted: true, replan_failed: false, stale: false }

function api(overrides: Partial<JourneyApi> = {}): JourneyApi {
  return {
    getPlan: vi.fn().mockResolvedValue(plan),
    getStatus: vi.fn().mockResolvedValue(status),
    getOfflineBundle: vi.fn(),
    ...overrides,
  } as JourneyApi
}

describe('JourneyCoordinator', () => {
  it('reads status before the effective plan during a refresh', async () => {
    const calls: string[] = []
    const client = api({
      getPlan: vi.fn().mockImplementation(async () => { calls.push('plan'); return plan }),
      getStatus: vi.fn().mockImplementation(async () => { calls.push('status'); return status }),
    })
    const coordinator = new JourneyCoordinator(client)
    await coordinator.initialize('trip-1')
    calls.length = 0

    await coordinator.refresh()

    expect(calls).toEqual(['status', 'plan'])
    expect(coordinator.state.snapshot?.routeConfirmed).toBe(true)
  })

  it('marks retained directions unconfirmed when status succeeds but plan reload fails', async () => {
    const client = api({ getPlan: vi.fn().mockResolvedValueOnce(plan).mockRejectedValueOnce(new ApiError('UPSTREAM_UNAVAILABLE', 'Plan unavailable.', true, 503)) })
    const coordinator = new JourneyCoordinator(client)
    await coordinator.initialize('trip-1')

    await coordinator.refresh()

    expect(coordinator.state.snapshot?.status).toEqual(status)
    expect(coordinator.state.snapshot?.routeConfirmed).toBe(false)
    expect(coordinator.state.phase).toBe('degraded')
    expect(coordinator.state.message).toBe('Plan unavailable.')
  })

  it('coalesces overlapping refresh requests', async () => {
    const client = api()
    const coordinator = new JourneyCoordinator(client)
    await coordinator.initialize('trip-1')

    await Promise.all([coordinator.refresh(), coordinator.refresh()])

    expect(client.getStatus).toHaveBeenCalledTimes(1)
  })
})
