import { useMemo } from 'react'
import { DoubleSide } from 'three'
import { Html } from '@react-three/drei'
import type { Asset } from '../types/contract'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { LEVEL_COLORS } from '../theme'
import { worldPosition } from './coordinates'

function AssetVolume({ asset, simple, verticalScale, maxDepth }: { asset: Asset; simple: boolean; verticalScale: number; maxDepth: number }) {
  const level = useHarbor(s => Object.values(s.alerts).reduce((max, alert) => alert.asset_id === asset.id ? Math.max(max, alert.level) : max, 0))
  const position = useMemo(() => worldPosition(asset.lat, asset.lon), [asset.lat, asset.lon])
  const height = maxDepth * verticalScale
  return <group position={position}>
    {!simple && asset.rings_m.map((radius, i) => <mesh key={i} position={[0, -height / 2, 0]} raycast={() => {}}><cylinderGeometry args={[radius, radius, height, 64, 1, true]} /><meshBasicMaterial color={LEVEL_COLORS[i + 1]} transparent opacity={level === i + 1 ? .14 : .035} depthWrite={false} side={DoubleSide} /></mesh>)}
    <mesh position={[0, 7, 0]}><boxGeometry args={[24, 14, 24]} /><meshStandardMaterial color="#c1d8e8" emissive="#34566c" emissiveIntensity={.35} /></mesh><Html position={[0, 34, 0]} center zIndexRange={[25, 0]} pointerEvents="none"><span className="asset-3d-label">{asset.name}</span></Html>
  </group>
}
export function AlertVolume({ simple, verticalScale, maxDepth }: { simple: boolean; verticalScale: number; maxDepth: number }) {
  const assets = useMapData(s => s.resources?.assets)
  return <group>{assets?.map(asset => <AssetVolume key={asset.id} asset={asset} simple={simple} verticalScale={verticalScale} maxDepth={maxDepth} />)}</group>
}
