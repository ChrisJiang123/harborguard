import { writeFile } from 'node:fs/promises'

const service = 'https://rpgis.isd.lacounty.gov/arcgis/rest/services/GISNET_Public/MapServer/434/query'
const bbox = [-118.31, 33.70, -118.19, 33.765]
const params = new URLSearchParams({
  where: 'Shape.STArea() > 10000',
  geometry: bbox.join(','),
  geometryType: 'esriGeometryEnvelope',
  inSR: '4326',
  outSR: '4326',
  spatialRel: 'esriSpatialRelIntersects',
  outFields: 'OBJECTID,HEIGHT,ELEV,CODE,STATUS',
  returnGeometry: 'true',
  f: 'geojson',
})
const response = await fetch(`${service}?${params}`, { headers: { 'User-Agent': 'HarborGuard local harbor model preparation', Accept: 'application/geo+json, application/json' }, signal: AbortSignal.timeout(45000) })
if (!response.ok) throw new Error(`LA County building query HTTP ${response.status}`)
const result = await response.json()
if (!Array.isArray(result.features) || !result.features.length) throw new Error('LA County building query returned no footprints; existing data was not overwritten.')

const features = result.features.flatMap(feature => {
  const id = feature.properties?.OBJECTID
  const heightFeet = Number(feature.properties?.HEIGHT)
  const rings = feature.geometry?.type === 'Polygon' ? feature.geometry.coordinates : null
  if (!Number.isInteger(id) || !Number.isFinite(heightFeet) || heightFeet <= 0 || !Array.isArray(rings) || !rings.length) return []
  return [{
    type: 'Feature',
    properties: { id: `lacounty-building/${id}`, kind: 'building', name: '', height_m: heightFeet * (1200 / 3937), height_ft: heightFeet, roof_elev_ft: Number.isFinite(Number(feature.properties.ELEV)) ? Number(feature.properties.ELEV) : undefined, height_source: 'la-county-lariac-height', update_status: feature.properties.STATUS ?? 'unknown' },
    geometry: { type: 'Polygon', coordinates: rings },
  }]
})
if (!features.length) throw new Error('No valid building outlines or heights found; existing data was not overwritten.')

const dataset = {
  type: 'FeatureCollection',
  source: 'Los Angeles County GISNET Public, Building Outline 2023 (LARIAC5 imagery)',
  source_url: service,
  source_image_dates: '2017 LARIAC5 acquisition; published layer is Countywide Building Outline (2023)',
  license: 'County of Los Angeles eGIS custom terms; attribution required; see public/data/LA-COUNTY-BUILDINGS.md',
  retrieved_at: new Date().toISOString(),
  horizontal_crs: 'EPSG:4326',
  source_height_unit: 'US survey feet as reported by the Los Angeles County service spatial reference',
  height_conversion: 'height_m = HEIGHT × (1200/3937); EPSG:2229 US survey feet to meters',
  extent_wgs84: bbox,
  selection: 'Building footprint area > 10,000 square feet intersecting the HarborGuard DEM extent',
  features,
}
await writeFile(new URL('../public/data/lacounty-port-buildings.geojson', import.meta.url), JSON.stringify(dataset))
console.log(`Saved ${features.length} Los Angeles County building footprints with measured height attributes.`)
