import { useEffect, useMemo } from 'react'
import { useTexture } from '@react-three/drei'
import { useThree } from '@react-three/fiber'
import { BufferGeometry, Color, DoubleSide, Float32BufferAttribute, LinearMipmapLinearFilter, MeshStandardMaterial, SRGBColorSpace } from 'three'
import type { ShoreTerrainGrid } from '../data/shoreTerrain'
import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'
import { heightfieldNormals, smoothRegionalHeights } from './heightfield'
import { quayFloorSampler } from './quayClosure'
import { terrainMaterial } from './terrainMaterial'
import { coastalBoundary } from './coastalBoundary'

const COLOR_STOPS = [new Color('#c4b48e'), new Color('#a7a982'), new Color('#718c70'), new Color('#536f63'), new Color('#7c7669')]
const WHITE = new Color('#ffffff')
const BLACK = new Color('#000000')

function heightColor(height: number, minimum: number, maximum: number): Color {
  const p = Math.max(0, Math.min(1, (height - minimum) / Math.max(1, maximum - minimum)))
  const scaled = Math.pow(p, .46) * (COLOR_STOPS.length - 1)
  const index = Math.min(COLOR_STOPS.length - 2, Math.floor(scaled))
  return COLOR_STOPS[index]!.clone().lerp(COLOR_STOPS[index + 1]!, scaled - index).lerp(WHITE, .86)
}
export function CoastalTerrain3D({ grid, verticalScale, quayWalls = true, smoothing = true, coastSmoothing = true, shoreline = true, floor, detailFloor }: { grid: ShoreTerrainGrid; verticalScale: number; quayWalls?: boolean; smoothing?: boolean; coastSmoothing?: boolean; shoreline?: boolean; floor?: BathymetryGrid | null; detailFloor?: BathymetryGrid | null }) {
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
    const validMask = Uint8Array.from(grid.values, value => value !== nodata_value ? 1 : 0)
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
    // Reconstruct the coarse model mask's outline, separately from elevations.
    // This is a bounded (10 m) display approximation, not a surveyed shoreline.
    result.userData.coastEdges = coastalBoundary(positions, validMask, width, height, coastSmoothing ? 10 : 0)
    const nw = worldPosition(bounds.north, bounds.west), se = worldPosition(bounds.south, bounds.east)
    const imageBounds = grid.metadata.imagery_bounds ?? bounds
    for (let i = 0; i < width * height; i++) {
      const lon = bounds.west + (positions[i * 3]! - nw[0]) / (se[0] - nw[0]) * (bounds.east - bounds.west)
      const lat = bounds.north - (positions[i * 3 + 2]! - nw[2]) / (se[2] - nw[2]) * (bounds.north - bounds.south)
      uvs[i * 2] = (lon - imageBounds.west) / (imageBounds.east - imageBounds.west)
      uvs[i * 2 + 1] = (lat - imageBounds.south) / (imageBounds.north - imageBounds.south)
    }
    result.setAttribute('position', new Float32BufferAttribute(positions, 3))
    result.setAttribute('color', new Float32BufferAttribute(colors, 3))
    result.setAttribute('uv', new Float32BufferAttribute(uvs, 2))
    result.setIndex(indices)
    result.setAttribute('normal', new Float32BufferAttribute(heightfieldNormals(elevations,width,height,(se[0]-nw[0])/(width-1),(se[2]-nw[2])/(height-1)),3))
    result.computeBoundingSphere()
    return result
  }, [grid, smoothing, coastSmoothing])
  const walls = useMemo(() => {
    const positions: number[] = [], indices: number[] = [], normals: number[] = []
    const colors: number[] = [], apronIndices: number[] = []
    const shallow = new Color('#669c99'), deep = new Color('#173c5a'), color = new Color()
    const surface = geometry.getAttribute('position')
    const coastEdges = geometry.userData.coastEdges as [number,number][]
    const next = new Map(coastEdges), previous = new Map(coastEdges.map(([a,b]) => [b,a]))
    const normalCache = new Map<number,[number,number,number]>()
    const edgeNormal = (i: number): [number,number,number] => {
      const cached = normalCache.get(i)
      if(cached) return cached
      let a=i,b=i
      // Shared contour tangents keep the many short closure panels from being
      // lit as separate alternating teeth. This changes lighting only.
      for(let k=0;k<4;k++) { a=previous.get(a)??a; b=next.get(b)??b }
      if (Math.hypot(surface.getX(b)-surface.getX(a),surface.getZ(b)-surface.getZ(a)) < .001) {
        a=previous.get(i)??i; b=next.get(i)??i
      }
      const dx=surface.getX(b)-surface.getX(a),dz=surface.getZ(b)-surface.getZ(a),length=Math.hypot(dx,dz)||1
      const normal:[number,number,number]=[dz/length,0,-dx/length]
      normalCache.set(i,normal); return normal
    }
    const sampleFloor=floor?quayFloorSampler(floor):null, sampleDetail=detailFloor?quayFloorSampler(detailFloor):null
    const floorCache=new Map<number,[number,number,number]|null>()
    const atFloor=(i:number) => {
      if(floorCache.has(i)) return floorCache.get(i)
      const x=surface.getX(i),z=surface.getZ(i),point=sampleDetail?.(x,z)??sampleFloor?.(x,z)??null
      floorCache.set(i,point);return point
    }
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
      const n = positions.length/3, dx=pb[0]-pa[0], dz=pb[2]-pa[2], length=Math.hypot(dx,dz)
      if (length < .001) return
      // Vertical panels share the reconstructed land outline. Never snap their
      // visible lower edge sideways to independent, nearest raster vertices:
      // that makes alternating triangular fans and corrugated lighting.
      positions.push(...pa,...pb,pa[0],reserve,pa[2],pb[0],reserve,pb[2])
      indices.push(n,n+2,n+1,n+1,n+2,n+3)
      for(const i of [a,b,a,b]) { normals.push(...edgeNormal(i)); colors.push(1,1,1) }
      // An illustrative submerged apron closes the unsupported last raster
      // width. Its far edge is below the supported floor, which occludes it.
      // It carries no contours and is never labelled as measured bathymetry.
      positions.push(pa[0],fa[1],pa[2],pb[0],fb[1],pb[2],fa[0],reserve,fa[2],fb[0],reserve,fb[2])
      apronIndices.push(n+4,n+6,n+5,n+5,n+6,n+7)
      for(let k=0;k<4;k++) {
        normals.push(0,1,0)
        color.copy(shallow).lerp(deep,Math.min(1,Math.max(0,-(k%2?fb[1]:fa[1])/35)))
        colors.push(color.r,color.g,color.b)
      }
    }
    for (const [a,b] of coastEdges) edge(a,b)
    const result = new BufferGeometry()
    result.setAttribute('position',new Float32BufferAttribute(positions,3)); result.setIndex([...indices,...apronIndices])
    result.setAttribute('color',new Float32BufferAttribute(colors,3))
    result.addGroup(0,indices.length,0); result.addGroup(indices.length,apronIndices.length,1)
    result.setAttribute('normal',new Float32BufferAttribute(normals,3)); result.computeBoundingSphere()
    return result
  },[geometry,floor,detailFloor])
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
  const wallMaterials = useMemo(() => {
    const apron = terrainMaterial({detail:false,shoreline:false,caustics:false},true)
    apron.side = DoubleSide
    return [new MeshStandardMaterial({color:'#717c7b',roughness:.95,side:DoubleSide}),apron]
  },[])
  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => () => imagery.dispose(), [imagery])
  useEffect(() => () => walls.dispose(), [walls])
  useEffect(() => () => material.dispose(), [material])
  useEffect(() => () => wallMaterials.forEach(value => value.dispose()), [wallMaterials])
  return <group scale={[1, verticalScale, 1]}><mesh geometry={geometry} material={material} raycast={() => {}} receiveShadow />{quayWalls && <mesh geometry={walls} material={wallMaterials} raycast={() => {}} />}</group>
}
