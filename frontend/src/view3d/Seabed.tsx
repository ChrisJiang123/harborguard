import { useEffect, useMemo } from 'react'
import { BufferGeometry, Color, DoubleSide, Float32BufferAttribute } from 'three'
import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'
import { buildBathymetryContours } from './seabedContours'
import { buildSeabedMeshData } from './seabedMesh'

const stops = [new Color('#b8b08a'), new Color('#4d8f91'), new Color('#245477'), new Color('#102d4d')]
function depthColor(depth: number, minDepth: number, maxDepth: number, color: Color): Color {
  const normalized = Math.max(0, Math.min(1, (depth - minDepth) / Math.max(1, maxDepth - minDepth)))
  const scaled = normalized * (stops.length - 1)
  const index = Math.min(stops.length - 2, Math.floor(scaled))
  return color.copy(stops[index]!).lerp(stops[index + 1]!, scaled - index)
}

export function Seabed({ grid, verticalScale, refinement = 2, showSurface = true, showContours = true }: { grid: BathymetryGrid; verticalScale: number; refinement?: 1 | 2; showSurface?: boolean; showContours?: boolean }) {
  const geometry = useMemo(() => {
    const result = new BufferGeometry()
    const { min_depth_m, max_depth_m } = grid.metadata
    const { positions, depths, indices } = buildSeabedMeshData(grid, refinement)
    const colors = new Float32Array(depths.length * 3)
    const color = new Color()
    for (let i = 0; i < depths.length; i++) {
      const depth = depths[i]!
      if (Number.isFinite(depth)) depthColor(depth, min_depth_m, max_depth_m, color)
      else color.set('#172838')
      colors.set([color.r, color.g, color.b], i * 3)
    }
    result.setAttribute('position', new Float32BufferAttribute(positions, 3))
    result.setAttribute('color', new Float32BufferAttribute(colors, 3))
    result.setIndex(indices)
    result.computeVertexNormals()
    result.computeBoundingSphere()
    return result
  }, [grid, refinement])
  const contours = useMemo(() => {
    const minor: number[] = [], major: number[] = []
    for (const segment of buildBathymetryContours(grid, refinement === 2 ? 2 : 5)) {
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
  }, [grid, refinement])
  useEffect(() => () => { geometry.dispose(); contours.minor.dispose(); contours.major.dispose() }, [geometry, contours])
  return <group scale={[1, verticalScale, 1]}>
    {showSurface && <mesh geometry={geometry} raycast={() => {}}><meshStandardMaterial vertexColors roughness={.96} side={DoubleSide} /></mesh>}
    {showContours && <><lineSegments geometry={contours.minor} raycast={() => {}} renderOrder={5}><lineBasicMaterial color="#9bd8e5" transparent opacity={.38} depthWrite={false} /></lineSegments><lineSegments geometry={contours.major} raycast={() => {}} renderOrder={6}><lineBasicMaterial color="#d8f3f7" transparent opacity={.62} depthWrite={false} /></lineSegments></>}
  </group>
}
