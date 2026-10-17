import { useEffect, useMemo } from 'react'
import { BufferGeometry, Color, DoubleSide, Float32BufferAttribute } from 'three'
import type { BathymetryGrid } from '../data/bathymetry'
import { worldPosition } from './coordinates'

function depthColor(depth: number, minDepth: number, maxDepth: number): Color {
  const stops = [new Color('#b8b08a'), new Color('#4d8f91'), new Color('#245477'), new Color('#102d4d')]
  const normalized = Math.max(0, Math.min(1, (depth - minDepth) / Math.max(1, maxDepth - minDepth)))
  const scaled = normalized * (stops.length - 1)
  const index = Math.min(stops.length - 2, Math.floor(scaled))
  return stops[index]!.clone().lerp(stops[index + 1]!, scaled - index)
}

export function Seabed({ grid, verticalScale }: { grid: BathymetryGrid; verticalScale: number }) {
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
        positions.push(...worldPosition(lat, lon, depth, verticalScale))
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
  }, [grid, verticalScale])
  useEffect(() => () => geometry.dispose(), [geometry])
  return <group>
    <mesh geometry={geometry} raycast={() => {}}><meshStandardMaterial vertexColors roughness={.96} side={DoubleSide} /></mesh>
    <mesh geometry={geometry} position={[0, -.04, 0]} raycast={() => {}}><meshBasicMaterial color="#a8c8d8" wireframe transparent opacity={.08} depthWrite={false} /></mesh>
  </group>
}
