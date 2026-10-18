import type { BathymetryBounds, BathymetryGrid } from '../data/bathymetry'
import { buildSeabedMeshData } from './seabedMesh'

export function regionalMeshData(grid: BathymetryGrid, survey: BathymetryGrid, excludeBounds?: BathymetryBounds) {
  const data = buildSeabedMeshData(grid, 1, excludeBounds)
  const { width, height, nodata_value } = survey.metadata
  const indices: number[] = []
  // Iterate the already masked/clipped triangles, never bridge a fill NoData cell.
  for (let j = 0; j < data.indices.length; j += 6) {
    const a = data.indices[j]!, c = data.indices[j+1]!, b = data.indices[j+2]!, d = data.indices[j+5]!
    if ([a,b,c,d].every(i => survey.values[i] !== nodata_value)) continue
    indices.push(a,c,b,b,c,d)
  }
  return { ...data, indices, columns: width, rows: height }
}

/** Regional display field on the detail lattice. H12617 values are read-only.
 * Every measured boundary vertex is pinned; only unsupported fill vertices
 * interpolate (32 m) toward the regional product. No triangulated survey cell
 * is rendered by the fill layer. Masked samples never enter interpolation.
 */
export function regionalDetailGrid(fill: BathymetryGrid, detail: BathymetryGrid): BathymetryGrid {
  const a = fill.metadata, b = detail.metadata, width = b.width, height = b.height
  const distances = new Float32Array(width*height).fill(32)
  const nearest = new Int32Array(width*height).fill(-1)
  const values = new Array<number>(width*height)
  for (let row = 0; row < height; row++) for (let col = 0; col < width; col++) {
    const i = row*width+col
    if (detail.values[i] !== b.nodata_value) { distances[i] = 0; nearest[i] = i }
    const lon = b.bounds.west + col/(width-1)*(b.bounds.east-b.bounds.west)
    const lat = b.bounds.north - row/(height-1)*(b.bounds.north-b.bounds.south)
    const x = (lon-a.bounds.west)/(a.bounds.east-a.bounds.west)*(a.width-1)
    const y = (a.bounds.north-lat)/(a.bounds.north-a.bounds.south)*(a.height-1)
    const left = Math.min(a.width-2,Math.max(0,Math.floor(x))), top = Math.min(a.height-2,Math.max(0,Math.floor(y)))
    const tx=x-left,ty=y-top,index=top*a.width+left
    const v0=fill.values[index]!,v1=fill.values[index+1]!,v2=fill.values[index+a.width]!,v3=fill.values[index+a.width+1]!
    const w0=(1-tx)*(1-ty),w1=tx*(1-ty),w2=(1-tx)*ty,w3=tx*ty
    // Exact shared nodes/edges do not require an unused, zero-weight support
    // across the other side of a shoreline. Nonzero masked support stays masked.
    const invalid=v0===a.nodata_value&&w0>1e-7||v1===a.nodata_value&&w1>1e-7||v2===a.nodata_value&&w2>1e-7||v3===a.nodata_value&&w3>1e-7
    values[i]=invalid?b.nodata_value:Math.fround((v0===a.nodata_value?0:v0*w0)+(v1===a.nodata_value?0:v1*w1)+(v2===a.nodata_value?0:v2*w2)+(v3===a.nodata_value?0:v3*w3))
  }
  const dx=b.approximate_spacing_m.east_west,dz=b.approximate_spacing_m.north_south
  const update = (i: number, other: number, step: number) => {
    if (nearest[other]! >= 0 && distances[other]!+step < distances[i]!) { distances[i] = distances[other]!+step; nearest[i] = nearest[other]! }
  }
  for (let row=0;row<height;row++) for (let col=0;col<width;col++) {
    const i=row*width+col
    if(col>0) update(i,i-1,dx)
    if(row>0) update(i,i-width,dz)
    if(row>0 && col>0) update(i,i-width-1,Math.hypot(dx,dz))
    if(row>0 && col+1<width) update(i,i-width+1,Math.hypot(dx,dz))
  }
  for (let row=height-1;row>=0;row--) for (let col=width-1;col>=0;col--) {
    const i=row*width+col
    if(col+1<width) update(i,i+1,dx)
    if(row+1<height) update(i,i+width,dz)
    if(row+1<height && col+1<width) update(i,i+width+1,Math.hypot(dx,dz))
    if(row+1<height && col>0) update(i,i+width-1,Math.hypot(dx,dz))
  }
  const coarseField=Float32Array.from(values)
  for(let i=0;i<values.length;i++) {
    if(detail.values[i] !== b.nodata_value) { values[i]=detail.values[i]!; continue }
    if(values[i] === b.nodata_value || nearest[i]! < 0) continue
    const t=distances[i]!/32,weight=t*t*(3-2*t)
    values[i]=Math.fround(detail.values[nearest[i]!]!*(1-weight)+values[i]!*weight)
    // Only the independent fill geomorphs inside the aligned patch rectangle.
    // It must meet the coarse model at the boundary even where the fine MBES
    // coverage mask differs between the shared coarse sampling points.
    const col=i%width,row=Math.floor(i/width)
    const edge=Math.min(col*dx,(width-1-col)*dx,row*dz,(height-1-row)*dz)
    const tEdge=Math.min(1,edge/32),morph=tEdge*tEdge*(3-2*tEdge)
    values[i]=Math.fround(coarseField[i]!*(1-morph)+values[i]!*morph)
  }
  let min=Infinity,max=-Infinity,missing=0
  for(const value of values) if(value===b.nodata_value) missing++;else{min=Math.min(min,value);max=Math.max(max,value)}
  return { version: 1, metadata: { ...a, width, height, bounds: b.bounds, approximate_spacing_m: b.approximate_spacing_m, nodata_value: b.nodata_value, min_depth_m:min,max_depth_m:max,nodata_cells:missing }, values }
}
