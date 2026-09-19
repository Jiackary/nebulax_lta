import 'fake-indexeddb/auto'
import { afterEach, describe, expect, it } from 'vitest'

import { clearOfflineBundle, readOfflineBundle, saveOfflineBundle } from './storage'

const bundle = {
  trip_id: 'trip-offline', generated_at: '2026-10-20T09:00:00+08:00', plan: { appointment_at: '2026-10-20T11:00:00+08:00' },
  status_snapshot: null, warnings: ['Check before travelling.'], steps_plain: ['Check before travelling.', 'Walk to the station.'], offline_notice: 'No signal.', attribution: [], tiles: { style_url: null, tile_pack_url: null, attribution: 'OSM', zoom_range: [13, 17], unavailable_reason: 'No tiles.' },
}

describe('offline bundle storage', () => {
  afterEach(async () => {
    await clearOfflineBundle('trip-offline')
  })

  it('returns the explicitly saved written bundle', async () => {
    await saveOfflineBundle(bundle as never)

    await expect(readOfflineBundle('trip-offline')).resolves.toMatchObject({ bundle, tripId: 'trip-offline' })
  })
})
