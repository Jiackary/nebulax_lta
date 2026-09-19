import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from '../../App'

function planPage() {
  window.history.replaceState({}, '', '/plan')
  return render(<App />)
}

describe('appointment form', () => {
  afterEach(() => {
    localStorage.clear()
    vi.unstubAllGlobals()
    window.history.replaceState({}, '', '/')
  })

  it('keeps the form visible and explains an incomplete appointment', async () => {
    const user = userEvent.setup()
    planPage()

    const appointment = screen.getByLabelText(/appointment date and time/i)
    await user.clear(appointment)
    await user.click(screen.getByRole('button', { name: /plan journey/i }))

    expect(screen.getByText(/choose an appointment date and time/i)).toBeVisible()
    expect(appointment).toBeVisible()
  })

  it('creates one journey with an explicit Singapore offset', async () => {
    const user = userEvent.setup()
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ trip_id: 'trip-123' }), {
      headers: { 'Content-Type': 'application/json' },
    }))
    vi.stubGlobal('fetch', fetchMock)
    planPage()

    const appointment = screen.getByLabelText(/appointment date and time/i)
    await user.clear(appointment)
    fireEvent.change(appointment, { target: { value: '2026-10-20T09:00' } })
    await user.click(screen.getByRole('button', { name: /plan journey/i }))

    await waitFor(() => expect(localStorage.getItem('ps2.activeTripId')).toBe('trip-123'))
    const creates = fetchMock.mock.calls.filter(([, options]) => (options as RequestInit).method === 'POST')
    expect(creates).toHaveLength(1)
    expect(creates[0][1]).toMatchObject({
      method: 'POST',
      body: JSON.stringify({
        destination_id: 'SGH',
        appointment_at: '2026-10-20T09:00:00+08:00',
        preferences: { walking_pace: 'slow', avoid_stairs: true, prefer_sheltered: true, buffer_min: 15 },
      }),
    })
    expect(screen.getByRole('heading', { name: /loading your saved route/i })).toBeVisible()
  })

  it('explains that the request is preparing a journey while submission is pending', async () => {
    const user = userEvent.setup()
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(new Promise(() => undefined)))
    planPage()

    await user.click(screen.getByRole('button', { name: /plan journey/i }))

    expect(screen.getByText(/preparing your journey/i)).toBeVisible()
    expect(screen.getByRole('button', { name: /planning/i })).toBeDisabled()
  })
})
