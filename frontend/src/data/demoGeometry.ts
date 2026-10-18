import type { Asset } from '../types/contract'
import type { StaticBuoy, ZoneCollection } from './mapGeometry'
import { PROPOSED_SONARS } from './sonarDeployment'

export const DEMO_ASSETS: Asset[] = [
  { id: 'asset-1', name: 'Demo Container Terminal', kind: 'berth', lat: 33.736, lon: -118.252, sensitivity: 0.9, rings_m: [1500, 800, 400] },
]
export const DEMO_BUOYS: StaticBuoy[] = PROPOSED_SONARS.map(({ id, lat, lon, range_m }) => ({ id, lat, lon, range_m }))
// Example partitions only. These rectangles are not OSM or official port security boundaries.
export const DEMO_ZONES: ZoneCollection = {
  type: 'FeatureCollection',
  features: Array.from({ length: 10 }, (_, i) => {
    const column = i % 5
    const row = Math.floor(i / 5)
    const west = -118.278 + column * 0.0064
    const south = 33.722 + row * 0.0075
    const east = west + 0.0062
    const north = south + 0.0073
    return {
      type: 'Feature',
      properties: { id: `Z${i + 1}`, name: `Demo ${row === 0 ? 'Channel' : 'Berth'} ${i + 1}`, kind: row === 0 ? 'channel' : 'berth', sensitivity: 0.5, berths: row === 0 ? 0 : 2, neighbors: [], entrance: i === 0 },
      geometry: { type: 'Polygon', coordinates: [[[west, south], [east, south], [east, north], [west, north], [west, south]]] },
    }
  }),
}
