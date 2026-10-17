import type { FeatureCollection, LineString } from 'geojson'

export type LocalBase = FeatureCollection<LineString, { id: string; kind: string; name: string }>
export function parseLocalBase(value: unknown): LocalBase {
  const data = value as LocalBase | null
  if (data?.type !== 'FeatureCollection' || !Array.isArray(data.features) || !data.features.length || !data.features.every(feature => feature.type === 'Feature' && typeof feature.properties?.id === 'string' && feature.geometry?.type === 'LineString' && feature.geometry.coordinates.length > 1 && feature.geometry.coordinates.every(p => Number.isFinite(p[0]) && Number.isFinite(p[1]) && Math.abs(p[0]!) <= 180 && Math.abs(p[1]!) <= 90))) throw new Error('本地 OSM 岸线文件无效。')
  return data
}
let cached: Promise<LocalBase> | null = null
export function loadLocalBase() {
  cached ??= fetch('/data/harbor-osm.geojson', { signal: AbortSignal.timeout(8000) }).then(async response => {
    if (!response.ok) throw new Error('本地岸线尚未提供。')
    return parseLocalBase(await response.json())
  })
  return cached
}
