import { useEffect, useMemo } from 'react'
import { Line } from '@react-three/drei'
import { DoubleSide, ExtrudeGeometry, Path, Shape, ShapeGeometry, Vector2 } from 'three'
import type { ZoneFeature } from '../data/mapGeometry'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { ZONE_COLORS } from '../theme'
import { worldPosition, zoneRings } from './coordinates'
import { SceneLabel } from './SceneLabel'

function ZoneOutline({ feature }: { feature: ZoneFeature }) {
  const id = feature.properties.id
  const state = useHarbor(s => s.latest?.zones.find(zone => zone.id === id)?.state ?? feature.properties.state ?? 'open')
  const hovered = useHarbor(s => !!s.hoveredOptionId && Object.values(s.optionsByAlert).some(options => options.some(option => option.id === s.hoveredOptionId && option.zones_closed.includes(id))))
  const focused = useHarbor(s => s.focusedZoneId === id)
  const disaster = useHarbor(s => s.latest?.mode === 'disaster')
  const coverage = useHarbor(s => s.latest?.zones.find(zone => zone.id === id)?.coverage)
  const rings = useMemo(() => zoneRings(feature), [feature])
  const geometry = useMemo(() => {
    const polygons = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates
    const shapes = polygons.map(polygon => {
      const points = polygon.map(ring => ring.map(point => {
        const position = worldPosition(point[1]!, point[0]!)
        return new Vector2(position[0], -position[2])
      }))
      const shape = new Shape(points[0])
      shape.holes = points.slice(1).map(hole => new Path(hole))
      return shape
    })
    return { surface: new ShapeGeometry(shapes), structure: feature.properties.kind === 'berth' ? new ExtrudeGeometry(shapes, { depth: 10, bevelEnabled: false }) : null }
  }, [feature])
  useEffect(() => () => { geometry.surface.dispose(); geometry.structure?.dispose() }, [geometry])
  const center = useMemo(() => { geometry.surface.computeBoundingBox(); const b = geometry.surface.boundingBox!; return [(b.min.x + b.max.x) / 2, 8, -(b.min.y + b.max.y) / 2] as [number, number, number] }, [geometry])
  const kind = feature.properties.kind
  const color = disaster || state !== 'open' ? ZONE_COLORS[state] : kind === 'channel' ? '#0b6a91' : kind === 'berth' ? '#566576' : '#28506b'
  const showLabel = focused || (disaster && (state !== 'open' || coverage === undefined || coverage < .999))
  return <group>
    {kind === 'berth' && !disaster && geometry.structure ? <mesh geometry={geometry.structure} rotation={[-Math.PI / 2, 0, 0]} position={[0, 1, 0]} raycast={() => {}}><meshStandardMaterial color={color} transparent opacity={state === 'restricted' ? .55 : .42} roughness={.9} metalness={.05} depthWrite={false} /></mesh> : <mesh geometry={geometry.surface} rotation={[-Math.PI / 2, 0, 0]} position={[0, 1, 0]} raycast={() => {}}><meshBasicMaterial color={color} transparent opacity={disaster ? .3 : kind === 'channel' ? .16 : .22} side={DoubleSide} depthWrite={false} /></mesh>}
    {rings.map((points, index) => <Line key={index} points={points} color={hovered ? '#EF4444' : focused ? '#7dd3fc' : color} lineWidth={hovered || focused ? 3 : kind === 'channel' ? 1.8 : 1.2} dashed={hovered} dashSize={45} gapSize={30} raycast={() => {}} />)}
    {showLabel && <SceneLabel position={center} text={`${id} · ${disaster ? coverage === undefined ? '—' : `${Math.round(coverage * 100)}%` : feature.properties.name}`} color={disaster ? ZONE_COLORS[state] : '#bde8ff'} pixelHeight={16} maxDistance={6000} importance={focused || state !== 'open' ? 'high' : 'normal'} />}
  </group>
}
export function Zone3D() {
  const zones = useMapData(s => s.resources?.zones)
  return <group>{zones?.features.map(feature => <ZoneOutline key={feature.properties.id} feature={feature} />)}</group>
}
