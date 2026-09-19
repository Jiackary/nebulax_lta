import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { RouteMapPanel } from './RouteMapPanel'

const legs = [
  { leg_id: 'l1', mode: 'walk' as const, from: { name: 'Home' }, to: { name: 'Bedok', station_code: 'EW5' } },
  { leg_id: 'l2', mode: 'rail' as const, from: { name: 'Bedok', station_code: 'EW5' }, to: { name: 'Outram Park', station_code: 'EW16' }, line: { code: 'EWL' } },
]

// MapLibre needs a WebGL context that jsdom cannot provide, so these cover the guard that
// runs before the map chunk is ever imported. The map itself is checked against a real
// browser build instead.
describe('RouteMapPanel', () => {
  it('falls back to the written steps when the plan carries no geometry', () => {
    render(<RouteMapPanel legs={legs} map={null} status={null} />)

    expect(screen.getByText(/route map is not available/i)).toBeVisible()
    expect(screen.getByText(/written steps below are complete/i)).toBeVisible()
  })

  it('does not reach for the map chunk at all on a journey restored from offline storage', () => {
    const geometry = {
      type: 'FeatureCollection' as const,
      features: [{ type: 'Feature' as const, properties: { leg_id: 'l1', mode: 'walk' }, geometry: { type: 'LineString' as const, coordinates: [[103.9, 1.3], [103.91, 1.31]] } }],
    }

    render(<RouteMapPanel legs={legs} map={{ bbox: [103.9, 1.3, 103.91, 1.31], geometry }} status={null} offline />)

    // The chunk is not precached, so offline the dynamic import rejects. Nothing catches
    // that above this component, so reaching for it blanks the whole page — including the
    // written steps she saved for exactly this moment.
    expect(screen.getByText(/map is not available offline/i)).toBeVisible()
    expect(screen.getByText(/written steps below are complete/i)).toBeVisible()
  })

  it('falls back when the bounding box is malformed rather than rendering a broken map', () => {
    const geometry = {
      type: 'FeatureCollection' as const,
      features: [{ type: 'Feature' as const, properties: { leg_id: 'l1', mode: 'walk' }, geometry: { type: 'LineString' as const, coordinates: [[103.9, 1.3], [103.91, 1.31]] } }],
    }

    render(<RouteMapPanel legs={legs} map={{ bbox: [103.9, 1.3], geometry }} status={null} />)

    expect(screen.getByText(/route map is not available/i)).toBeVisible()
  })
})
