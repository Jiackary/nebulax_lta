import { useContext } from 'react'

import { JourneyContext } from './journeyContext'

export function useJourney() {
  const value = useContext(JourneyContext)
  if (!value) throw new Error('useJourney must be used within JourneyProvider')
  return value
}
