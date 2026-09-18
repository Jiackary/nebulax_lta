import { requestJson } from './client'
import type { Alternatives, OfflineBundle, RouteStatus, TripPlan, TripRequest } from './types'

export function createTrip(request: TripRequest) {
  return requestJson<TripPlan>('/api/trips', { method: 'POST', body: request })
}

export function getTrip(tripId: string) {
  return requestJson<TripPlan>(`/api/trips/${encodeURIComponent(tripId)}`)
}

export function getStatus(tripId: string) {
  return requestJson<RouteStatus>(`/api/trips/${encodeURIComponent(tripId)}/status`)
}

export function getAlternatives(tripId: string) {
  return requestJson<Alternatives>(`/api/trips/${encodeURIComponent(tripId)}/alternatives`)
}

export function getOfflineBundle(tripId: string) {
  return requestJson<OfflineBundle>(`/api/trips/${encodeURIComponent(tripId)}/offline`)
}

export function deleteTrip(tripId: string) {
  return requestJson<{ deleted: boolean; note: string }>(`/api/trips/${encodeURIComponent(tripId)}`, { method: 'DELETE' })
}
