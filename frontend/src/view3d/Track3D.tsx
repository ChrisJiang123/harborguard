import { useMemo, useRef } from 'react'
import { Line } from '@react-three/drei'
import { useFrame } from '@react-three/fiber'
import type { Line2 } from 'three-stdlib'
import type { Group } from 'three'
import { useShallow } from 'zustand/react/shallow'
import { useHarbor } from '../store/useHarbor'
import { LEVEL_COLORS } from '../theme'
import { createTrackMotion, HISTORY_CAPACITY, PREDICTED_CAPACITY, sampleTrackMotion, worldPosition } from './coordinates'
import type { Point3 } from './coordinates'
import type { Track } from '../types/contract'
import { updateLine } from './lineBuffers'

const blank = (count: number): Point3[] => Array.from({ length: count }, () => [0, 0, 0])
function Trail({ id }: { id: string }) {
  const level = useHarbor(s => s.tracks[id]?.level ?? 0)
  const tentative = useHarbor(s => s.tracks[id]?.status === 'tentative')
  const selected = useHarbor(s => s.selectedTrackId === id)
  const historyLine = useRef<Line2>(null)
  const predictionLine = useRef<Line2>(null)
  const projectionLine = useRef<Line2>(null)
  const surfaceRing = useRef<Group>(null)
  const previous = useRef<Track | null>(null)
  const historyPoints = useMemo(() => blank(HISTORY_CAPACITY), [])
  const predictionPoints = useMemo(() => blank(PREDICTED_CAPACITY), [])
  const projectionPoints = useMemo(() => blank(2), [])
  const motion = useMemo(() => createTrackMotion(useHarbor.getState().tracks[id]), [id])
  const vertical = useRef(blank(2))
  useFrame(({ clock }) => {
    const track = useHarbor.getState().tracks[id]
    if (!track) return
    if (track !== previous.current) {
      updateLine(historyLine.current, track.history.slice(-HISTORY_CAPACITY).map(point => worldPosition(point[0], point[1], point[2])))
      updateLine(predictionLine.current, [worldPosition(track.lat, track.lon, track.depth_m), ...track.predicted.slice(0, PREDICTED_CAPACITY - 1).map(point => worldPosition(point[0], point[1], point[2]))])
      previous.current = track
    }
    const position = sampleTrackMotion(motion, track, clock.elapsedTime)
    const points = vertical.current
    points[0]![0] = position[0]; points[0]![1] = position[1]; points[0]![2] = position[2]
    points[1]![0] = position[0]; points[1]![1] = 1; points[1]![2] = position[2]
    updateLine(projectionLine.current, points)
    surfaceRing.current?.position.set(position[0], 1, position[2])
  })
  return <group>
    <Line ref={historyLine} points={historyPoints} color={LEVEL_COLORS[level]} lineWidth={selected ? 2.5 : 1.5} transparent opacity={tentative ? .4 : .85} frustumCulled={false} raycast={() => {}} />
    <Line ref={predictionLine} points={predictionPoints} color={LEVEL_COLORS[level]} lineWidth={1.3} dashed dashSize={35} gapSize={25} transparent opacity={tentative ? .25 : .65} frustumCulled={false} raycast={() => {}} />
    <Line ref={projectionLine} points={projectionPoints} color="#82b9d8" lineWidth={1} dashed dashSize={10} gapSize={8} transparent opacity={.55} frustumCulled={false} raycast={() => {}} />
    <group ref={surfaceRing}><mesh rotation={[-Math.PI / 2, 0, 0]} raycast={() => {}}><ringGeometry args={[13, 16, 32]} /><meshBasicMaterial color={LEVEL_COLORS[level]} transparent opacity={.8} depthWrite={false} side={2} /></mesh></group>
  </group>
}
export function Track3D() {
  const ids = useHarbor(useShallow(s => Object.keys(s.tracks)))
  return <group>{ids.map(id => <Trail key={id} id={id} />)}</group>
}
