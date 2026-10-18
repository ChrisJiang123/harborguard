import { useEffect, useMemo } from 'react'
import { useTexture } from '@react-three/drei'
import { useThree } from '@react-three/fiber'
import { BufferGeometry, Color, DoubleSide, Float32BufferAttribute, LinearMipmapLinearFilter, SRGBColorSpace } from 'three'
import type { ShoreTerrainGrid } from '../data/shoreTerrain'
import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'
import { heightfieldNormals, smoothRegionalHeights } from './heightfield'
import { quayFloorSampler } from './quayClosure'
import { terrainMaterial } from './terrainMaterial'

const COLOR_STOPS = [new Color('#c4b48e'), new Color('#a7a982'), new Color('#718c70'), new Color('#536f63'), new Color('#7c7669')]
const WHITE = new Color('#ffffff')
const BLACK = new Color('#000000')

function heightColor(height: number, minimum: number, maximum: number): Color {
  const p = Math.max(0, Math.min(1, (height - minimum) / Math.max(1, maximum - minimum)))
  const scaled = Math.pow(p, .46) * (COLOR_STOPS.length - 1)
  const index = Math.min(COLOR_STOPS.length - 2, Math.floor(scaled))
  return COLOR_STOPS[index]!.clone().lerp(COLOR_STOPS[index + 1]!, scaled - index).lerp(WHITE, .86)
}
export function CoastalTerrain3D({ grid, verticalScale, quayWalls = true, smoothing = true, shoreline = true, floor, detailFloor }: { grid: ShoreTerrainGrid; verticalScale: number; quayWalls?: boolean; smoothing?: boolean; shoreline?: boolean; floor?: BathymetryGrid | null; detailFloor?: BathymetryGrid | null }) {
  const gl = useThree(s => s.gl)
  // Resolve imagery before allocating the large land mesh. A suspended first
  // render discards its memoized work; allocating first repeats that work on
  // retry (and twice again in development StrictMode).
  const sourceImagery = useTexture('/data/shore-ortho-usgs-naip.png')
  const geometry = useMemo(() => {
    const result = new BufferGeometry()
    const { width, height, bounds, nodata_value, min_elevation_m, max_elevation_m } = grid.metadata
    const positions = new Float32Array(width*height*3)
    const colors = new Float32Array(width*height*3)
    const uvs = new Float32Array(width*height*2)
    const indices: number[] = []
    const raw = Float32Array.from(grid.values, value => value === nodata_value ? NaN : value)
    const elevations = smoothing ? smoothRegionalHeights(raw, width, height) : raw
    for (let row = 0; row < height; row++) {
      const lat = bounds.north - row / (height - 1) * (bounds.north - bounds.south)
      for (let column = 0; column < width; column++) {
        const lon = bounds.west + column / (width - 1) * (bounds.east - bounds.west)
        const i = row*width+column
        const elevation = elevations[i]!
        const valid = Number.isFinite(elevation)
        const point = worldPosition(lat, lon)
        positions.set([point[0], valid ? elevation : 0, point[2]], i*3)
        const imageBounds=grid.metadata.imagery_bounds??bounds
        uvs.set([(lon-imageBounds.west)/(imageBounds.east-imageBounds.west),(lat-imageBounds.south)/(imageBounds.north-imageBounds.south)], i*2)
        const color = valid ? heightColor(elevation, min_elevation_m, max_elevation_m) : BLACK
        colors.set([color.r, color.g, color.b], i*3)
      }
    }
    for (let row = 0; row < height - 1; row++) {
      for (let column = 0; column < width - 1; column++) {
        const a = row * width + column, b = a + 1, c = a + width, d = c + 1
        if ([a, b, c, d].some(index => grid.values[index] === nodata_value)) continue
        indices.push(a, c, b, b, c, d)
      }
    }
    result.setAttribute('position', new Float32BufferAttribute(positions, 3))
    result.setAttribute('color', new Float32BufferAttribute(colors, 3))
    result.setAttribute('uv', new Float32BufferAttribute(uvs, 2))
    result.setIndex(indices)
    const nw = worldPosition(bounds.north, bounds.west), se = worldPosition(bounds.south, bounds.east)
    result.setAttribute('normal', new Float32BufferAttribute(heightfieldNormals(elevations,width,height,(se[0]-nw[0])/(width-1),(se[2]-nw[2])/(height-1)),3))
    result.computeBoundingSphere()
    return result
  }, [grid, smoothing])
  const walls = useMemo(() => {
    const { width, height, nodata_value } = grid.metadata
    const positions: number[] = [], indices: number[] = []
    const surface = geometry.getAttribute('position')
    const sampleFloor=floor?quayFloorSampler(floor):null, sampleDetail=detailFloor?quayFloorSampler(detailFloor):null
    const floorCache=new Map<number,[number,number,number]|null>()
    const atFloor=(i:number) => {
      if(floorCache.has(i)) return floorCache.get(i)
      const x=surface.getX(i),z=surface.getZ(i),point=sampleDetail?.(x,z)??sampleFloor?.(x,z)??null
      floorCache.set(i,point);return point
    }
    const validCell = (row: number, col: number) => row >= 0 && col >= 0 && row < height-1 && col < width-1 && [row*width+col,row*width+col+1,(row+1)*width+col,(row+1)*width+col+1].every(i => grid.values[i] !== nodata_value)
    const edge = (a: number, b: number) => {
      const ay = surface.getY(a), by = surface.getY(b)
      if (Math.max(ay,by) > 15) return
      // Illustrative closure to supported floor vertices, not a measured wall.
      // Land NAVD88 / floor datum are untransformed (0 m offset), as disclosed.
      const pa:[number,number,number]=[surface.getX(a),ay,surface.getZ(a)],pb:[number,number,number]=[surface.getX(b),by,surface.getZ(b)]
      const fa=atFloor(a),fb=atFloor(b)
      if(!fa||!fb) return
      // Hidden closure reserve extends below the model's deepest floor. Ending
      // each independent panel exactly at a nearest floor sample leaves small
      // triangular light leaks between that polyline and the sampled floor.
      // The actual floor occludes the reserve. This is illustrative LAND quay
      // closure, never a skirt on, or a change to, the measured MBES geometry.
      const reserve=-Math.max(floor?.metadata.max_depth_m??0,detailFloor?.metadata.max_depth_m??0)-1
      const n = positions.length/3
      positions.push(...pa,...pb,fa[0],Math.min(reserve,fa[1]),fa[2],fb[0],Math.min(reserve,fb[1]),fb[2])
      indices.push(n,n+2,n+1,n+1,n+2,n+3)
    }
    for (let row = 1; row < height-2; row++) for (let col = 1; col < width-2; col++) {
      if (!validCell(row,col)) continue
      const a = row*width+col,b=a+1,c=a+width,d=c+1
      if (!validCell(row-1,col)) edge(b,a)
      if (!validCell(row+1,col)) edge(c,d)
      if (!validCell(row,col-1)) edge(a,c)
      if (!validCell(row,col+1)) edge(d,b)
    }
    const result = new BufferGeometry()
    result.setAttribute('position',new Float32BufferAttribute(positions,3)); result.setIndex(indices)
    result.computeVertexNormals(); result.computeBoundingSphere()
    return result
  },[geometry,grid,floor,detailFloor])
  const imagery = useMemo(() => {
    const texture = sourceImagery.clone()
    texture.colorSpace = SRGBColorSpace
    texture.anisotropy = gl.capabilities.getMaxAnisotropy()
    texture.generateMipmaps = true
    texture.minFilter = LinearMipmapLinearFilter
    texture.needsUpdate = true
    return texture
  }, [sourceImagery,gl])
  const material=useMemo(()=>{
    const result=terrainMaterial({detail:false,shoreline,caustics:false})
    result.map=imagery;result.side=DoubleSide;return result
  },[imagery,shoreline])
  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => () => imagery.dispose(), [imagery])
  useEffect(() => () => walls.dispose(), [walls])
  useEffect(() => () => material.dispose(), [material])
  return <group scale={[1, verticalScale, 1]}><mesh geometry={geometry} material={material} raycast={() => {}} receiveShadow />{quayWalls && <mesh geometry={walls} raycast={() => {}}><meshStandardMaterial color="#717c7b" roughness={.95} side={DoubleSide} /></mesh>}</group>
}
