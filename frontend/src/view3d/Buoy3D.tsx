import { useMemo, useRef } from 'react'
import { Html } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { DoubleSide } from 'three'
import type { Group, Mesh, MeshBasicMaterial } from 'three'
import { useShallow } from 'zustand/react/shallow'
import type { StaticBuoy } from '../data/mapGeometry'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { SEABED_DEPTH_M, VZ } from '../theme'
import { pingEnvelope, worldPosition } from './coordinates'

function Buoy({ id, baseline }: { id: string; baseline?: StaticBuoy }) {
  const status = useHarbor(s => s.latest?.buoys.find(buoy => buoy.id === id)?.status ?? 'pending')
  const range = useHarbor(s => s.latest?.buoys.find(buoy => buoy.id === id)?.range_m ?? baseline?.range_m ?? 650)
  const initial = useMemo(() => {
    const buoy = useHarbor.getState().latest?.buoys.find(item => item.id === id) ?? baseline
    return buoy ? worldPosition(buoy.lat, buoy.lon) : [0, 0, 0] as [number, number, number]
  }, [id, baseline])
  const group = useRef<Group>(null)
  const wave = useRef<Mesh>(null)
  const waveMaterial = useRef<MeshBasicMaterial>(null)
  const pulse = useRef({ previous: false, at: -Infinity, lat: NaN, lon: NaN })
  const color = status === 'ok' ? '#38bdf8' : '#6B7280'
  const height = SEABED_DEPTH_M * VZ
  useFrame(({ clock }) => {
    const buoy = useHarbor.getState().latest?.buoys.find(item => item.id === id)
    const current = buoy ?? baseline
    if (!current || !group.current) return
    if (pulse.current.lat !== current.lat || pulse.current.lon !== current.lon) {
      group.current.position.fromArray(worldPosition(current.lat, current.lon))
      pulse.current.lat = current.lat; pulse.current.lon = current.lon
    }
    const pinging = !!buoy?.pinging && buoy.status === 'ok'
    if (pinging && !pulse.current.previous) pulse.current.at = clock.elapsedTime
    pulse.current.previous = pinging
    if (wave.current && waveMaterial.current) {
      const envelope = pingEnvelope(clock.elapsedTime - pulse.current.at, range)
      wave.current.visible = envelope.opacity > 0 && buoy?.status === 'ok'
      wave.current.scale.setScalar(envelope.radius)
      waveMaterial.current.opacity = envelope.opacity
    }
  })
  return <group ref={group} position={initial}>
    <mesh position={[0, 3, 0]}><cylinderGeometry args={[3, 3, 6, 12]} /><meshStandardMaterial color={status === 'ok' ? '#f9bc49' : '#6B7280'} emissive={color} emissiveIntensity={.4} /></mesh>
    <mesh position={[0, -height / 2, 0]} raycast={() => {}}><coneGeometry args={[range, height, 32, 1, true]} /><meshBasicMaterial color={color} transparent opacity={status === 'ok' ? .12 : .025} depthWrite={false} side={DoubleSide} /></mesh>
    <mesh ref={wave} visible={false} raycast={() => {}}><sphereGeometry args={[1, 24, 12]} /><meshBasicMaterial ref={waveMaterial} color="#7dd3fc" transparent wireframe opacity={0} depthWrite={false} /></mesh>
    <Html position={[0, 22, 0]} center zIndexRange={[20, 0]} pointerEvents="none"><span className={`buoy-3d-label ${status}`}>{id}{status === 'down' ? ' ×' : status === 'pending' ? ' · 待连接' : ''}</span></Html>
  </group>
}
export function Buoy3D() {
  const ids = useHarbor(useShallow(s => (s.latest?.buoys ?? []).map(buoy => buoy.id)))
  const baseline = useMapData(s => s.resources?.buoys)
  const combined = useMemo(() => [...new Set([...(baseline ?? []).map(buoy => buoy.id), ...ids])], [ids, baseline])
  return <group>{combined.map(id => <Buoy key={id} id={id} baseline={baseline?.find(buoy => buoy.id === id)} />)}</group>
}
