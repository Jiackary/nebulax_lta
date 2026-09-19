import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'

import { getOfflineBundle, getStatus, getTrip } from '../../api/trips'
import { readOfflineBundle } from '../offline/storage'
import { JourneyCoordinator, type JourneyState } from './journeyCoordinator'
import { JourneyContext } from './journeyContext'

export function JourneyProvider({ children, tripId }: { children: ReactNode; tripId: string }) {
  const [state, setState] = useState<JourneyState>({ phase: 'loading', operation: 'loading-plan', snapshot: null, message: null })
  const coordinatorRef = useRef<JourneyCoordinator | null>(null)

  useEffect(() => {
    const current = new JourneyCoordinator({ getPlan: getTrip, getStatus, getOfflineBundle })
    coordinatorRef.current = current
    const unsubscribe = current.subscribe(setState)
    void current.initialize(tripId).then(async () => {
      if (current.state.snapshot) {
        await current.refresh()
        return
      }
      const saved = await readOfflineBundle(tripId).catch(() => undefined)
      if (!saved) return
      const plan = { ...saved.bundle.plan, trip_id: tripId }
      current.hydrateSaved(tripId, plan, saved.bundle.status_snapshot ?? null, {
        generatedAt: saved.bundle.generated_at,
        savedAt: saved.savedAt,
        warnings: saved.bundle.warnings,
      })
    })
    return () => {
      unsubscribe()
      current.dispose()
      if (coordinatorRef.current === current) coordinatorRef.current = null
    }
  }, [tripId])

  const refresh = useCallback(() => coordinatorRef.current?.refresh() ?? Promise.resolve(), [])
  const prepareOffline = useCallback(() => {
    if (!coordinatorRef.current) return Promise.reject(new Error('This journey is no longer available.'))
    return coordinatorRef.current.prepareOffline()
  }, [])
  const value = useMemo(() => ({ ...state, refresh, prepareOffline }), [prepareOffline, refresh, state])
  return <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>
}
