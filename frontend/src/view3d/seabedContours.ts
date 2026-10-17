import type { BathymetryBounds, BathymetryGrid } from '../data/bathymetry'

export interface ContourPoint { lat: number; lon: number; depth: number }
export interface ContourSegment { depth: number; from: ContourPoint; to: ContourPoint }

interface Sample extends ContourPoint { valid: boolean }

/** Build lightweight contour segments from the same grid used by the seabed mesh. */
export function buildBathymetryContours(grid: BathymetryGrid, interval = 5, excludeBounds?: BathymetryBounds): ContourSegment[] {
  if (!Number.isFinite(interval) || interval <= 0) return []
  const { width, height, bounds, nodata_value, min_depth_m, max_depth_m } = grid.metadata
  const first = Math.ceil(min_depth_m / interval) * interval
  const point = (row: number, column: number): Sample => {
    const depth = grid.values[row * width + column]!
    return {
      lat: bounds.north - row / (height - 1) * (bounds.north - bounds.south),
      lon: bounds.west + column / (width - 1) * (bounds.east - bounds.west),
      depth,
      valid: depth !== nodata_value,
    }
  }
  const crossing = (a: Sample, b: Sample, depth: number): ContourPoint | null => {
    if (!a.valid || !b.valid || (a.depth < depth) === (b.depth < depth) || a.depth === b.depth) return null
    const ratio = (depth - a.depth) / (b.depth - a.depth)
    return { lat: a.lat + (b.lat - a.lat) * ratio, lon: a.lon + (b.lon - a.lon) * ratio, depth }
  }
  const segments: ContourSegment[] = []
  for (let row = 0; row < height - 1; row++) for (let column = 0; column < width - 1; column++) {
    if (excludeBounds) {
      const lat = bounds.north - (row + .5) / (height - 1) * (bounds.north - bounds.south)
      const lon = bounds.west + (column + .5) / (width - 1) * (bounds.east - bounds.west)
      if (lon > excludeBounds.west && lon < excludeBounds.east && lat > excludeBounds.south && lat < excludeBounds.north) continue
    }
    const index = row*width+column
    const a = grid.values[index]!, b = grid.values[index+1]!, c = grid.values[index+width]!, d = grid.values[index+width+1]!
    if (a === nodata_value || b === nodata_value || c === nodata_value || d === nodata_value) continue
    const minimum = Math.min(a,b,c,d), maximum = Math.min(max_depth_m, Math.max(a,b,c,d))
    const firstCrossing = Math.max(first, (Math.floor(minimum/interval)+1)*interval)
    if (firstCrossing > maximum) continue
    const corners = [point(row, column), point(row, column + 1), point(row + 1, column + 1), point(row + 1, column)]
    for (let depth = firstCrossing; depth <= maximum; depth += interval) {
      const intersections = [[0, 1], [1, 2], [2, 3], [3, 0]].map(([a, b]) => crossing(corners[a]!, corners[b]!, depth)).filter((item): item is ContourPoint => item !== null)
      if (intersections.length === 2) segments.push({ depth, from: intersections[0]!, to: intersections[1]! })
      else if (intersections.length === 4) {
        segments.push({ depth, from: intersections[0]!, to: intersections[1]! })
        segments.push({ depth, from: intersections[2]!, to: intersections[3]! })
      }
    }
  }
  return segments
}
