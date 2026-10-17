import type { Feature, FeatureCollection, MultiPolygon, Polygon } from 'geojson'
import type { Asset, Buoy, ZoneState } from '../types/contract'

// Geometry metadata belongs to B's documented static files, not the WebSocket contract.
export interface ZoneProperties {
  id: string; name: string; kind: string; sensitivity: number; berths: number
  neighbors: string[]; entrance: boolean; state?: ZoneState; coverage?: number
}
export type ZoneFeature = Feature<Polygon | MultiPolygon, ZoneProperties>
export type ZoneCollection = FeatureCollection<Polygon | MultiPolygon, ZoneProperties>
export type StaticBuoy = Pick<Buoy, 'id' | 'lat' | 'lon' | 'range_m'>
export type GeometrySource = 'api' | 'file' | 'demo'
export interface MapResources {
  zones: ZoneCollection; assets: Asset[]; buoys: StaticBuoy[]
  sources: { zones: GeometrySource; assets: GeometrySource; buoys: GeometrySource }
}

const object = (value: unknown): Record<string, unknown> | null => typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null
const validLatLon = (lat: unknown, lon: unknown) => typeof lat === 'number' && Number.isFinite(lat) && Math.abs(lat) <= 90 && typeof lon === 'number' && Number.isFinite(lon) && Math.abs(lon) <= 180
const uniqueIds = (items: { id: string }[]) => new Set(items.map(item => item.id)).size === items.length

function validRing(value: unknown): boolean {
  if (!Array.isArray(value) || value.length < 4) return false
  if (!value.every(point => Array.isArray(point) && validLatLon(point[1], point[0]))) return false
  const first = value[0] as number[]
  const last = value[value.length - 1] as number[]
  return first[0] === last[0] && first[1] === last[1]
}
function validPolygon(value: unknown): boolean { return Array.isArray(value) && value.length > 0 && value.every(validRing) }

export function parseZones(value: unknown): ZoneCollection | null {
  const collection = object(value)
  if (collection?.type !== 'FeatureCollection' || !Array.isArray(collection.features) || !collection.features.length) return null
  const features = collection.features
  const valid = features.every(item => {
    const feature = object(item)
    const properties = object(feature?.properties)
    const geometry = object(feature?.geometry)
    return feature?.type === 'Feature' && typeof properties?.id === 'string' && properties.id.length > 0 && typeof properties.name === 'string' && typeof properties.kind === 'string' && geometry && (
      geometry.type === 'Polygon' ? validPolygon(geometry.coordinates) : geometry.type === 'MultiPolygon' && Array.isArray(geometry.coordinates) && geometry.coordinates.length > 0 && geometry.coordinates.every(validPolygon)
    )
  })
  if (!valid || !uniqueIds(features.map(item => (item as ZoneFeature).properties))) return null
  return value as ZoneCollection
}

export function parseAssets(value: unknown): Asset[] | null {
  if (!Array.isArray(value) || !value.length) return null
  const valid = value.every(item => {
    const asset = object(item)
    return asset && typeof asset.id === 'string' && asset.id.length > 0 && typeof asset.name === 'string' && validLatLon(asset.lat, asset.lon) && Array.isArray(asset.rings_m) && asset.rings_m.length === 3 && asset.rings_m.every(radius => typeof radius === 'number' && Number.isFinite(radius) && radius > 0)
  })
  return valid && uniqueIds(value as Asset[]) ? value as Asset[] : null
}

export function parseBuoys(value: unknown): StaticBuoy[] | null {
  if (!Array.isArray(value) || !value.length) return null
  const valid = value.every(item => {
    const buoy = object(item)
    return buoy && typeof buoy.id === 'string' && buoy.id.length > 0 && validLatLon(buoy.lat, buoy.lon) && typeof buoy.range_m === 'number' && Number.isFinite(buoy.range_m) && buoy.range_m > 0
  })
  return valid && uniqueIds(value as StaticBuoy[]) ? value as StaticBuoy[] : null
}

/** GeoJSON is [lon,lat]; Leaflet is [lat,lon]. Preserve polygons, islands and holes. */
export function polygonPositions(geometry: Polygon | MultiPolygon): [number, number][][][] {
  const polygons = geometry.type === 'Polygon' ? [geometry.coordinates] : geometry.coordinates
  return polygons.map(polygon => polygon.map(ring => ring.map(point => [point[1]!, point[0]!])))
}
