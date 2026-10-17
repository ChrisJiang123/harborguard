import { useMemo, useRef } from 'react'
import { Html } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import { Object3D } from 'three'
import type { Group, InstancedMesh } from 'three'
import { useShallow } from 'zustand/react/shallow'
import { useHarbor } from '../store/useHarbor'
import { LEVEL_COLORS } from '../theme'
import type { Cls } from '../types/contract'
import { createTrackMotion, sampleTrackMotion } from './coordinates'

function FishSchool({ color }: { color: string }) {
  const mesh = useRef<InstancedMesh>(null)
  const dummy = useMemo(() => new Object3D(), [])
  useFrame(() => {
    if (!mesh.current) return
    const t = useHarbor.getState().latest?.t ?? 0
    for (let i = 0; i < 30; i++) {
      dummy.position.set(Math.sin(i * 2.399) * (3 + i % 6) + Math.sin(t + i) * .3, Math.sin(i * 4.3) * 2 + Math.cos(t * .7 + i) * .2, Math.cos(i * 2.399) * (3 + i % 6))
      dummy.scale.set(.6, .4, 1)
      dummy.rotation.set(0, Math.sin(t * .2 + i) * .3, 0)
      dummy.updateMatrix()
      mesh.current.setMatrixAt(i, dummy.matrix)
    }
    mesh.current.instanceMatrix.needsUpdate = true
  })
  return <instancedMesh ref={mesh} args={[undefined, undefined, 30]} frustumCulled={false}><sphereGeometry args={[.8, 6, 4]} /><meshStandardMaterial color={color} emissive={color} emissiveIntensity={.2} /></instancedMesh>
}

function TargetBody({ cls, color, tentative }: { cls: Cls; color: string; tentative: boolean }) {
  const material = <meshStandardMaterial color={color} emissive={color} emissiveIntensity={.25} roughness={.4} transparent opacity={tentative ? .5 : 1} />
  if (cls === 'fish_school') return <FishSchool color={color} />
  if (cls === 'uuv') return <group><mesh rotation={[Math.PI / 2, 0, 0]}><capsuleGeometry args={[1.2, 7, 4, 12]} />{material}</mesh><mesh position={[0, 1.1, 2]}><boxGeometry args={[.3, 2, 2]} /><meshStandardMaterial color={color} /></mesh><mesh position={[0, 0, -4.1]}><sphereGeometry args={[.6, 8, 6]} /><meshBasicMaterial color="#d6f1ff" /></mesh></group>
  if (cls === 'debris') return <mesh><boxGeometry args={[2.5, 2.5, 2.5]} />{material}</mesh>
  if (cls === 'marine_mammal') return <mesh scale={[1.4, 1, 4]}><sphereGeometry args={[1, 16, 10]} />{material}</mesh>
  if (cls === 'vessel') return <group><mesh><boxGeometry args={[3.2, 1.1, 8.5]} />{material}</mesh><mesh position={[0, 0, -5.6]} rotation={[-Math.PI / 2, 0, 0]}><coneGeometry args={[1.6, 3, 4]} />{material}</mesh><mesh position={[0, 1.25, .7]}><boxGeometry args={[2.1, 1.4, 3]} /><meshStandardMaterial color="#d8e4ec" emissive={color} emissiveIntensity={.15} /></mesh><mesh position={[0, 2.5, .7]}><cylinderGeometry args={[.12, .12, 2.4, 6]} /><meshStandardMaterial color="#cbd5e1" /></mesh></group>
  return <mesh><octahedronGeometry args={[2]} />{material}</mesh>
}

function Target({ id, verticalScale }: { id: string; verticalScale: number }) {
  const cls = useHarbor(s => s.tracks[id]?.cls ?? 'unknown')
  const level = useHarbor(s => s.tracks[id]?.level ?? 0)
  const tentative = useHarbor(s => s.tracks[id]?.status === 'tentative')
  const selected = useHarbor(s => s.selectedTrackId === id)
  const group = useRef<Group>(null)
  const model = useRef<Group>(null)
  const label = useRef<HTMLSpanElement>(null)
  const motion = useMemo(() => createTrackMotion(useHarbor.getState().tracks[id], verticalScale), [id, verticalScale])
  useFrame(({ clock }) => {
    const track = useHarbor.getState().tracks[id]
    if (!track || !group.current) return
    group.current.position.fromArray(sampleTrackMotion(motion, track, clock.elapsedTime, verticalScale))
    if (model.current) model.current.rotation.y = -track.heading_deg * Math.PI / 180
    const text = track.cls === 'vessel' ? `${id} · 船舶 · ${Math.round(track.heading_deg)}°` : `${id} · L${track.level} · ${track.depth_m.toFixed(1)} m`
    if (label.current && label.current.textContent !== text) label.current.textContent = text
  })
  return <group ref={group} onClick={event => { event.stopPropagation(); useHarbor.getState().selectTrack(id) }}>
    <group ref={model} scale={5}><TargetBody cls={cls} color={LEVEL_COLORS[level]} tentative={tentative} /></group>
    {selected && <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -6, 0]} raycast={() => {}}><ringGeometry args={[19, 22, 40]} /><meshBasicMaterial color="#ffffff" transparent opacity={.85} depthWrite={false} side={2} /></mesh>}
    {(selected || level > 0) && <Html position={[0, 32, 0]} center zIndexRange={[40, 0]} pointerEvents="none"><span ref={label} className={`target-3d-label ${selected ? 'selected' : ''}`} style={{ color: LEVEL_COLORS[level] }}>{id}</span></Html>}
  </group>
}

export function Target3D({ verticalScale }: { verticalScale: number }) {
  const ids = useHarbor(useShallow(s => Object.keys(s.tracks)))
  return <group>{ids.map(id => <Target key={id} id={id} verticalScale={verticalScale} />)}</group>
}
