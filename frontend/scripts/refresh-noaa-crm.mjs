import { writeFile } from 'node:fs/promises'

// NOAA/NCEI Southern California Coastal Relief Model v2, 1 arc-second.
// Crop indices are inclusive and correspond to the existing HarborGuard demo extent.
const rowStart = 9720
const rowEnd = 9954
const columnStart = 16884
const columnEnd = 17316
const height = rowEnd - rowStart + 1
const width = columnEnd - columnStart + 1
// THREDDS accepts the brackets escaped but requires range colons to remain literal.
const endpoint = `https://www.ngdc.noaa.gov/thredds/dodsC/crm/crm_socal_1as_vers2.nc.ascii?Band1%5B${rowStart}:1:${rowEnd}%5D%5B${columnStart}:1:${columnEnd}%5D`

const response = await fetch(endpoint, { signal: AbortSignal.timeout(90000) })
if (!response.ok) throw new Error(`NOAA THREDDS returned HTTP ${response.status}`)
const text = await response.text()
if (text.length > 5_000_000) throw new Error(`Unexpectedly large NOAA subset (${text.length} characters)`)

const header = text.match(/Band1\.Band1\[(\d+)\]\[(\d+)\]/)
if (!header || Number(header[1]) !== height || Number(header[2]) !== width) throw new Error('NOAA grid dimensions do not match the requested extent')
const valuesSection = text.split(/Band1\.Band1\[\d+\]\[\d+\]\r?\n/, 2)[1]?.split(/\r?\nBand1\.lat\[/, 1)[0]
if (!valuesSection) throw new Error('NOAA response does not contain a parseable elevation grid')

async function readAxis(name, start, end, expectedLength) {
  const url = `https://www.ngdc.noaa.gov/thredds/dodsC/crm/crm_socal_1as_vers2.nc.ascii?${name}%5B${start}:1:${end}%5D`
  const axisResponse = await fetch(url, { signal: AbortSignal.timeout(30000) })
  if (!axisResponse.ok) throw new Error(`NOAA ${name} axis returned HTTP ${axisResponse.status}`)
  const axisText = await axisResponse.text()
  const axisHeader = axisText.match(new RegExp(`${name}\\[(\\d+)\\]\\r?\\n`))
  const axisValues = axisText.split(axisHeader?.[0] ?? '\0', 2)[1]?.split(/\r?\n/, 1)[0]?.split(/,\s*/).map(Number)
  if (!axisHeader || Number(axisHeader[1]) !== expectedLength || axisValues?.length !== expectedLength || axisValues.some(value => !Number.isFinite(value))) throw new Error(`NOAA ${name} axis is invalid`)
  return axisValues
}
const [sourceLatitudes, sourceLongitudes] = await Promise.all([
  readAxis('lat', rowStart, rowEnd, height),
  readAxis('lon', columnStart, columnEnd, width),
])

const elevations = []
for (const line of valuesSection.split(/\r?\n/)) {
  const match = line.match(/^\[(\d+)\],\s*(.*)$/)
  if (!match) continue
  const row = Number(match[1])
  if (row !== elevations.length / width) throw new Error(`NOAA grid row sequence is discontinuous at ${row}`)
  const cells = match[2].split(/,\s*/).map(Number)
  if (cells.length !== width || cells.some(value => !Number.isFinite(value))) throw new Error(`Invalid NOAA values in row ${row}`)
  elevations.push(...cells)
}
if (elevations.length !== width * height) throw new Error(`NOAA response returned ${elevations.length} cells, expected ${width * height}`)

// NOAA CRM cells are elevations in metres, positive upward, relative to MSL.
// Land cells (>= MSL) are excluded; below-MSL cells become water depths positive down.
const nodata = -9999
// OPeNDAP latitude indices increase south-to-north; the frontend grid contract
// stores rows north-to-south, so reverse rows without changing east-west order.
const depths = Array.from({ length: height }, (_, row) => {
  const sourceRow = height - row - 1
  return elevations.slice(sourceRow * width, (sourceRow + 1) * width).map(elevation => elevation === nodata || elevation >= 0 ? nodata : -elevation)
}).flat()
const valid = depths.filter(depth => depth !== nodata)
if (valid.length < width * height * 0.2) throw new Error('Too few below-MSL cells; refusing to replace the current seabed file')

const west = -118.31
const east = -118.19
const south = 33.70
const north = 33.765
const close = (actual, expected) => Math.abs(actual - expected) < 0.000001
if (!close(sourceLatitudes[0], south) || !close(sourceLatitudes.at(-1), north) || !close(sourceLongitudes[0], west) || !close(sourceLongitudes.at(-1), east)) throw new Error('NOAA grid axes do not match declared geographic bounds')
const minDepth = Math.min(...valid)
const maxDepth = Math.max(...valid)
const document = {
  version: 1,
  metadata: {
    title: 'NOAA/NCEI Southern California Coastal Relief Model v2 — Port of Los Angeles crop',
    source_kind: 'regional_dem',
    source: 'NOAA/NCEI U.S. Coastal Relief Model, Southern California Version 2 (2012), 1 arc-second; regional merged topobathymetric DEM, not navigation data',
    source_url: 'https://doi.org/10.7289/V5V985ZM',
    access_url: 'https://www.ngdc.noaa.gov/thredds/catalog/crm/catalog.html?dataset=crmDatasetScan/crm_socal_1as_vers2.nc',
    retrieved_at: new Date().toISOString(),
    horizontal_crs: 'EPSG:4269',
    horizontal_units: 'degrees',
    horizontal_transform: 'Source NAD83 geographic coordinates are used directly in the local WGS84-style ENU frame; legacy NAD83/WGS84 datum difference is not resolved to a realization and is not survey-grade.',
    vertical_units: 'm',
    vertical_datum: 'Mean Sea Level (MSL), NOAA CRM Southern California Version 2; land elevations >= MSL masked as NoData; this is not MLLW or live tide.',
    source_elevation_positive: 'up',
    depth_positive: 'down',
    reference_water_level_m: 0,
    reference_water_level_note: 'MSL reference plane from NOAA regional model; display reference only, not a real-time tide observation.',
    nodata_value: nodata,
    nodata_rule: 'NOAA FillValue (-9999) and land/on-mean-sea-level elevations (>=0 m) masked; only below-MSL cells rendered as seabed.',
    width,
    height,
    bounds: { west, south, east, north },
    approximate_spacing_m: { east_west: 25.7, north_south: 30.9 },
    min_depth_m: minDepth,
    max_depth_m: maxDepth,
    nodata_cells: depths.length - valid.length,
    intended_use: 'Regional situational visualization only. Not for navigation, dredging, engineering, or safety-critical decisions; 1 arc-second regional grid does not resolve all harbor-channel details.',
  },
  values: depths,
}

await writeFile(new URL('../public/data/seabed-dem.json', import.meta.url), `${JSON.stringify(document)}\n`)
console.log(`Saved NOAA CRM crop ${width}x${height}: ${valid.length} below-MSL cells, ${depths.length - valid.length} land/NoData cells, depth ${minDepth}–${maxDepth} m.`)
