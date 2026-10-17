import type { FeatureCollection, Geometry } from 'geojson'

export type LocalBaseProperties = { id: string; kind: string; name: string; building_type?: string; height_m?: number; height_ft?: number; roof_elev_ft?: number; height_source?: 'osm' | 'levels-estimate' | 'default-estimate' | 'la-county-lariac-height'; update_status?: string }
export type LocalBase = FeatureCollection<Geometry, LocalBaseProperties>
export function parseLocalBase(value: unknown): LocalBase {
  const data = value as LocalBase | null
  const validPoint = (point: number[]) => Number.isFinite(point[0]) && Number.isFinite(point[1]) && Math.abs(point[0]!) <= 180 && Math.abs(point[1]!) <= 90
  const validGeometry = (geometry: Geometry | null | undefined) => {
    if (!geometry) return false
    if (geometry.type === 'Point') return validPoint(geometry.coordinates)
    if (geometry.type === 'LineString') return geometry.coordinates.length > 1 && geometry.coordinates.every(validPoint)
    if (geometry.type === 'Polygon') return geometry.coordinates.length > 0 && geometry.coordinates.every(ring => ring.length >= 4 && ring.every(validPoint) && ring[0]![0] === ring.at(-1)![0] && ring[0]![1] === ring.at(-1)![1])
    return false
  }
  if (data?.type !== 'FeatureCollection' || !Array.isArray(data.features) || !data.features.length || !data.features.every(feature => feature.type === 'Feature' && typeof feature.properties?.id === 'string' && typeof feature.properties.kind === 'string' && validGeometry(feature.geometry))) throw new Error('本地 OSM 港区要素文件无效。')
  return data
}
let cached: Promise<LocalBase> | null = null
export function loadLocalBase() {
  cached ??= fetch('/data/harbor-osm.geojson', { signal: AbortSignal.timeout(8000) }).then(async response => {
    if (!response.ok) throw new Error('本地港区 OSM 数据尚未提供。')
    return parseLocalBase(await response.json())
  })
  return cached
}

let buildingsCached: Promise<LocalBase> | null = null
export function loadPortBuildings() {
  buildingsCached ??= fetch('/data/lacounty-port-buildings.geojson', { signal: AbortSignal.timeout(12000) }).then(async response => {
    if (!response.ok) throw new Error('洛杉矶县港区建筑轮廓尚未提供。')
    return parseLocalBase(await response.json())
  })
  return buildingsCached
}
