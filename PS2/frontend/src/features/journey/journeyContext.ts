import { createContext } from 'react'

import type { OfflineBundle } from '../../api/types'
import type { JourneyState } from './journeyCoordinator'

export type JourneyContextValue = JourneyState & {
  refresh: () => Promise<void>
  prepareOffline: () => Promise<OfflineBundle>
}

export const JourneyContext = createContext<JourneyContextValue | null>(null)
