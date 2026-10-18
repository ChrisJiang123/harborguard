import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'
import type { buildSeabedMeshData } from './seabedMesh'

/** Split coarse boundary triangles along the finer source polyline. Unlike a
 * skirt or geomorph, this adds source-supported vertices without moving any
 * existing vertex or changing a sounding. Never extends an edge through NoData.
 */
export function stitchTerrainBoundary(data: ReturnType<typeof buildSeabedMeshData>, coarse: BathymetryGrid, fine: BathymetryGrid) {
  const c=coarse.metadata,f=fine.metadata
  const nw=worldPosition(f.bounds.north,f.bounds.west), se=worldPosition(f.bounds.south,f.bounds.east)
  const positions=Array.from(data.positions), depths=Array.from(data.depths), indices:number[]=[]
  const cache=new Map<number,number>()
  const point=(i:number) => [data.positions[i*3]!,data.positions[i*3+2]!]
  const near=(x:number,y:number) => Math.abs(x-y)<.02
  const sample=(x:number,z:number) => [Math.round((x-nw[0])/(se[0]-nw[0])*(f.width-1)),Math.round((z-nw[2])/(se[2]-nw[2])*(f.height-1))]
  for(let j=0;j<data.indices.length;j+=3) {
    const triangle=data.indices.slice(j,j+3)
    let split=false
    for(let edge=0;edge<3;edge++) {
      const a=triangle[edge]!,b=triangle[(edge+1)%3]!,opposite=triangle[(edge+2)%3]!
      const [ax,az]=point(a),[bx,bz]=point(b)
      const vertical=near(ax!,bx!)&&(near(ax!,nw[0])||near(ax!,se[0]))&&Math.min(az!,bz!)>=nw[2]-.02&&Math.max(az!,bz!)<=se[2]+.02
      const horizontal=near(az!,bz!)&&(near(az!,nw[2])||near(az!,se[2]))&&Math.min(ax!,bx!)>=nw[0]-.02&&Math.max(ax!,bx!)<=se[0]+.02
      if(!vertical&&!horizontal) continue
      const [ac,ar]=sample(ax!,az!),[bc,br]=sample(bx!,bz!)
      const steps=Math.max(Math.abs(bc!-ac!),Math.abs(br!-ar!))
      if(steps<2) continue
      const support=Array.from({length:steps+1},(_,k)=>Math.round(ar!+(br!-ar!)*k/steps)*f.width+Math.round(ac!+(bc!-ac!)*k/steps))
      if(support.some(i=>i<0||i>=fine.values.length||fine.values[i]===f.nodata_value)) continue
      let previous=a
      for(let k=1;k<=steps;k++) {
        let next=b
        if(k<steps) {
          const source=support[k]!
          next=cache.get(source)??-1
          if(next<0) {
            next=depths.length;cache.set(source,next)
            const lon=f.bounds.west+(source%f.width)/(f.width-1)*(f.bounds.east-f.bounds.west)
            const lat=f.bounds.north-Math.floor(source/f.width)/(f.height-1)*(f.bounds.north-f.bounds.south)
            positions.push(...worldPosition(lat,lon,fine.values[source]!,1));depths.push(fine.values[source]!)
          }
        }
        indices.push(previous,next,opposite);previous=next
      }
      split=true;break
    }
    if(!split) indices.push(...triangle)
  }
  // Existing original samples/NoData, including unused vertices, are preserved.
  return { ...data, positions:Float32Array.from(positions),depths:Float32Array.from(depths),indices,sourceWidth:c.width }
}
