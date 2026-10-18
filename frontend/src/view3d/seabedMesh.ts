import type { BathymetryBounds, BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'

/** One display-cell feather INSIDE valid coverage, never fills or moves soundings.
 * Crop/LOD rectangle edges stay opaque so matching patches do not develop seams.
 */
export function surveyEdgeOpacity(depths: Float32Array, columns: number, rows: number): Float32Array {
  const opacity = new Float32Array(depths.length)
  for (let row = 0; row < rows; row++) for (let col = 0; col < columns; col++) {
    const i = row*columns+col
    if (!Number.isFinite(depths[i])) continue
    const boundary = col > 0 && !Number.isFinite(depths[i-1]) || col+1 < columns && !Number.isFinite(depths[i+1]) || row > 0 && !Number.isFinite(depths[i-columns]) || row+1 < rows && !Number.isFinite(depths[i+columns])
    opacity[i] = boundary ? 0 : 1
  }
  return opacity
}

/** Continuous distance-field coverage in metre space; display alpha only.
 * Leave the legacy one-cell helper above for its source-preservation regression.
 */
export function surveyEdgeFade(depths: Float32Array, columns: number, rows: number, dx: number, dz: number, band = 24): Float32Array {
  const distances = new Float32Array(depths.length)
  for (let i = 0; i < depths.length; i++) distances[i] = Number.isFinite(depths[i]) ? band : 0
  const diagonal = Math.hypot(dx, dz)
  for (let row = 0; row < rows; row++) for (let col = 0; col < columns; col++) {
    const i = row*columns+col
    if (col > 0) distances[i] = Math.min(distances[i]!, distances[i-1]!+dx)
    if (row > 0) distances[i] = Math.min(distances[i]!, distances[i-columns]!+dz)
    if (row > 0 && col > 0) distances[i] = Math.min(distances[i]!, distances[i-columns-1]!+diagonal)
    if (row > 0 && col+1 < columns) distances[i] = Math.min(distances[i]!, distances[i-columns+1]!+diagonal)
  }
  for (let row = rows-1; row >= 0; row--) for (let col = columns-1; col >= 0; col--) {
    const i = row*columns+col
    if (col+1 < columns) distances[i] = Math.min(distances[i]!, distances[i+1]!+dx)
    if (row+1 < rows) distances[i] = Math.min(distances[i]!, distances[i+columns]!+dz)
    if (row+1 < rows && col+1 < columns) distances[i] = Math.min(distances[i]!, distances[i+columns+1]!+diagonal)
    if (row+1 < rows && col > 0) distances[i] = Math.min(distances[i]!, distances[i+columns-1]!+diagonal)
  }
  return distances.map(distance => { const t = Math.min(1, distance/band); return t*t*(3-2*t) })
}

/** Conservative display tessellation, not new soundings. Never bridges NoData. */
export function buildSeabedMeshData(grid: BathymetryGrid, refinement: 1 | 2 = 2, excludeBounds?: BathymetryBounds) {
  const { width, height, bounds, nodata_value } = grid.metadata
  // Bound the additional GPU/CPU cost for user-supplied larger survey grids.
  const factor = grid.values.length <= 150_000 ? refinement : 1
  const columns = (width - 1) * factor + 1, rows = (height - 1) * factor + 1
  const positions = new Float32Array(columns * rows * 3)
  const depths = new Float32Array(columns * rows).fill(NaN)
  const indices: number[] = []
  const northwest = worldPosition(bounds.north, bounds.west), southeast = worldPosition(bounds.south, bounds.east)
  for (let row = 0; row < rows; row++) for (let column = 0; column < columns; column++) {
    if (factor === 1) {
      // Dense measured grids need no interpolation. Avoid millions of temporary
      // sample/weight/point arrays when remounting the 3D view.
      const index = row*columns+column, depth = grid.values[index]!
      positions[index*3] = northwest[0] + column/(columns-1)*(southeast[0]-northwest[0])
      positions[index*3+1] = depth === nodata_value ? 0 : -depth
      positions[index*3+2] = northwest[2] + row/(rows-1)*(southeast[2]-northwest[2])
      if (depth !== nodata_value) depths[index] = depth
      continue
    }
    const x = column / factor, y = row / factor
    const left = Math.min(width - 2, Math.floor(x)), top = Math.min(height - 2, Math.floor(y))
    const tx = x - left, ty = y - top
    const samples = [grid.values[top * width + left]!, grid.values[top * width + left + 1]!, grid.values[(top + 1) * width + left]!, grid.values[(top + 1) * width + left + 1]!]
    const weights = [(1 - tx) * (1 - ty), tx * (1 - ty), (1 - tx) * ty, tx * ty]
    const valid = samples.every((sample, i) => weights[i]! === 0 || sample !== nodata_value)
    const depth = valid ? samples.reduce((sum, sample, i) => sum + sample * weights[i]!, 0) : 0
    const lat = bounds.north - y / (height - 1) * (bounds.north - bounds.south)
    const lon = bounds.west + x / (width - 1) * (bounds.east - bounds.west)
    const index = row * columns + column
    positions.set(worldPosition(lat, lon, depth, 1), index * 3)
    if (valid) depths[index] = depth
  }
  for (let row = 0; row < height - 1; row++) for (let column = 0; column < width - 1; column++) {
    if (excludeBounds) {
      const lat = bounds.north - (row + .5) / (height - 1) * (bounds.north - bounds.south)
      const lon = bounds.west + (column + .5) / (width - 1) * (bounds.east - bounds.west)
      if (lon > excludeBounds.west && lon < excludeBounds.east && lat > excludeBounds.south && lat < excludeBounds.north) continue
    }
    const source = row * width + column
    if (grid.values[source] === nodata_value || grid.values[source+1] === nodata_value || grid.values[source+width] === nodata_value || grid.values[source+width+1] === nodata_value) continue
    for (let y = 0; y < factor; y++) for (let x = 0; x < factor; x++) {
      const a = (row * factor + y) * columns + column * factor + x
      const b = a + 1, c = a + columns, d = c + 1
      indices.push(a, c, b, b, c, d)
    }
  }
  return { positions, depths, indices, columns, rows, factor }
}
