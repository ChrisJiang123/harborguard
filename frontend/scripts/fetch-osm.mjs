import { writeFile } from 'node:fs/promises'

// One bounded vector-data query. Never fetch/prefetch tiles from tile.openstreetmap.org.
const bbox = [33.705, -118.29, 33.765, -118.215]
const query = `[out:json][timeout:25];(way["natural"="coastline"](${bbox});way["man_made"~"^(pier|breakwater)$"](${bbox});way["highway"~"^(motorway|trunk|primary)$"](${bbox}););out body geom(${bbox});`
const response = await fetch(`https://overpass-api.de/api/interpreter?data=${encodeURIComponent(query)}`, { signal: AbortSignal.timeout(40000), headers: { 'User-Agent': 'HarborGuard-local-demo/1.0 (bounded port coastline extract)' } })
if (!response.ok) throw new Error(`OSM extract HTTP ${response.status}`)
const result = await response.json()
if (result.remark) throw new Error(result.remark)
const features = []
for (const way of result.elements ?? []) {
  let segment = [], part = 0
  const flush = () => {
    if (segment.length > 1) features.push({ type: 'Feature', properties: { id: `way/${way.id}/${part++}`, osm_id: way.id, kind: way.tags?.natural === 'coastline' ? 'coastline' : way.tags?.man_made ?? 'road', name: way.tags?.name ?? '' }, geometry: { type: 'LineString', coordinates: segment } })
    segment = []
  }
  for (const point of way.geometry ?? []) {
    if (point && Number.isFinite(point.lat) && Number.isFinite(point.lon)) segment.push([point.lon, point.lat])
    else flush()
  }
  flush()
}
if (!features.some(feature => feature.properties.kind === 'coastline')) throw new Error('No coastline returned; existing data was not overwritten.')
const collection = { type: 'FeatureCollection', source: 'OpenStreetMap contributors / Overpass API', license: 'ODbL 1.0 — https://www.openstreetmap.org/copyright', retrieved_at: new Date().toISOString(), osm_base: result.osm3s?.timestamp_osm_base, bbox: [bbox[1], bbox[0], bbox[3], bbox[2]], query, features }
await writeFile(new URL('../public/data/harbor-osm.geojson', import.meta.url), JSON.stringify(collection))
console.log(`Saved ${features.length} local OSM line features; no raster tiles requested.`)
