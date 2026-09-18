const ACTIVE_TRIP_KEY = 'ps2.activeTripId'

export function getActiveTripId() {
  return localStorage.getItem(ACTIVE_TRIP_KEY)
}

export function setActiveTripId(tripId: string) {
  localStorage.setItem(ACTIVE_TRIP_KEY, tripId)
}

export function clearActiveTripId() {
  localStorage.removeItem(ACTIVE_TRIP_KEY)
}
