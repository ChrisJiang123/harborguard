import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'

export interface WaterSurfaceData { positions: number[]; indices: number[] }

/** Build a flat water surface only over grid cells with four supported underwater corners. */
export function buildWaterSurfaceData(grid: BathymetryGrid): WaterSurfaceData {
  const { width, height, bounds, nodata_value } = grid.metadata
  const positions: number[] = []
  const indices: number[] = []
  for (let row = 0; row < height; row++) {
    const lat = bounds.north - row / (height - 1) * (bounds.north - bounds.south)
    for (let column = 0; column < width; column++) {
      const lon = bounds.west + column / (width - 1) * (bounds.east - bounds.west)
      positions.push(...worldPosition(lat, lon, 0))
    }
  }
  for (let row = 0; row < height - 1; row++) {
    for (let column = 0; column < width - 1; column++) {
      const a = row * width + column, b = a + 1, c = a + width, d = c + 1
      if ([a, b, c, d].some(index => grid.values[index] === nodata_value)) continue
      indices.push(a, c, b, b, c, d)
    }
  }
  return { positions, indices }
}
