import { useEffect, useMemo } from 'react'
import { DoubleSide, PlaneGeometry } from 'three'
import { seabedElevation } from './coordinates'
import type { SceneBounds } from './coordinates'

export function Seabed({ bounds }: { bounds: SceneBounds }) {
  const geometry = useMemo(() => {
    const size = Math.max(8000, bounds.span * 2.2)
    const plane = new PlaneGeometry(size, size, 48, 48)
    plane.rotateX(-Math.PI / 2)
    const points = plane.attributes.position!
    for (let i = 0; i < points.count; i++) points.setY(i, seabedElevation(points.getX(i) + bounds.center[0], points.getZ(i) + bounds.center[2]))
    points.needsUpdate = true
    plane.computeVertexNormals()
    return plane
  }, [bounds])
  useEffect(() => () => geometry.dispose(), [geometry])
  return <mesh geometry={geometry} position={[bounds.center[0], 0, bounds.center[2]]} raycast={() => {}}><meshStandardMaterial color="#574b38" roughness={1} side={DoubleSide} /></mesh>
}
