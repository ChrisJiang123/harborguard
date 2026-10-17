import { useEffect, useMemo } from 'react'
import { BufferGeometry, Color, DoubleSide, Float32BufferAttribute } from 'three'
import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'
import { buildBathymetryContours } from './seabedContours'

function depthColor(depth: number, minDepth: number, maxDepth: number): Color {
  const stops = [new Color('#b8b08a'), new Color('#4d8f91'), new Color('#245477'), new Color('#102d4d')]
  const normalized = Math.max(0, Math.min(1, (depth - minDepth) / Math.max(1, maxDepth - minDepth)))
  const scaled = normalized * (stops.length - 1)
  const index = Math.min(stops.length - 2, Math.floor(scaled))
  return stops[index]!.clone().lerp(stops[index + 1]!, scaled - index)
}

export function Seabed({ grid, verticalScale, showSurface = true, showContours = true }: { grid: BathymetryGrid; verticalScale: number; showSurface?: boolean; showContours?: boolean }) {
  const geometry = useMemo(() => {
    const result = new BufferGeometry()
    const { width, height, bounds, nodata_value, min_depth_m, max_depth_m } = grid.metadata
    const positions: number[] = []
    const colors: number[] = []
    const indices: number[] = []
    for (let row = 0; row < height; row++) {
      const lat = bounds.north - row / (height - 1) * (bounds.north - bounds.south)
      for (let column = 0; column < width; column++) {
        const lon = bounds.west + column / (width - 1) * (bounds.east - bounds.west)
        const raw = grid.values[row * width + column]!
        const depth = raw === nodata_value ? max_depth_m : raw
        positions.push(...worldPosition(lat, lon, depth, 1))
        const color = raw === nodata_value ? new Color('#172838') : depthColor(depth, min_depth_m, max_depth_m)
        colors.push(color.r, color.g, color.b)
      }
    }
    for (let row = 0; row < height - 1; row++) {
      for (let column = 0; column < width - 1; column++) {
        const a = row * width + column
        const b = a + 1
        const c = a + width
        const d = c + 1
        if ([a, b, c, d].some(index => grid.values[index] === nodata_value)) continue
        indices.push(a, c, b, b, c, d)
      }
    }
    result.setAttribute('position', new Float32BufferAttribute(positions, 3))
    result.setAttribute('color', new Float32BufferAttribute(colors, 3))
    result.setIndex(indices)
    result.computeVertexNormals()
    result.computeBoundingSphere()
    return result
  }, [grid])
  const contours = useMemo(() => {
    const minor: number[] = [], major: number[] = []
    for (const segment of buildBathymetryContours(grid)) {
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
  }, [grid])
  useEffect(() => () => { geometry.dispose(); contours.minor.dispose(); contours.major.dispose() }, [geometry, contours])
  return <group scale={[1, verticalScale, 1]}>
    {showSurface && <><mesh geometry={geometry} raycast={() => {}}><meshStandardMaterial vertexColors roughness={.96} side={DoubleSide} /></mesh><mesh geometry={geometry} position={[0, -.04, 0]} raycast={() => {}}><meshBasicMaterial color="#a8c8d8" wireframe transparent opacity={.055} depthWrite={false} /></mesh></>}
    {showContours && <><lineSegments geometry={contours.minor} raycast={() => {}} renderOrder={5}><lineBasicMaterial color="#9bd8e5" transparent opacity={.38} depthWrite={false} /></lineSegments><lineSegments geometry={contours.major} raycast={() => {}} renderOrder={6}><lineBasicMaterial color="#d8f3f7" transparent opacity={.62} depthWrite={false} /></lineSegments></>}
  </group>
}
