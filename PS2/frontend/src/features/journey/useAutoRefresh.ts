import { useEffect, useRef } from 'react'

// A "leave by" time is only worth reading if it still reflects the network. The screen can
// sit open on a kitchen table for an hour before she picks the phone up again, so it has to
// bring itself up to date rather than wait to be tapped.
export const REFRESH_INTERVAL_MS = 60_000
export const STALE_AFTER_MS = 5 * 60_000
const TICK_MS = 15_000

export function useAutoRefresh({ receivedAt, refresh, markStale, enabled }: {
  receivedAt: string | null
  refresh: () => Promise<void>
  markStale: () => void
  enabled: boolean
}) {
  // Held in refs so a new callback identity does not restart the timer mid-cycle.
  const callbacks = useRef({ refresh, markStale })
  useEffect(() => {
    callbacks.current = { refresh, markStale }
  }, [refresh, markStale])
  // A failed refresh leaves the status as old as it was, so age alone would retry on every
  // tick. Spacing attempts keeps a backend that is down from being hammered by an open tab.
  const lastAttempt = useRef(0)

  useEffect(() => {
    if (!enabled) return
    const since = receivedAt ? new Date(receivedAt).getTime() : Number.NaN
    const age = () => (Number.isNaN(since) ? Number.POSITIVE_INFINITY : Date.now() - since)

    // Polling a screen nobody is looking at spends her battery and the LTA quota for nothing.
    const attempt = () => {
      lastAttempt.current = Date.now()
      void callbacks.current.refresh()
    }
    const refreshIfDue = () => {
      if (document.visibilityState !== 'visible') return
      if (age() < REFRESH_INTERVAL_MS) return
      if (Date.now() - lastAttempt.current < REFRESH_INTERVAL_MS) return
      attempt()
    }
    // Coming back online is itself the news: whatever we last showed was fetched offline or
    // failed, so it is worth a check even if the clock says it is recent.
    const refreshNow = () => {
      if (document.visibilityState !== 'visible') return
      attempt()
    }
    const tick = () => {
      if (age() >= STALE_AFTER_MS) callbacks.current.markStale()
      refreshIfDue()
    }

    const timer = window.setInterval(tick, TICK_MS)
    document.addEventListener('visibilitychange', refreshIfDue)
    window.addEventListener('online', refreshNow)
    return () => {
      window.clearInterval(timer)
      document.removeEventListener('visibilitychange', refreshIfDue)
      window.removeEventListener('online', refreshNow)
    }
  }, [enabled, receivedAt])
}
