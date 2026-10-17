import { mkdir, writeFile } from 'node:fs/promises'

const width = 65
const height = 49
const bounds = { west: -118.31, south: 33.70, east: -118.19, north: 33.765 }
const noData = -9999
const values = []

for (let row = 0; row < height; row++) {
  const v = row / (height - 1)
  for (let column = 0; column < width; column++) {
    const u = column / (width - 1)
    const channel = 12 * Math.exp(-Math.pow((v - (.23 + u * .34)) / .115, 2))
    const outerBasin = 5 * Math.exp(-((u - .72) ** 2 + (v - .30) ** 2) / .055)
    const shoal = 7 * Math.exp(-((u - .28) ** 2 + (v - .72) ** 2) / .025)
    const relief = 2.6 * Math.sin(u * Math.PI * 4.4) * Math.cos(v * Math.PI * 3.2) + 1.4 * Math.sin((u + v) * Math.PI * 5)
    const missing = u < .055 && v > .84 || u > .92 && v > .90
    values.push(missing ? noData : Number(Math.max(4.5, Math.min(39, 15 + channel + outerBasin - shoal + relief)).toFixed(2)))
  }
}

const valid = values.filter(value => value !== noData)
const document = {
  version: 1,
  metadata: {
    title: 'HarborGuard synthetic Los Angeles Harbor bathymetry',
    source_kind: 'synthetic',
    source: 'Deterministic frontend demonstration grid; not surveyed bathymetry and not for navigation',
    horizontal_crs: 'EPSG:4326',
    horizontal_units: 'degrees',
    vertical_units: 'm',
    vertical_datum: 'Demonstration water-surface reference; not chart datum, MLLW, tide, or live water level',
    depth_positive: 'down',
    reference_water_level_m: 0,
    nodata_value: noData,
    width,
    height,
    bounds,
    approximate_spacing_m: { east_west: 173, north_south: 150 },
    min_depth_m: Math.min(...valid),
    max_depth_m: Math.max(...valid),
    nodata_cells: values.length - valid.length,
  },
  values,
}

await mkdir(new URL('../public/data/', import.meta.url), { recursive: true })
await writeFile(new URL('../public/data/seabed-dem.json', import.meta.url), `${JSON.stringify(document)}\n`)
console.log(`Saved ${width}x${height} synthetic bathymetry grid (${valid.length} valid cells).`)
