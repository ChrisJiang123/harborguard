import { DoubleSide } from 'three'
import type { SceneBounds } from './coordinates'

export function Water({ bounds }: { bounds: SceneBounds }) {
  const size = Math.max(8000, bounds.span * 2.2)
  return <group position={[bounds.center[0], 0, bounds.center[2]]}><mesh rotation={[-Math.PI / 2, 0, 0]} renderOrder={2} raycast={() => {}}><planeGeometry args={[size, size]} /><meshStandardMaterial color="#177cb1" transparent opacity={.25} roughness={.5} metalness={.1} depthWrite={false} side={DoubleSide} /></mesh><gridHelper args={[size, 32, '#27506d', '#19364b']} position={[0, .5, 0]} raycast={() => {}} /></group>
}
