import { readFile, writeFile } from 'node:fs/promises'
import { fromArrayBuffer } from 'geotiff'

const bounds = { west: -118.31, south: 33.70, east: -118.19, north: 33.765 }
const width = 512
const height = 278
const noData = -9999
function exportUrl(serviceUrl, parameters) {
  const url = new URL(serviceUrl)
  url.search = new URLSearchParams(parameters).toString()
  return url
}
const demUrl = exportUrl('https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage', {
  bbox: `${bounds.west},${bounds.south},${bounds.east},${bounds.north}`,
  bboxSR: '4326', imageSR: '4326', size: `${width},${height}`,
  format: 'tiff', pixelType: 'F32', interpolation: 'RSP_Bilinear', f: 'image',
})
const imageryUrl = exportUrl('https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage', {
  bbox: `${bounds.west},${bounds.south},${bounds.east},${bounds.north}`,
  bboxSR: '4326', imageSR: '4326', size: '1536,834', format: 'png32', interpolation: 'RSP_Bilinear', f: 'image',
})

const [response, imageryResponse] = await Promise.all([
  fetch(demUrl, { signal: AbortSignal.timeout(60000) }),
  fetch(imageryUrl, { signal: AbortSignal.timeout(60000) }),
])
if (!response.ok) throw new Error(`USGS 3DEP export failed: HTTP ${response.status}`)
if (!imageryResponse.ok) throw new Error(`USGS NAIP imagery export failed: HTTP ${imageryResponse.status}`)
const imageryBytes = Buffer.from(await imageryResponse.arrayBuffer())
if (imageryBytes.length < 1000 || !imageryBytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]))) throw new Error('USGS NAIP export did not return a usable PNG image')
const bathymetry = JSON.parse(await readFile(new URL('../public/data/seabed-dem.json', import.meta.url), 'utf8'))
const tiff = await fromArrayBuffer(await response.arrayBuffer())
const image = await tiff.getImage()
if (image.getWidth() !== width || image.getHeight() !== height || image.getGeoKeys().GeographicTypeGeoKey !== 4326) {
  throw new Error('USGS export dimensions or CRS do not match requested EPSG:4326 grid')
}
const rasterBounds = image.getBoundingBox()
const raster = await image.readRasters({ interleave: true })
const water = bathymetry.values
const bathyMeta = bathymetry.metadata
const values = Array.from({ length: width * height }, (_, index) => {
  const row = Math.floor(index / width)
  const column = index % width
  const lon = rasterBounds[0] + column / (width - 1) * (rasterBounds[2] - rasterBounds[0])
  const lat = rasterBounds[3] - row / (height - 1) * (rasterBounds[3] - rasterBounds[1])
  const bathyColumn = Math.round((lon - bathyMeta.bounds.west) / (bathyMeta.bounds.east - bathyMeta.bounds.west) * (bathyMeta.width - 1))
  const bathyRow = Math.round((bathyMeta.bounds.north - lat) / (bathyMeta.bounds.north - bathyMeta.bounds.south) * (bathyMeta.height - 1))
  const bathyValue = water[bathyRow * bathyMeta.width + bathyColumn]
  const elevation = raster[index]
  // Keep only valid USGS elevations on the land side of the regional topo-bathy shoreline mask.
  if (bathyValue !== bathyMeta.nodata_value || !Number.isFinite(elevation) || elevation < -100 || elevation > 9000) return noData
  return Math.round(elevation * 10) / 10
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
    acquisition_note: 'USGS 3DEP source mosaics are multi-resolution; this 512×278 EPSG:4326 display crop is resampled, not a 1 m delivered grid.',
    imagery_source: 'USGS National Map NAIP Imagery ImageServer; imagery is an orthophoto mosaic, not live video.',
    imagery_url: 'https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer',
    imagery_date_note: 'Image service copyright date: January 09, 2025; underlying acquisition dates vary by location.',
    imagery_file: 'shore-ortho-usgs-naip.png',
    imagery_grid: '1536×834 RGB orthophoto, exported to the same EPSG:4326 bounding box and draped over the land-only terrain mesh.',
    horizontal_crs: 'EPSG:4326', horizontal_units: 'degrees',
    vertical_datum: 'NAVD88', vertical_units: 'm', elevation_positive: 'up',
    vertical_alignment: 'NAVD88 values displayed with zero offset against the NOAA MSL water plane; datum transformation has not been applied.',
    width, height, bounds: { west: rasterBounds[0], south: rasterBounds[1], east: rasterBounds[2], north: rasterBounds[3] }, nodata_value: noData,
    min_elevation_m: Math.min(...valid), max_elevation_m: Math.max(...valid),
    nodata_cells: values.length - valid.length,
    spacing_m_approx: { east_west: 111320 * Math.cos(33.73 * Math.PI / 180) * (bounds.east - bounds.west) / (width - 1), north_south: 111132 * (bounds.north - bounds.south) / (height - 1) },
  },
  values,
}
await writeFile(new URL('../public/data/shore-dem-usgs-3dep.json', import.meta.url), `${JSON.stringify(output)}\n`)
await writeFile(new URL('../public/data/shore-ortho-usgs-naip.png', import.meta.url), imageryBytes)
console.log(`Wrote USGS shore DEM snapshot: ${width}×${height}, ${valid.length} land samples, ${output.metadata.min_elevation_m.toFixed(1)}..${output.metadata.max_elevation_m.toFixed(1)} m NAVD88.`)
console.log(`Wrote USGS/USDA NAIP orthophoto texture: ${imageryBytes.length.toLocaleString()} bytes, 1536×834 PNG.`)
