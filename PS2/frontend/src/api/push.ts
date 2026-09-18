import { requestJson } from './client'
import type { PushKey } from './types'

type BrowserSubscription = { endpoint: string; keys: Record<string, string> }

export function getPushKey() {
  return requestJson<PushKey>('/api/push/key')
}

export function savePushSubscription(subscription: BrowserSubscription, tripId: string) {
  return requestJson<{ subscribed: boolean; checks: string[] }>('/api/push/subscribe', {
    method: 'POST',
    body: { subscription, trip_ids: [tripId] },
  })
}

export function unsubscribePush(endpoint: string) {
  return requestJson<{ unsubscribed: boolean; note: string }>('/api/push/subscribe', { method: 'DELETE', query: { endpoint } })
}
