import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'

interface WaterRectangle { left: number; right: number; top: number; bottom: number }
export interface WaterSurfaceData { positions: number[]; indices: number[]; supportedCells: number; rectangles: WaterRectangle[] }

/** Build a flat water surface only over grid cells with four supported underwater corners. */
export function buildWaterSurfaceData(grid: BathymetryGrid): WaterSurfaceData {
  const { width, height, bounds, nodata_value } = grid.metadata
  const positions: number[] = []
  const indices: number[] = []
  // Water is flat: merge identical supported row runs into rectangles, preserving
  // the exact mask instead of sending millions of redundant planar triangles.
  const rectangles: WaterRectangle[] = []
  let active = new Map<string, WaterRectangle>(), supportedCells = 0
  for (let row = 0; row < height - 1; row++) {
    const next = new Map<string, WaterRectangle>()
    let left = -1
    for (let column = 0; column < width; column++) {
      const a = row * width + column, b = a + 1, c = a + width, d = c + 1
      const valid = column < width - 1 && grid.values[a] !== nodata_value && grid.values[b] !== nodata_value && grid.values[c] !== nodata_value && grid.values[d] !== nodata_value
      if (valid) { supportedCells++; if (left < 0) left = column; continue }
      if (left < 0) continue
      const key = `${left}:${column}`
      const rectangle = active.get(key) ?? { left, right: column, top: row, bottom: row + 1 }
      rectangle.bottom = row + 1
      next.set(key, rectangle)
      active.delete(key)
      left = -1
    }
    rectangles.push(...active.values())
    active = next
  }
  rectangles.push(...active.values())
  for (const { left, right, top, bottom } of rectangles) {
    const index = positions.length / 3
    for (const [row,column] of [[top,left],[top,right],[bottom,left],[bottom,right]]) {
      const lat = bounds.north - row! / (height - 1) * (bounds.north - bounds.south)
      const lon = bounds.west + column! / (width - 1) * (bounds.east - bounds.west)
      positions.push(...worldPosition(lat,lon,0))
    }
    indices.push(index,index+2,index+1,index+1,index+2,index+3)
  }
  return { positions, indices, supportedCells, rectangles }
}
