import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'

/** Conservative display tessellation, not new soundings. Never bridges NoData. */
export function buildSeabedMeshData(grid: BathymetryGrid, refinement: 1 | 2 = 2) {
  const { width, height, bounds, nodata_value } = grid.metadata
  // Bound the additional GPU/CPU cost for user-supplied larger survey grids.
  const factor = grid.values.length <= 150_000 ? refinement : 1
  const columns = (width - 1) * factor + 1, rows = (height - 1) * factor + 1
  const positions = new Float32Array(columns * rows * 3)
  const depths = new Float32Array(columns * rows).fill(NaN)
  const indices: number[] = []
  for (let row = 0; row < rows; row++) for (let column = 0; column < columns; column++) {
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
    const source = row * width + column
    if ([source, source + 1, source + width, source + width + 1].some(index => grid.values[index] === nodata_value)) continue
    for (let y = 0; y < factor; y++) for (let x = 0; x < factor; x++) {
      const a = (row * factor + y) * columns + column * factor + x
      const b = a + 1, c = a + columns, d = c + 1
      indices.push(a, c, b, b, c, d)
    }
  }
  return { positions, depths, indices, columns, rows, factor }
}
