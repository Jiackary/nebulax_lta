import { createContext } from 'react'

import type { JourneyState } from './journeyCoordinator'

export type JourneyContextValue = JourneyState & { refresh: () => Promise<void> }

export const JourneyContext = createContext<JourneyContextValue | null>(null)
