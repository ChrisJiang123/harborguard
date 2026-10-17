import { useEffect, useState } from 'react'
import { Polyline, useMap } from 'react-leaflet'
import { loadLocalBase } from '../data/localBase'
import type { LocalBase } from '../data/localBase'

const COPYRIGHT = '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors · local vector / ODbL'
export function LocalBaseLayer({ visible }: { visible: boolean }) {
  const map = useMap()
  const [data, setData] = useState<LocalBase | null>(null)
  useEffect(() => { let disposed = false; void loadLocalBase().then(value => { if (!disposed) setData(value) }).catch(() => {}); return () => { disposed = true } }, [])
  useEffect(() => { if (!visible) return; map.attributionControl.addAttribution(COPYRIGHT); return () => { map.attributionControl.removeAttribution(COPYRIGHT) } }, [map, visible])
  if (!visible || !data) return null
  return <>{data.features.map(feature => <Polyline key={feature.properties.id} positions={feature.geometry.coordinates.map(p => [p[1]!, p[0]!] as [number, number])} interactive={false} pathOptions={{ color: feature.properties.kind === 'road' ? '#4b5c68' : '#73a8b7', opacity: .8, weight: feature.properties.kind === 'coastline' ? 2 : 1, fill: false }} />)}</>
}
