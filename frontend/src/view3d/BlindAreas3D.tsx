import { useMemo } from 'react'
import { Html, Line } from '@react-three/drei'
import { useShallow } from 'zustand/react/shallow'
import { useHarbor } from '../store/useHarbor'
import type { Buoy } from '../types/contract'
import { worldPosition } from './coordinates'

function BlindCircle({ buoy }: { buoy: Buoy }) {
  const center = useMemo(() => { const p = worldPosition(buoy.lat, buoy.lon); p[1] = 6; return p }, [buoy.lat, buoy.lon])
  const stripes = useMemo(() => Array.from({ length: 15 }, (_, index) => {
    const offset = (index - 7) * buoy.range_m / 8
    const half = Math.sqrt(buoy.range_m ** 2 - offset ** 2)
    // Parallel diagonal chords clipped to the coverage circle.
    return [[(offset - half) / Math.SQRT2, 0, (offset + half) / Math.SQRT2], [(offset + half) / Math.SQRT2, 0, (offset - half) / Math.SQRT2]] as [number, number, number][]
  }), [buoy.range_m])
  return <group position={center}>{stripes.map((points, index) => <Line key={index} points={points} color="#9ca3af" transparent opacity={.6} lineWidth={1} raycast={() => {}} />)}<Html center style={{ pointerEvents: 'none' }}><span className="three-zone-label">{buoy.id} 离线 · 潜在盲区</span></Html></group>
}
export function BlindAreas3D() {
  const buoys = useHarbor(useShallow(s => s.latest?.buoys.filter(buoy => buoy.status === 'down') ?? []))
  return <group>{buoys.map(buoy => <BlindCircle key={buoy.id} buoy={buoy} />)}</group>
}
