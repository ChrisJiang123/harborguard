import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'

/** Mask-aware central differences in unexaggerated metre space. NoData is not 0.
 * Invalid vertices are never indexed. One-sided differences at coverage edges
 * avoid pointing edge normals down an artificial wall to a zero-height sample.
 */
export function heightfieldNormals(heights: Float32Array, columns: number, rows: number, dx: number, dz: number): Float32Array {
  const normals = new Float32Array(heights.length * 3)
  for (let row = 0; row < rows; row++) for (let col = 0; col < columns; col++) {
    const i = row * columns + col, h = heights[i]!
    if (!Number.isFinite(h)) { normals[i * 3 + 1] = 1; continue }
    const hasLeft = col > 0 && Number.isFinite(heights[i-1]), hasRight = col+1 < columns && Number.isFinite(heights[i+1])
    const hasTop = row > 0 && Number.isFinite(heights[i-columns]), hasBottom = row+1 < rows && Number.isFinite(heights[i+columns])
    const left = hasLeft ? heights[i-1]! : h, right = hasRight ? heights[i+1]! : h
    const top = hasTop ? heights[i-columns]! : h, bottom = hasBottom ? heights[i+columns]! : h
    const nx = (left-right)/(dx * (hasLeft && hasRight ? 2 : 1))
    const nz = (top-bottom)/(dz * (hasTop && hasBottom ? 2 : 1))
    const length = Math.hypot(nx, 1, nz)
    normals.set([nx/length, 1/length, nz/length], i*3)
  }
  return normals
}

/** Include fine central-difference normals for inserted LOD boundary vertices. */
export function stitchedHeightfieldNormals(heights: Float32Array, columns: number, rows: number, dx: number, dz: number, positions: Float32Array, fine?: BathymetryGrid) {
  const normals=new Float32Array(positions.length)
  normals.set(heightfieldNormals(heights,columns,rows,dx,dz))
  if (!fine) return normals
  const f=fine.metadata,nw=worldPosition(f.bounds.north,f.bounds.west),se=worldPosition(f.bounds.south,f.bounds.east)
  for(let i=columns*rows;i<positions.length/3;i++) {
    const col=Math.round((positions[i*3]!-nw[0])/(se[0]-nw[0])*(f.width-1))
    const row=Math.round((positions[i*3+2]!-nw[2])/(se[2]-nw[2])*(f.height-1))
    const center=positions[i*3+1]!,values=new Float32Array(9)
    for(let y=-1;y<=1;y++) for(let x=-1;x<=1;x++) {
      const value=fine.values[(row+y)*f.width+col+x]
      values[(y+1)*3+x+1]=row+y<0||row+y>=f.height||col+x<0||col+x>=f.width||value===f.nodata_value||value===undefined ? center : -value
    }
    normals.set(heightfieldNormals(values,3,3,f.approximate_spacing_m.east_west,f.approximate_spacing_m.north_south).subarray(12,15),i*3)
  }
  return normals
}

/** Display-only 3×3 Gaussian; never used on measured H12617 elevations. */
export function smoothRegionalHeights(heights: Float32Array, width: number, height: number) {
  const result = new Float32Array(heights)
  for (let row = 0; row < height; row++) for (let col = 0; col < width; col++) {
    const i = row*width+col
    if (!Number.isFinite(heights[i])) continue
    let sum = 0, weight = 0
    for (let y = -1; y <= 1; y++) for (let x = -1; x <= 1; x++) {
      if (row+y < 0 || row+y >= height || col+x < 0 || col+x >= width) continue
      const value = heights[(row+y)*width+col+x]!
      if (!Number.isFinite(value)) continue
      const w = (x === 0 ? 2 : 1) * (y === 0 ? 2 : 1)
      sum += value*w; weight += w
    }
    result[i] = sum/weight
  }
  return result
}
