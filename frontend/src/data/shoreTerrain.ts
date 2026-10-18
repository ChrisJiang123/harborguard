export interface ShoreTerrainGrid {
  version: 1
  metadata: {
    title: string
    source_kind: 'lidar_dem'
    source: string
    source_url: string
    acquisition_note: string
    imagery_source: string
    imagery_url: string
    imagery_date_note: string
    imagery_file: string
    imagery_grid: string
    imagery_bounds?: { west: number; south: number; east: number; north: number }
    grid_registration?: 'pixel_centres'
    horizontal_crs: 'EPSG:4326'
    horizontal_units: 'degrees'
    vertical_datum: 'NAVD88'
    vertical_units: 'm'
    elevation_positive: 'up'
    vertical_alignment: string
    width: number
    height: number
    bounds: { west: number; south: number; east: number; north: number }
    nodata_value: number
    min_elevation_m: number
    max_elevation_m: number
    nodata_cells: number
    spacing_m_approx: { east_west: number; north_south: number }
  }
  values: number[]
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function parseShoreTerrain(value: unknown): ShoreTerrainGrid | null {
  if (!isObject(value) || value.version !== 1 || !isObject(value.metadata) || !isObject(value.metadata.bounds) || !isObject(value.metadata.spacing_m_approx) || !Array.isArray(value.values)) return null
  const metadata = value.metadata
  const width = metadata.width, height = metadata.height
  if (metadata.source_kind !== 'lidar_dem' || metadata.horizontal_crs !== 'EPSG:4326' || metadata.vertical_datum !== 'NAVD88' || metadata.vertical_units !== 'm' || metadata.elevation_positive !== 'up' || typeof metadata.imagery_source !== 'string' || typeof metadata.imagery_url !== 'string' || typeof metadata.imagery_date_note !== 'string' || typeof metadata.imagery_file !== 'string' || typeof metadata.imagery_grid !== 'string' || typeof metadata.nodata_value !== 'number' || typeof width !== 'number' || typeof height !== 'number' || !Number.isInteger(width) || !Number.isInteger(height) || width < 2 || height < 2 || value.values.length !== width * height || !value.values.every(item => typeof item === 'number' && Number.isFinite(item))) return null
  const bounds = metadata.bounds as Record<string, unknown>
  const west = bounds.west, south = bounds.south, east = bounds.east, north = bounds.north
  if (typeof west !== 'number' || typeof south !== 'number' || typeof east !== 'number' || typeof north !== 'number' || ![west, south, east, north].every(Number.isFinite) || !(west < east) || !(south < north)) return null
  const valid = value.values.filter(item => item !== metadata.nodata_value) as number[]
  if (!valid.length || valid.length < width * height * .2 || valid.some(item => item < -15000 || item > 9000) || metadata.nodata_cells !== width * height - valid.length) return null
  if (Math.abs(valid.reduce((a,b) => Math.min(a,b), Infinity) - Number(metadata.min_elevation_m)) > .11 || Math.abs(valid.reduce((a,b) => Math.max(a,b), -Infinity) - Number(metadata.max_elevation_m)) > .11) return null
  return value as unknown as ShoreTerrainGrid
}

export function sampleShoreElevation(grid: ShoreTerrainGrid, lat: number, lon: number): number | null {
  const { bounds, width, height, nodata_value } = grid.metadata
  const x = (lon - bounds.west) / (bounds.east - bounds.west) * (width - 1)
  const y = (bounds.north - lat) / (bounds.north - bounds.south) * (height - 1)
  if (x < 0 || x >= width - 1 || y < 0 || y >= height - 1) return null
  const column = Math.floor(x), row = Math.floor(y), tx = x - column, ty = y - row
  const a = grid.values[row * width + column]!, b = grid.values[row * width + column + 1]!
  const c = grid.values[(row + 1) * width + column]!, d = grid.values[(row + 1) * width + column + 1]!
  if ([a, b, c, d].some(item => item === nodata_value)) return null
  return (a * (1 - tx) + b * tx) * (1 - ty) + (c * (1 - tx) + d * tx) * ty
}

let cached: Promise<ShoreTerrainGrid> | null = null
export function loadShoreTerrain() {
  cached ??= fetch('/data/shore-dem-usgs-3dep.json', { signal: AbortSignal.timeout(12000) }).then(async response => {
    if (!response.ok) throw new Error(`USGS land DEM request failed (HTTP ${response.status})`)
    const grid = parseShoreTerrain(await response.json())
    if (!grid) throw new Error('Invalid USGS land DEM metadata or grid format')
    return grid
  }).catch(error => { cached = null; throw error })
  return cached
}
