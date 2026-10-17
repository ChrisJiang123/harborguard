import { useEffect, useMemo, useState } from 'react'
import { BufferGeometry, Float32BufferAttribute } from 'three'
import { loadLocalBase } from '../data/localBase'
import type { LocalBase } from '../data/localBase'
import { useMapData } from '../store/useMapData'
import { worldPosition, zoneCenter, zoneExtent } from './coordinates'

function Crane({ position, rotation = 0 }: { position: [number, number, number]; rotation?: number }) {
  return <group position={position} rotation={[0, rotation, 0]}>
    <mesh position={[0, 30, 0]}><boxGeometry args={[5, 60, 5]} /><meshStandardMaterial color="#e7edf2" roughness={.8} /></mesh>
    <mesh position={[24, 58, 0]}><boxGeometry args={[52, 4, 4]} /><meshStandardMaterial color="#f4f7f9" roughness={.75} /></mesh>
    <mesh position={[48, 39, 0]}><boxGeometry args={[1.2, 38, 1.2]} /><meshStandardMaterial color="#cbd5dc" /></mesh>
    <mesh position={[-7, 8, 0]} rotation={[0, 0, -.28]}><boxGeometry args={[4, 46, 4]} /><meshStandardMaterial color="#dce5ea" /></mesh>
  </group>
}

function Shoreline({ data }: { data: LocalBase }) {
  const geometry = useMemo(() => {
    const positions: number[] = []
    data.features.filter(feature => feature.properties.kind === 'coastline' || feature.properties.kind === 'breakwater' || feature.properties.kind === 'pier').forEach(feature => {
      const coordinates = feature.geometry.coordinates
      for (let i = 1; i < coordinates.length; i++) {
        const previous = coordinates[i - 1]!, current = coordinates[i]!
        const a = worldPosition(previous[1]!, previous[0]!), b = worldPosition(current[1]!, current[0]!)
        positions.push(a[0], 2.4, a[2], b[0], 2.4, b[2])
      }
    })
    const result = new BufferGeometry()
    result.setAttribute('position', new Float32BufferAttribute(positions, 3))
    return result
  }, [data])
  useEffect(() => () => geometry.dispose(), [geometry])
  return <lineSegments geometry={geometry} raycast={() => {}}><lineBasicMaterial color="#dde6ea" transparent opacity={.82} /></lineSegments>
}

export function HarborModels3D() {
  const resources = useMapData(s => s.resources)
  const [base, setBase] = useState<LocalBase | null>(null)
  useEffect(() => { let active = true; void loadLocalBase().then(data => { if (active) setBase(data) }).catch(() => {}); return () => { active = false } }, [])
  const berths = resources?.zones.features.filter(feature => feature.properties.kind === 'berth').slice(0, 6) ?? []
  return <group>
    {base && <Shoreline data={base} />}
    {berths.map((feature, index) => {
      const center = zoneCenter(feature, 4)
      const extent = zoneExtent(feature)
      const width = Math.max(90, Math.min(520, extent.width * .72)), length = Math.max(120, Math.min(720, extent.length * .72))
      return <group key={feature.properties.id} position={center}>
        <mesh position={[0, -2.5, 0]}><boxGeometry args={[width, 5, length]} /><meshStandardMaterial color="#bfcbd2" roughness={.95} /></mesh>
        <mesh position={[width * .12, 18, length * .08]}><boxGeometry args={[width * .34, 36, length * .24]} /><meshStandardMaterial color={index % 2 ? '#eef2f4' : '#d9e1e5'} roughness={.88} /></mesh>
        <mesh position={[-width * .2, 10, -length * .1]}><boxGeometry args={[width * .24, 20, length * .18]} /><meshStandardMaterial color="#e7ecef" roughness={.9} /></mesh>
        {index < 4 && <Crane position={[-width * .28, 0, length * .28]} rotation={index % 2 ? Math.PI : 0} />}
      </group>
    })}
    {resources?.assets.slice(0, 5).map((asset, index) => {
      const position = worldPosition(asset.lat, asset.lon)
      return <group key={asset.id} position={[position[0], 0, position[2]]}>
        <mesh position={[0, 9, 0]}><boxGeometry args={[30, 18, 30]} /><meshStandardMaterial color="#f1f4f6" roughness={.82} /></mesh>
        <mesh position={[0, 20, 0]} rotation={[0, Math.PI / 4, 0]}><coneGeometry args={[22, 10, 4]} /><meshStandardMaterial color="#cbd6dc" /></mesh>
        {index < 3 && <Crane position={[42, 0, -28]} rotation={index * .6} />}
      </group>
    })}
  </group>
}
