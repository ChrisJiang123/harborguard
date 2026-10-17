import { DoubleSide } from 'three'
import type { SceneBounds } from './coordinates'

export function Water({ bounds, opacity }: { bounds: SceneBounds; opacity: number }) {
  const size = Math.max(8000, bounds.span * 2.2)
  return <group position={[bounds.center[0], 0, bounds.center[2]]}><mesh rotation={[-Math.PI / 2, 0, 0]} renderOrder={2} raycast={() => {}}><planeGeometry args={[size, size]} /><meshStandardMaterial color="#1680b2" transparent opacity={opacity} roughness={.45} metalness={.08} depthWrite={false} side={DoubleSide} /></mesh><gridHelper args={[size, 32, '#65b9d6', '#24536c']} position={[0, .3, 0]} raycast={() => {}} /></group>
}
