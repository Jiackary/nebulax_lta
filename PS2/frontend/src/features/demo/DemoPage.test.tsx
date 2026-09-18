import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { DemoPage } from './DemoPage'

describe('DemoPage', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('labels scenario toggles as shared simulation state', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ enabled: false, scenarios: { lift_outage_outram: false, ewl_disruption: false }, note: 'Demo mode' }), { headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetchMock)
    render(<DemoPage />)

    await screen.findByText(/shared demo server/i)
    await user.click(screen.getByLabelText(/simulate a lift outage/i))

    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/scenario', expect.objectContaining({ method: 'POST' })))
  })
})
