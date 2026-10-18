import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'

interface WaterRectangle { left: number; right: number; top: number; bottom: number }
export interface WaterSurfaceData { positions: number[]; indices: number[]; supportedCells: number; rectangles: WaterRectangle[] }

/** Mask input is the regional+survey WATER domain, not MBES survey coverage.
 * Positive depth establishes modelled water; NoData and on/above-datum land do
 * not establish water. Absence of a sounding does not establish land either.
 */
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
      const valid = column < width - 1 && [a,b,c,d].every(i => grid.values[i] !== nodata_value && Number.isFinite(grid.values[i]) && grid.values[i]! > 0)
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
