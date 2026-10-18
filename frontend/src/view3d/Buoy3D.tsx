import { useMemo, useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { DoubleSide } from 'three'
import type { Group, Mesh, MeshBasicMaterial } from 'three'
import { useShallow } from 'zustand/react/shallow'
import type { StaticBuoy } from '../data/mapGeometry'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { pingEnvelope, worldPosition } from './coordinates'
import { SceneLabel } from './SceneLabel'
import { proposedSonar } from '../data/sonarDeployment'

function Buoy({ id, baseline, verticalScale }: { id: string; baseline?: StaticBuoy; verticalScale: number }) {
  const proposal = useHarbor(s => {
    const current = s.latest?.buoys.find(buoy => buoy.id === id) ?? baseline
    return current && (s.conn === 'mock' || s.conn === 'replay') ? proposedSonar(current) : undefined
  })
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
  const headY = -(proposal?.head_depth_m ?? 0) * verticalScale
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
    <mesh position={[0, 3, 0]}><cylinderGeometry args={[3, 3, 6, 12]} /><meshStandardMaterial color={status === 'ok' ? '#f9bc49' : '#6B7280'} emissive={color} emissiveIntensity={.4} /></mesh><mesh position={[0, 9, 0]}><cylinderGeometry args={[.45, .45, 8, 8]} /><meshStandardMaterial color="#f8fafc" /></mesh><mesh position={[0, 13, 0]}><sphereGeometry args={[1.3, 10, 8]} /><meshStandardMaterial color={color} emissive={color} emissiveIntensity={.7} /></mesh>
    {proposal && <><mesh position={[0,headY/2,0]} raycast={() => {}}><cylinderGeometry args={[.3,.3,-headY,6]} /><meshStandardMaterial color="#879eab" /></mesh><mesh position={[0,headY,0]}><cylinderGeometry args={[2.5,2.5,2.5,12]} /><meshStandardMaterial color={color} emissive={color} emissiveIntensity={.5} /></mesh><SceneLabel position={[0,headY-4,0]} text={`${id} sonar · 3 m (proposed)`} color="#88cce8" borderColor="#294d66" importance="low" maxDistance={1000} pixelHeight={13} /></>}
    <mesh position={[0,headY,0]} rotation={[-Math.PI/2,0,0]} raycast={() => {}}><ringGeometry args={[Math.max(0,range-1.5),range,96]} /><meshBasicMaterial color={color} transparent opacity={status === 'ok' ? .22 : .04} depthWrite={false} side={DoubleSide} /></mesh>
    <group position={[0,headY,0]}><mesh ref={wave} visible={false} raycast={() => {}}><sphereGeometry args={[1, 24, 12]} /><meshBasicMaterial ref={waveMaterial} color="#7dd3fc" transparent wireframe opacity={0} depthWrite={false} /></mesh></group>
    <SceneLabel position={[0, 22, 0]} text={`${id}${status === 'down' ? ' ×' : status === 'pending' ? ' · Connecting' : ''}`} color={status === 'ok' ? '#7bd0f2' : '#a0aabd'} borderColor={status === 'ok' ? '#2b5c77' : '#4a5365'} pixelHeight={16} maxDistance={3200} importance={status === 'down' ? 'high' : 'low'} />
  </group>
}
export function Buoy3D({ verticalScale }: { verticalScale: number; maxDepth?: number }) {
  const ids = useHarbor(useShallow(s => (s.latest?.buoys ?? []).map(buoy => buoy.id)))
  const baseline = useMapData(s => s.resources?.buoys)
  const combined = useMemo(() => [...new Set([...(baseline ?? []).map(buoy => buoy.id), ...ids])], [ids, baseline])
  return <group>{combined.map(id => <Buoy key={id} id={id} baseline={baseline?.find(buoy => buoy.id === id)} verticalScale={verticalScale} />)}</group>
}
