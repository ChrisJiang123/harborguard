import { useEffect, useMemo } from 'react'
import { BufferGeometry, Color, DoubleSide, Float32BufferAttribute } from 'three'
import type { BathymetryBounds, BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'
import { buildBathymetryContours } from './seabedContours'
import { buildSeabedMeshData, surveyEdgeFade } from './seabedMesh'
import { stitchedHeightfieldNormals } from './heightfield'
import { DEFAULT_TERRAIN_EFFECTS, terrainMaterial } from './terrainMaterial'
import type { TerrainEffects } from './terrainMaterial'
import { stitchTerrainBoundary } from './stitchTerrain'

const stops = [new Color('#b8b08a'), new Color('#4d8f91'), new Color('#245477'), new Color('#102d4d')]
function depthColor(depth: number, minDepth: number, maxDepth: number, color: Color): Color {
  const normalized = Math.max(0, Math.min(1, (depth - minDepth) / Math.max(1, maxDepth - minDepth)))
  const scaled = normalized * (stops.length - 1)
  const index = Math.min(stops.length - 2, Math.floor(scaled))
  return color.copy(stops[index]!).lerp(stops[index + 1]!, scaled - index)
}

export function Seabed({ grid, verticalScale, refinement = 2, showSurface = true, showContours = true, excludeBounds, colorRange, softEdges = true, effects = DEFAULT_TERRAIN_EFFECTS, stitchTo, normalGrid }: { grid: BathymetryGrid; verticalScale: number; refinement?: 1 | 2; showSurface?: boolean; showContours?: boolean; excludeBounds?: BathymetryBounds; colorRange?: { min_depth_m: number; max_depth_m: number }; softEdges?: boolean; effects?: TerrainEffects; stitchTo?: BathymetryGrid; normalGrid?: BathymetryGrid | null }) {
  const geometry = useMemo(() => {
    const result = new BufferGeometry()
    const { min_depth_m, max_depth_m } = colorRange ?? grid.metadata
    const base = buildSeabedMeshData(grid, refinement, excludeBounds)
    const { positions, depths, indices, columns, rows } = stitchTo ? stitchTerrainBoundary(base, grid, stitchTo) : base
    const opacity = surveyEdgeFade(depths,columns,rows, grid.metadata.approximate_spacing_m.east_west, grid.metadata.approximate_spacing_m.north_south)
    const colors = new Float32Array(depths.length * 4)
    const color = new Color()
    for (let i = 0; i < depths.length; i++) {
      const depth = depths[i]!
      if (Number.isFinite(depth)) depthColor(depth, min_depth_m, max_depth_m, color)
      else color.set('#172838')
      colors[i*4] = color.r; colors[i*4+1] = color.g; colors[i*4+2] = color.b; colors[i*4+3] = i < columns*rows ? opacity[i]! : 1
    }
    result.setAttribute('position', new Float32BufferAttribute(positions, 3))
    result.setAttribute('color', new Float32BufferAttribute(colors, 4))
    result.setIndex(indices)
    const nw = worldPosition(grid.metadata.bounds.north, grid.metadata.bounds.west)
    const se = worldPosition(grid.metadata.bounds.south, grid.metadata.bounds.east)
    // In composite mode the lighting samples the same display field as fill,
    // avoiding a normal discontinuity at the coverage edge. Survey POSITIONS
    // and indices remain source-supported and unchanged by this lighting field.
    const heights=normalGrid && base.factor===1 ? Float32Array.from(normalGrid.values,v=>v===normalGrid.metadata.nodata_value?NaN:-v) : depths.map(v=>-v)
    const normals=stitchedHeightfieldNormals(heights,columns,rows,(se[0]-nw[0])/(columns-1),(se[2]-nw[2])/(rows-1),positions,stitchTo)
    result.setAttribute('normal', new Float32BufferAttribute(normals, 3))
    result.computeBoundingSphere()
    return result
  }, [grid, refinement, excludeBounds, colorRange, stitchTo, normalGrid])
  const material = useMemo(() => {
    const result = terrainMaterial(effects)
    result.side = DoubleSide
    result.alphaToCoverage = softEdges
    return result
  }, [effects, softEdges])
  useEffect(() => () => material.dispose(), [material])
  const contours = useMemo(() => {
    const minor: number[] = [], major: number[] = []
    for (const segment of showContours ? buildBathymetryContours(grid, refinement === 2 ? 2 : 5, excludeBounds) : []) {
      const target = Math.abs(segment.depth % 10) < .001 ? major : minor
      const from = worldPosition(segment.from.lat, segment.from.lon, segment.depth, 1)
      const to = worldPosition(segment.to.lat, segment.to.lon, segment.depth, 1)
      from[1] += .15; to[1] += .15
      target.push(...from, ...to)
    }
    const make = (positions: number[]) => {
      const result = new BufferGeometry()
      result.setAttribute('position', new Float32BufferAttribute(positions, 3))
      result.computeBoundingSphere()
      return result
    }
    return { minor: make(minor), major: make(major) }
  }, [grid, refinement, excludeBounds, showContours])
  useEffect(() => () => geometry.dispose(), [geometry])
  useEffect(() => () => { contours.minor.dispose(); contours.major.dispose() }, [contours])
  return <group scale={[1, verticalScale, 1]}>
    {showSurface && <mesh geometry={geometry} material={material} raycast={() => {}} />}
    {showContours && <><lineSegments geometry={contours.minor} raycast={() => {}} renderOrder={5}><lineBasicMaterial color="#9bd8e5" transparent opacity={.16} depthWrite={false} /></lineSegments><lineSegments geometry={contours.major} raycast={() => {}} renderOrder={6}><lineBasicMaterial color="#d8f3f7" transparent opacity={.28} depthWrite={false} /></lineSegments></>}
  </group>
}
