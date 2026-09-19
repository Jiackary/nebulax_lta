import { useEffect, useRef, useState } from 'react'
import { Map as MapLibreMap, Marker, NavigationControl, setWorkerUrl, type GeoJSONSource, type LngLatBoundsLike, type LngLatLike, type StyleSpecification } from 'maplibre-gl'
import maplibreWorkerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url'
import 'maplibre-gl/dist/maplibre-gl.css'

import type { LegImpact } from './legImpact'

// Singapore Land Authority's own basemap. Free for Singapore coverage and already the
// source behind the walking directions, so no second provider and no API key.
const ONEMAP_TILES = 'https://www.onemap.gov.sg/maps/tiles/Grey/{z}/{x}/{y}.png'
const ONEMAP_ATTRIBUTION = '<a href="https://www.onemap.gov.sg/" target="_blank" rel="noreferrer">OneMap</a> &copy; contributors | <a href="https://www.sla.gov.sg/" target="_blank" rel="noreferrer">Singapore Land Authority</a>'

// OneMap publishes tiles for Singapore only; panning past this just wastes requests.
const SINGAPORE_BOUNDS: LngLatBoundsLike = [[103.596, 1.1443], [104.1, 1.4835]]

// MapLibre resolves its worker with new URL('./maplibre-gl-worker.mjs', import.meta.url),
// which no bundler can follow, so the file is never emitted and the worker 404s. ?worker&url
// makes Vite bundle it as a worker entry, which also pulls in the maplibre-gl-shared chunk
// the worker imports relatively — plain ?url copies the file alone and its sibling import
// falls through to the SPA handler, which answers a JavaScript request with index.html.
// Every GeoJSON source is parsed in that worker, so without this the route silently never
// draws: the basemap still tiles and the markers still mount, so it looks like it works.
setWorkerUrl(maplibreWorkerUrl)

const COLOUR = { none: '#0d6048', warn: '#b26a00', critical: '#b3261e' } as const

type RouteFeature = {
  type: 'Feature'
  properties: { leg_id: string; mode: string } & Record<string, unknown>
  geometry: { type: 'LineString'; coordinates: number[][] }
}

export type RouteGeometry = { type: 'FeatureCollection'; features: RouteFeature[] }

// MapLibre takes ownership of the style object it is handed and mutates it while loading.
// Sharing one across instances leaves the second map with a style that never finishes
// loading, so its line layers never paint. Build a fresh one every time.
function createStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {
      onemap: { type: 'raster', tiles: [ONEMAP_TILES], tileSize: 256, maxzoom: 18, attribution: ONEMAP_ATTRIBUTION },
    },
    layers: [{ id: 'basemap', type: 'raster', source: 'onemap' }],
  }
}

function decorate(geometry: RouteGeometry, impacts: Map<string, LegImpact>) {
  return {
    ...geometry,
    features: geometry.features.map((feature) => {
      const impact = impacts.get(feature.properties.leg_id)
      return { ...feature, properties: { ...feature.properties, level: impact?.level ?? 'none', reason: impact?.reason ?? '' } }
    }),
  }
}

export function RouteMap({ geometry, bbox, impacts, label }: {
  geometry: RouteGeometry
  bbox: [number, number, number, number]
  impacts: Map<string, LegImpact>
  label: string
}) {
  const container = useRef<HTMLDivElement>(null)
  const map = useRef<MapLibreMap | null>(null)
  const [failed, setFailed] = useState(false)
  // Read through a ref so a status refresh redraws the route instead of rebuilding the map.
  // Seeded from the first render, which is what the map is built from, then kept in step.
  const latest = useRef({ geometry, impacts, bbox })
  useEffect(() => {
    latest.current = { geometry, impacts, bbox }
  }, [geometry, impacts, bbox])

  useEffect(() => {
    if (!container.current) return
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const instance = new MapLibreMap({
      container: container.current,
      style: createStyle(),
      bounds: latest.current.bbox,
      fitBoundsOptions: { padding: 28 },
      maxBounds: SINGAPORE_BOUNDS,
      attributionControl: { compact: true },
      // The written steps below are the accessible route of record; the map is a second
      // view of the same thing, so it does not trap keyboard users in a pan surface.
      keyboard: false,
      dragRotate: false,
      pitchWithRotate: false,
      fadeDuration: reduceMotion ? 0 : 300,
    })
    instance.touchZoomRotate.disableRotation()
    instance.addControl(new NavigationControl({ showCompass: false }), 'top-right')
    // Tile hiccups are routine and recoverable; only a style failure means no map at all.
    instance.on('error', (event) => {
      if ((event as { sourceId?: string }).sourceId) return
      setFailed(true)
    })

    instance.on('load', () => {
      const { geometry: data, impacts: levels } = latest.current
      instance.addSource('route', { type: 'geojson', data: decorate(data, levels) })
      // A white casing keeps the route legible over the basemap's own coloured rail lines.
      instance.addLayer({
        id: 'route-casing', type: 'line', source: 'route',
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': '#ffffff', 'line-width': 10 },
      })
      instance.addLayer({
        id: 'route-unaffected', type: 'line', source: 'route', filter: ['==', ['get', 'level'], 'none'],
        layout: { 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': COLOUR.none, 'line-width': 5 },
      })
      // Affected legs are dashed as well as coloured: D14 asks for pattern and label, and
      // colour alone fails anyone who cannot separate green from amber.
      instance.addLayer({
        id: 'route-affected', type: 'line', source: 'route', filter: ['!=', ['get', 'level'], 'none'],
        layout: { 'line-cap': 'butt', 'line-join': 'round' },
        paint: {
          'line-color': ['match', ['get', 'level'], 'critical', COLOUR.critical, COLOUR.warn],
          'line-width': 6,
          'line-dasharray': [2, 1.5],
        },
      })

      const coordinates = data.features.flatMap((feature) => feature.geometry.coordinates)
      const start = coordinates[0]
      const end = coordinates[coordinates.length - 1]
      if (start) new Marker({ color: COLOUR.none }).setLngLat(start as LngLatLike).addTo(instance)
      if (end) new Marker({ color: '#12271f' }).setLngLat(end as LngLatLike).addTo(instance)
    })

    map.current = instance
    return () => {
      instance.remove()
      map.current = null
    }
  }, [])

  // Keep the drawn route in step with status refreshes without tearing the map down.
  useEffect(() => {
    const source = map.current?.getSource('route') as GeoJSONSource | undefined
    source?.setData(decorate(geometry, impacts))
  }, [geometry, impacts])

  if (failed) {
    return (
      <section className="route-map route-map-unavailable">
        <strong>The map could not be loaded.</strong>
        <span>Your written steps below are complete and do not need the map.</span>
      </section>
    )
  }

  // The legend has to describe what is actually drawn, so it follows the worst impact
  // present rather than assuming a colour.
  const levels = [...impacts.values()]
  const worst = levels.some((impact) => impact.level === 'critical') ? 'critical'
    : levels.some((impact) => impact.level === 'warn') ? 'warn' : 'none'
  const reasons = [...new Set(levels.map((impact) => impact.reason).filter(Boolean))]

  return (
    <section className="route-map">
      <div className="route-map-canvas" ref={container} role="img" aria-label={label} />
      <ul className="route-map-legend">
        <li><span className="route-key route-key-clear" aria-hidden="true" />On your usual route</li>
        {worst === 'none'
          ? <li className="route-map-clear">Nothing is affecting this route.</li>
          : <li><span className={`route-key route-key-${worst}`} aria-hidden="true" />{reasons[0] ?? 'Affected section'}</li>}
      </ul>
    </section>
  )
}
