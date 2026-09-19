import { act, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ReminderControls } from './ReminderControls'

vi.mock('../../api/push', () => ({
  getPushKey: vi.fn(() => Promise.resolve({ public_key: 'BA' })),
  savePushSubscription: vi.fn(() => Promise.resolve({ subscribed: true, checks: [] })),
}))

function stubPushCapableBrowser(ready: Promise<ServiceWorkerRegistration>) {
  vi.stubGlobal('Notification', class {})
  vi.stubGlobal('PushManager', class {})
  Object.defineProperty(navigator, 'serviceWorker', { value: { ready }, configurable: true })
}

describe('ReminderControls', () => {
  beforeEach(() => vi.useFakeTimers())
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    Reflect.deleteProperty(navigator, 'serviceWorker')
  })

  it('reports a failure instead of waiting forever when no service worker takes control', async () => {
    // A worker that never activates leaves navigator.serviceWorker.ready pending: it never
    // rejects, so without a timeout the button stays disabled for the rest of the session.
    stubPushCapableBrowser(new Promise<ServiceWorkerRegistration>(() => {}))
    render(<ReminderControls tripId="trip-1" />)

    await act(async () => {
      screen.getByRole('button', { name: 'Enable reminders' }).click()
    })
    expect(screen.getByRole('button', { name: 'Enabling reminders…' })).toBeDisabled()

    await act(async () => {
      vi.advanceTimersByTime(5_000)
    })

    expect(screen.getByText(/did not start the background service/i)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Enable reminders' })).toBeEnabled()
  })

  it('explains itself on a browser without push support instead of starting', async () => {
    // jsdom implements neither Notification nor PushManager, so this is the unsupported path.
    render(<ReminderControls tripId="trip-1" />)

    await act(async () => {
      screen.getByRole('button', { name: 'Enable reminders' }).click()
    })

    expect(screen.getByText(/does not support journey reminders/i)).toBeVisible()
  })
})
