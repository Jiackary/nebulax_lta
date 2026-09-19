import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { REFRESH_INTERVAL_MS, STALE_AFTER_MS, useAutoRefresh } from './useAutoRefresh'

function setVisibility(state: 'visible' | 'hidden') {
  Object.defineProperty(document, 'visibilityState', { value: state, configurable: true })
  document.dispatchEvent(new Event('visibilitychange'))
}

describe('useAutoRefresh', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    Object.defineProperty(document, 'visibilityState', { value: 'visible', configurable: true })
  })
  afterEach(() => vi.useRealTimers())

  function setup(overrides: Partial<Parameters<typeof useAutoRefresh>[0]> = {}) {
    const refresh = vi.fn(() => Promise.resolve())
    const markStale = vi.fn()
    const receivedAt = new Date().toISOString()
    const view = renderHook(() => useAutoRefresh({ receivedAt, refresh, markStale, enabled: true, ...overrides }))
    return { refresh, markStale, view }
  }

  it('refreshes once the status has aged past the interval', () => {
    const { refresh } = setup()

    act(() => { vi.advanceTimersByTime(REFRESH_INTERVAL_MS - 1000) })
    expect(refresh).not.toHaveBeenCalled()

    act(() => { vi.advanceTimersByTime(30_000) })
    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('does not poll while the screen is hidden', () => {
    const { refresh } = setup()
    act(() => { setVisibility('hidden') })

    act(() => { vi.advanceTimersByTime(REFRESH_INTERVAL_MS * 3) })

    expect(refresh).not.toHaveBeenCalled()
  })

  it('refreshes as soon as she comes back to a screen left open', () => {
    const { refresh } = setup()
    act(() => { setVisibility('hidden') })
    act(() => { vi.advanceTimersByTime(REFRESH_INTERVAL_MS * 3) })
    expect(refresh).not.toHaveBeenCalled()

    act(() => { setVisibility('visible') })

    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('refreshes when the connection comes back, however recent the last check', () => {
    const { refresh } = setup()

    act(() => { window.dispatchEvent(new Event('online')) })

    expect(refresh).toHaveBeenCalledTimes(1)
  })

  it('marks the status stale once it is too old to describe as current', () => {
    const { markStale } = setup()

    act(() => { vi.advanceTimersByTime(STALE_AFTER_MS + 1000) })

    expect(markStale).toHaveBeenCalled()
  })

  it('does nothing at all when disabled', () => {
    const { refresh, markStale } = setup({ enabled: false })

    act(() => { vi.advanceTimersByTime(STALE_AFTER_MS * 2) })
    act(() => { window.dispatchEvent(new Event('online')) })

    expect(refresh).not.toHaveBeenCalled()
    expect(markStale).not.toHaveBeenCalled()
  })
})
