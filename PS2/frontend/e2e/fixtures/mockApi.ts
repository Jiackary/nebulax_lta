// Serves the frozen payloads to the app so a test exercises one named state and nothing else.
// Everything the page would otherwise fetch — the API, map tiles — is answered here, so no test
// depends on a running backend or on the network.
import type { Page, Route } from '@playwright/test'

import type { Alternatives, OfflineBundle, RouteStatus, TripPlan } from '../../src/api/types'
import { FIXTURE_TRIP_ID } from './payloads'
import { savedBundle } from './states'

export type ApiFailure = { status: number; code: string; message: string; retryable?: boolean }

export type MockApiOptions = {
  plan?: TripPlan | ApiFailure
  status?: RouteStatus | ApiFailure
  alternatives?: Alternatives | ApiFailure
  offline?: OfflineBundle | ApiFailure
  /** Hold every API response open, so the page stays in its loading state. */
  hang?: boolean
  /** Seed this bundle into IndexedDB before the app boots, as "Save written steps" would. */
  savedOffline?: OfflineBundle | null
  tripId?: string
}

function isFailure(value: unknown): value is ApiFailure {
  return typeof value === 'object' && value !== null && 'status' in value && 'code' in value
}

async function fulfil(route: Route, payload: unknown) {
  if (isFailure(payload)) {
    await route.fulfill({
      status: payload.status,
      contentType: 'application/json',
      body: JSON.stringify({
        error: { code: payload.code, message: payload.message, retryable: payload.retryable ?? payload.status >= 500 },
      }),
    })
    return
  }
  await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(payload) })
}

export async function mockApi(page: Page, options: MockApiOptions = {}) {
  const tripId = options.tripId ?? FIXTURE_TRIP_ID

  // Map tiles never leave the harness: a slow tile server must not look like a layout failure.
  await page.route('**://www.onemap.gov.sg/**', (route) => route.abort())

  // Matched on the pathname, not a glob: `**/api/**` also catches the dev server's own
  // `/src/api/*.ts` modules and answers them with JSON, which breaks the page before it boots.
  await page.route(
    (url) => url.pathname.startsWith('/api/'),
    async (route) => {
      if (options.hang) return
      const path = new URL(route.request().url()).pathname
      if (path.endsWith('/status')) return fulfil(route, options.status ?? { status: 503, code: 'UPSTREAM_UNAVAILABLE', message: 'Status is unavailable.' })
      if (path.endsWith('/alternatives')) return fulfil(route, options.alternatives ?? { status: 503, code: 'UPSTREAM_UNAVAILABLE', message: 'Alternatives are unavailable.' })
      if (path.endsWith('/offline')) return fulfil(route, options.offline ?? savedBundle)
      if (path.startsWith('/api/trips/')) return fulfil(route, options.plan ?? { status: 404, code: 'TRIP_NOT_FOUND', message: 'This journey is no longer available.' })
      await route.fulfill({ status: 200, contentType: 'application/json', body: '{}' })
    },
  )

  await page.addInitScript(
    ({ activeTripId, bundle }: { activeTripId: string; bundle: OfflineBundle | null }) => {
      window.localStorage.setItem('ps2.activeTripId', activeTripId)
      if (!bundle) return
      const request = window.indexedDB.open('ps2-journey', 1)
      request.onupgradeneeded = () => request.result.createObjectStore('offlineBundles', { keyPath: 'tripId' })
      request.onsuccess = () => {
        const db = request.result
        const store = db.transaction('offlineBundles', 'readwrite').objectStore('offlineBundles')
        store.put({ tripId: bundle.trip_id, savedAt: '2026-09-19T09:06:00+08:00', bundle })
      }
    },
    { activeTripId: tripId, bundle: options.savedOffline ?? null },
  )
}

export { FIXTURE_TRIP_ID }
