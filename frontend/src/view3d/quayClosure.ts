import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'

/** A modelled connection to the rendered floor, not surveyed quay construction.
 * Return only vertices belonging to four-corner-supported water cells. This
 * closes the last raster-width shore gap without turning missing elevations
 * into zero or changing a survey coordinate. Search is bounded to 50 metres.
 */
export function quayFloorSampler(grid: BathymetryGrid) {
  const m=grid.metadata, nw=worldPosition(m.bounds.north,m.bounds.west),se=worldPosition(m.bounds.south,m.bounds.east)
  const dx=(se[0]-nw[0])/(m.width-1),dz=(se[2]-nw[2])/(m.height-1)
  const used=new Uint8Array(grid.values.length)
  for(let row=0;row<m.height-1;row++) for(let col=0;col<m.width-1;col++) {
    const a=row*m.width+col,b=a+1,c=a+m.width,d=c+1
    if([a,b,c,d].every(i=>grid.values[i]!==m.nodata_value&&grid.values[i]!>0&&Number.isFinite(grid.values[i]))) for(const i of [a,b,c,d]) used[i]=1
  }
  return (x:number,z:number): [number,number,number] | null => {
    const col=Math.round((x-nw[0])/dx),row=Math.round((z-nw[2])/dz)
    if(col<0||row<0||col>=m.width||row>=m.height) return null
    let best=-1, distance=50*50
    const maxRadius=Math.ceil(50/Math.min(dx,dz))
    for(let radius=0;radius<=maxRadius;radius++) {
      if(radius>0 && (radius-1)*Math.min(dx,dz)>Math.sqrt(distance)) break
      for(let y=-radius;y<=radius;y++) for(let c=-radius;c<=radius;c++) {
        if(radius>0 && Math.abs(y)!==radius && Math.abs(c)!==radius) continue
        if(row+y<0||row+y>=m.height||col+c<0||col+c>=m.width) continue
        const i=(row+y)*m.width+col+c
        if(!used[i]) continue
        const d=(nw[0]+(col+c)*dx-x)**2+(nw[2]+(row+y)*dz-z)**2
        if(d<distance){distance=d;best=i}
      }
    }
    return best<0?null:[nw[0]+(best%m.width)*dx,-grid.values[best]!,nw[2]+Math.floor(best/m.width)*dz]
  }
}
