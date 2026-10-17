import { useEffect, useMemo } from 'react'
import { BufferGeometry, DoubleSide, Float32BufferAttribute } from 'three'
import type { BathymetryGrid } from '../data/bathymetry'
import type { SceneBounds } from './coordinates'
import { buildWaterSurfaceData } from './waterMask'

function buildWaterMask(grid: BathymetryGrid) {
  const { positions, indices } = buildWaterSurfaceData(grid)
  const geometry = new BufferGeometry()
  geometry.setAttribute('position', new Float32BufferAttribute(positions, 3))
  geometry.setIndex(indices)
  geometry.computeVertexNormals()
  geometry.computeBoundingSphere()
  return geometry
}

export function Water({ bounds, opacity, grid }: { bounds: SceneBounds; opacity: number; grid: BathymetryGrid | null }) {
  const mask = useMemo(() => grid && grid.metadata.source_kind !== 'synthetic' ? buildWaterMask(grid) : null, [grid])
  useEffect(() => () => mask?.dispose(), [mask])
  const size = Math.max(8000, bounds.span * 2.2)
  return mask
    ? <mesh geometry={mask} position={[0, .02, 0]} renderOrder={2} raycast={() => {}}><meshStandardMaterial color="#1680b2" transparent opacity={opacity} roughness={.45} metalness={.08} depthWrite={false} side={DoubleSide} /></mesh>
    : <group position={[bounds.center[0], 0, bounds.center[2]]}><mesh rotation={[-Math.PI / 2, 0, 0]} renderOrder={2} raycast={() => {}}><planeGeometry args={[size, size]} /><meshStandardMaterial color="#1680b2" transparent opacity={opacity} roughness={.45} metalness={.08} depthWrite={false} side={DoubleSide} /></mesh><gridHelper args={[size, 32, '#65b9d6', '#24536c']} position={[0, .3, 0]} raycast={() => {}} /></group>
}
