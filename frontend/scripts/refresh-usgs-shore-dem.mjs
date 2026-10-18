import { readFile, writeFile } from 'node:fs/promises'
import { fromArrayBuffer } from 'geotiff'

const bounds = { west: -118.31, south: 33.70, east: -118.19, north: 33.765 }
// ~4.8 m display sampling in both axes. F32 elevations, never 8-bit heights.
const width = 2304
const height = 1500
const noData = -9999
function exportUrl(serviceUrl, parameters) {
  const url = new URL(serviceUrl)
  url.search = new URLSearchParams(parameters).toString()
  return url
}
const demUrl = exportUrl('https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage', {
  bbox: `${bounds.west},${bounds.south},${bounds.east},${bounds.north}`,
  bboxSR: '4326', imageSR: '4326', size: `${width},${height}`,
  adjustAspectRatio: 'false',
  format: 'tiff', pixelType: 'F32', interpolation: 'RSP_Bilinear', f: 'image',
})
// Keep the independently georeferenced bundled orthophoto. Refreshing the DEM
// must not depend on the imagery service (which can time out independently).
const previous = JSON.parse(await readFile(new URL('../public/data/shore-dem-usgs-3dep.json', import.meta.url), 'utf8'))
let imageryBounds = previous.metadata.imagery_bounds
if (!imageryBounds && previous.metadata.imagery_export_url) {
  const [west,south,east,north] = new URL(previous.metadata.imagery_export_url).searchParams.get('bbox').split(',').map(Number)
  imageryBounds = { west,south,east,north }
}
if (!imageryBounds) throw new Error('Existing imagery has no traceable bbox; refresh imagery separately before exporting the DEM')
const imageryBytes = await readFile(new URL('../public/data/shore-ortho-usgs-naip.png', import.meta.url))
if (imageryBytes.readUInt32BE(16) !== 3072 || imageryBytes.readUInt32BE(20) !== 1668) throw new Error('Unexpected orthophoto dimensions')
const response = await fetch(demUrl, { signal: AbortSignal.timeout(60000) })
if (!response.ok) throw new Error(`USGS 3DEP export failed: HTTP ${response.status}`)
// Land/water classification must use the regional topobathy mask, not MBES
// coverage: an unsurveyed water cell is not land. Generate this file first.
const bathymetry = JSON.parse(await readFile(new URL('../public/data/seabed-fill-regional.json', import.meta.url), 'utf8'))
const tiff = await fromArrayBuffer(await response.arrayBuffer())
const image = await tiff.getImage()
if (image.getWidth() !== width || image.getHeight() !== height || image.getGeoKeys().GeographicTypeGeoKey !== 4326) {
  throw new Error('USGS export dimensions or CRS do not match requested EPSG:4326 grid')
}
const rasterBounds = image.getBoundingBox()
const cropBounds = { west: rasterBounds[0], south: rasterBounds[1], east: rasterBounds[2], north: rasterBounds[3] }
if (Object.keys(bounds).some(key => Math.abs(cropBounds[key] - bounds[key]) > 1e-8)) throw new Error('USGS silently adjusted the crop; refusing misregistered DEM/imagery')
// TIFF bbox denotes outer pixel edges; the scene grid denotes sample centres.
const pixelX=(cropBounds.east-cropBounds.west)/width, pixelY=(cropBounds.north-cropBounds.south)/height
const actualBounds = { west: cropBounds.west+pixelX/2, east: cropBounds.east-pixelX/2, south: cropBounds.south+pixelY/2, north: cropBounds.north-pixelY/2 }
const spacing = { east_west: 111320 * Math.cos(33.73 * Math.PI / 180) * (actualBounds.east - actualBounds.west) / (width - 1), north_south: 111132 * (actualBounds.north - actualBounds.south) / (height - 1) }
if (spacing.east_west > 5 || spacing.north_south > 5) throw new Error('Returned DEM exceeds the 5 m display sampling limit')
const raster = await image.readRasters({ interleave: true })
const water = bathymetry.values
const bathyMeta = bathymetry.metadata
const values = Array.from({ length: width * height }, (_, index) => {
  const row = Math.floor(index / width)
  const column = index % width
  const lon = actualBounds.west + column / (width - 1) * (actualBounds.east - actualBounds.west)
  const lat = actualBounds.north - row / (height - 1) * (actualBounds.north - actualBounds.south)
  const bathyColumn = Math.round((lon - bathyMeta.bounds.west) / (bathyMeta.bounds.east - bathyMeta.bounds.west) * (bathyMeta.width - 1))
  const bathyRow = Math.round((bathyMeta.bounds.north - lat) / (bathyMeta.bounds.north - bathyMeta.bounds.south) * (bathyMeta.height - 1))
  const bathyValue = water[bathyRow * bathyMeta.width + bathyColumn]
  const elevation = raster[index]
  // Keep only valid USGS elevations on the land side of the regional topo-bathy shoreline mask.
  if (bathyValue !== bathyMeta.nodata_value || !Number.isFinite(elevation) || elevation < -100 || elevation > 9000) return noData
  // Millimetre decimal serialization of the Float32 DEM (not source accuracy).
  return Math.round(Math.fround(elevation) * 1000) / 1000
})
const valid = values.filter(value => value !== noData)
if (valid.length < 1000) throw new Error(`Only ${valid.length} valid land DEM samples; refusing to replace snapshot`)
const output = {
  version: 1,
  metadata: {
    title: 'USGS 3DEP bare-earth elevation — Los Angeles Harbor coastal crop',
    source_kind: 'lidar_dem',
    source: 'USGS 3DEP Elevation ImageServer (regional multi-resolution DEM; NOAA regional topo-bathy land mask)',
    source_url: 'https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer',
    acquisition_note: 'USGS 3DEP source mosaics are multi-resolution; this 2304×1500 EPSG:4326 display crop is resampled (~4.8 m), not a claim of native 5 m source accuracy.',
    imagery_source: 'USGS National Map NAIP Imagery ImageServer; imagery is an orthophoto mosaic, not live video.',
    imagery_url: 'https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer',
    imagery_date_note: 'Image service copyright date: January 09, 2025; underlying acquisition dates vary by location.',
    imagery_file: 'shore-ortho-usgs-naip.png',
    imagery_bounds: imageryBounds,
    imagery_export_url: previous.metadata.imagery_export_url,
    imagery_retrieved_at: previous.metadata.imagery_retrieved_at,
    grid_registration: 'pixel_centres',
    imagery_grid: '3072×1668 RGB orthophoto with independent imagery_bounds, geographically draped over the land-only mesh using pixel-centre coordinates. Display pixels are not a claim of source ground accuracy.',
    horizontal_crs: 'EPSG:4326', horizontal_units: 'degrees',
    vertical_datum: 'NAVD88', vertical_units: 'm', elevation_positive: 'up',
    vertical_alignment: 'NAVD88 values displayed with zero offset against the MLLW display water reference; datum transformation has not been applied. Regional fill also retains its source datum.',
    width, height, bounds: actualBounds, nodata_value: noData,
    min_elevation_m: valid.reduce((a, b) => Math.min(a, b), Infinity), max_elevation_m: valid.reduce((a, b) => Math.max(a, b), -Infinity),
    nodata_cells: values.length - valid.length,
    spacing_m_approx: spacing,
  },
  values,
}
await writeFile(new URL('../public/data/shore-dem-usgs-3dep.json', import.meta.url), `${JSON.stringify(output)}\n`)
console.log(`Wrote USGS shore DEM snapshot: ${width}×${height}, ${valid.length} land samples, ${output.metadata.min_elevation_m.toFixed(1)}..${output.metadata.max_elevation_m.toFixed(1)} m NAVD88.`)
console.log(`Preserved georeferenced USGS/USDA NAIP orthophoto: ${imageryBytes.length.toLocaleString()} bytes, 3072×1668 PNG.`)
