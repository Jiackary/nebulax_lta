import { openDB, type IDBPDatabase } from 'idb'

import type { OfflineBundle } from '../../api/types'

export type SavedOfflineBundle = { tripId: string; savedAt: string; bundle: OfflineBundle }

let database: Promise<IDBPDatabase> | null = null

function getDatabase() {
  if (!('indexedDB' in globalThis)) throw new Error('Offline storage is not supported in this browser.')
  database ??= openDB('ps2-journey', 1, {
    upgrade(db) {
      db.createObjectStore('offlineBundles', { keyPath: 'tripId' })
    },
  })
  return database
}

export async function saveOfflineBundle(bundle: OfflineBundle) {
  const saved: SavedOfflineBundle = { tripId: bundle.trip_id, savedAt: new Date().toISOString(), bundle }
  await (await getDatabase()).put('offlineBundles', saved)
  return saved
}

export async function readOfflineBundle(tripId: string) {
  return (await getDatabase()).get('offlineBundles', tripId) as Promise<SavedOfflineBundle | undefined>
}

export async function clearOfflineBundle(tripId: string) {
  await (await getDatabase()).delete('offlineBundles', tripId)
}
