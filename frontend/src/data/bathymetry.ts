export interface BathymetryBounds { west: number; south: number; east: number; north: number }
export interface BathymetryGrid {
  version: 1
  metadata: {
    title: string; source_kind: 'synthetic' | 'survey' | 'regional_dem'; source: string
    horizontal_crs: 'EPSG:4326' | 'EPSG:4269'; horizontal_units: 'degrees'; vertical_units: 'm'
    vertical_datum: string; depth_positive: 'down'; reference_water_level_m: number
    nodata_value: number; width: number; height: number; bounds: BathymetryBounds
    approximate_spacing_m: { east_west: number; north_south: number }
    min_depth_m: number; max_depth_m: number; nodata_cells: number
    source_spacing_m?: number
    reference_water_level_note?: string
    measurement_method?: 'multibeam_echosounder'
    survey_id?: string
    native_resolution?: string
    transition_m?: number
  }
  values: number[]
}

/** Labels come from the loaded dataset, never from a hard-coded MSL assumption. */
export function bathymetryDescription(grid: BathymetryGrid): string {
  const m = grid.metadata
  if (m.source_kind === 'synthetic') return 'Demo terrain · Not surveyed bathymetry · Fixed reference water level'
  const spacing = `${m.approximate_spacing_m.east_west.toFixed(1)}×${m.approximate_spacing_m.north_south.toFixed(1)} m display grid`
  return `${m.title} · ${m.vertical_datum} · ${m.source_spacing_m ? `Finest original grid ${m.source_spacing_m} m · ` : ''}${spacing} · Grid spacing is not survey accuracy / Not for navigation`
}

/** Only replace aligned harbor cells with a finer grid from the same source/frame. */
export function compatibleBathymetryDetail(main: BathymetryGrid, patch: BathymetryGrid): boolean {
  const a = main.metadata, b = patch.metadata, x = a.bounds, y = b.bounds
  if (a.source !== b.source || a.vertical_datum !== b.vertical_datum || a.horizontal_crs !== b.horizontal_crs || a.reference_water_level_m !== b.reference_water_level_m || y.west < x.west || y.east > x.east || y.south < x.south || y.north > x.north) return false
  const dx = (x.east-x.west)/(a.width-1), dy = (x.north-x.south)/(a.height-1)
  const aligned = (n: number) => Math.abs(n-Math.round(n)) < 1e-6
  const spanX = (y.east-y.west)/dx, spanY = (y.north-y.south)/dy
  return [(y.west-x.west)/dx,(y.east-x.west)/dx,(x.north-y.north)/dy,(x.north-y.south)/dy].every(aligned) && spanX > 0 && spanY > 0 && (b.width-1) > spanX && (b.height-1) > spanY && aligned((b.width-1)/spanX) && aligned((b.height-1)/spanY)
}

const object = (value: unknown): Record<string, unknown> | null => typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : null

export function parseBathymetry(value: unknown): BathymetryGrid | null {
  const root = object(value), metadata = object(root?.metadata), bounds = object(metadata?.bounds), spacing = object(metadata?.approximate_spacing_m)
  const width = metadata?.width, height = metadata?.height, values = root?.values
  if (root?.version !== 1 || !metadata || !['synthetic', 'survey', 'regional_dem'].includes(String(metadata.source_kind)) || typeof metadata.title !== 'string' || !metadata.title || typeof metadata.source !== 'string' || !metadata.source || metadata.horizontal_crs !== 'EPSG:4326' && metadata.horizontal_crs !== 'EPSG:4269' || metadata.horizontal_units !== 'degrees' || metadata.vertical_units !== 'm' || metadata.depth_positive !== 'down' || typeof metadata.vertical_datum !== 'string' || !metadata.vertical_datum || typeof metadata.reference_water_level_m !== 'number' || typeof metadata.nodata_value !== 'number' || !Number.isInteger(width) || !Number.isInteger(height) || (width as number) < 2 || (height as number) < 2 || !bounds || !spacing || !Array.isArray(values) || values.length !== (width as number) * (height as number)) return null
  const coordinates = [bounds.west, bounds.south, bounds.east, bounds.north]
  if (!coordinates.every(item => typeof item === 'number' && Number.isFinite(item)) || !(bounds.west as number < (bounds.east as number)) || !(bounds.south as number < (bounds.north as number)) || !values.every(item => typeof item === 'number' && Number.isFinite(item))) return null
  const noData = metadata.nodata_value as number
  if (metadata.source_spacing_m !== undefined && (typeof metadata.source_spacing_m !== 'number' || !Number.isFinite(metadata.source_spacing_m) || metadata.source_spacing_m <= 0) || metadata.reference_water_level_note !== undefined && typeof metadata.reference_water_level_note !== 'string' || metadata.survey_id !== undefined && typeof metadata.survey_id !== 'string' || metadata.measurement_method !== undefined && metadata.measurement_method !== 'multibeam_echosounder') return null
  const valid = values.filter(item => item !== noData) as number[]
  const minDepth = valid.reduce((minimum, item) => Math.min(minimum, item), Infinity)
  const maxDepth = valid.reduce((maximum, item) => Math.max(maximum, item), -Infinity)
  const declaredNumbers = [metadata.reference_water_level_m, metadata.min_depth_m, metadata.max_depth_m, metadata.nodata_cells, spacing.east_west, spacing.north_south]
  if (!valid.length || valid.some(item => item < 0) || !declaredNumbers.every(item => typeof item === 'number' && Number.isFinite(item)) || (spacing.east_west as number) <= 0 || (spacing.north_south as number) <= 0 || metadata.nodata_cells !== values.length - valid.length || Math.abs((metadata.min_depth_m as number) - minDepth) > .011 || Math.abs((metadata.max_depth_m as number) - maxDepth) > .011) return null
  return value as BathymetryGrid
}

export async function fetchBathymetry(url: string, timeoutMs = 8000): Promise<BathymetryGrid> {
  const response = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) })
  if (!response.ok) throw new Error(`DEM request failed (HTTP ${response.status})`)
  const parsed = parseBathymetry(await response.json())
  if (!parsed) throw new Error('Invalid DEM metadata or grid format')
  return parsed
}
