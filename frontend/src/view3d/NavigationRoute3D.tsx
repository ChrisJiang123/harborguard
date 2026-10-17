import { useMemo } from 'react'
import { Line } from '@react-three/drei'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { zoneCenter } from './coordinates'
import { SceneLabel } from './SceneLabel'

export function NavigationRoute3D() {
  const zones = useMapData(s => s.resources?.zones.features)
  const planIds = useHarbor(s => s.reopenPlan?.route_zone_ids.join('\u0000') ?? '')
  const planned = !!planIds
  const route = useMemo(() => {
    if (!zones) return []
    const ids = planned ? planIds.split('\u0000') : zones.filter(zone => zone.properties.kind === 'channel').map(zone => zone.properties.id)
    return ids.map(id => zones.find(zone => zone.properties.id === id)).filter(zone => zone !== undefined).map(zone => zoneCenter(zone, 5))
  }, [zones, planIds, planned])
  if (route.length < 2) return null
  const color = planned ? '#4ade80' : '#38bdf8'
  const label = planned ? '数据源复航航线' : '港区航道参考线'
  const middle = route[Math.floor(route.length / 2)]!
  return <group>
    <Line points={route} color={color} lineWidth={planned ? 4 : 2.2} dashed={!planned} dashSize={55} gapSize={32} transparent opacity={planned ? .95 : .7} raycast={() => {}} />
    {route.map((point, index) => <mesh key={index} position={point} rotation={[-Math.PI / 2, 0, 0]} raycast={() => {}}><ringGeometry args={[10, 15, 24]} /><meshBasicMaterial color={color} transparent opacity={.8} depthWrite={false} side={2} /></mesh>)}
    <SceneLabel position={[middle[0], middle[1] + 18, middle[2]]} text={label} color={planned ? '#8ce9ae' : '#72d8f7'} borderColor={planned ? '#50b881' : '#2686a6'} pixelHeight={17} />
  </group>
}
