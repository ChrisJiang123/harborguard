import { Fragment, memo, useEffect, useMemo, useRef } from 'react'
import { divIcon } from 'leaflet'
import type { Marker as LeafletMarker } from 'leaflet'
import { Circle, Marker, Tooltip } from 'react-leaflet'
import type { StaticBuoy } from '../data/mapGeometry'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { buoyIconHTML } from './styles'

const BuoyMarker = memo(function BuoyMarker({ id, baseline }: { id: string; baseline?: StaticBuoy }) {
  const buoy = useHarbor(s => s.latest?.buoys.find(item => item.id === id))
  const current = buoy ?? baseline
  const status = buoy?.status ?? 'pending'
  const marker = useRef<LeafletMarker>(null)
  const animation = useRef<Animation | null>(null)
  const icon = useMemo(() => divIcon({ className: 'harbor-buoy-icon', html: buoyIconHTML(status), iconSize: [24, 24], iconAnchor: [12, 12] }), [status])
  useEffect(() => {
    if (!buoy?.pinging || buoy.status !== 'ok') return
    const ripple = marker.current?.getElement()?.querySelector('.buoy-ripple')
    animation.current?.cancel()
    if (ripple) animation.current = ripple.animate([{ transform: 'scale(.4)', opacity: .8 }, { transform: 'scale(4)', opacity: 0 }], { duration: 1500, easing: 'ease-out' })
  }, [buoy?.pinging, buoy?.status])
  useEffect(() => () => animation.current?.cancel(), [])
  if (!current) return null
  const color = status === 'ok' ? '#38bdf8' : '#6B7280'
  return <Fragment><Circle center={[current.lat, current.lon]} radius={current.range_m} interactive={false} pathOptions={{ color, weight: 1, opacity: .2, fillColor: color, fillOpacity: status === 'ok' ? .035 : .015, dashArray: status === 'ok' ? undefined : '4 6' }} /><Marker ref={marker} position={[current.lat, current.lon]} icon={icon} bubblingMouseEvents={false} title={`${id} · ${status === 'pending' ? '等待实时状态' : status === 'ok' ? '在线' : '离线'} · 覆盖 ${current.range_m} 米`}><Tooltip permanent direction="bottom" offset={[0, 9]} className="buoy-label">{id}{status === 'down' ? ' ×' : ''}</Tooltip></Marker></Fragment>
})

export function BuoyLayer() {
  const liveBuoys = useHarbor(s => s.latest?.buoys)
  const baseline = useMapData(s => s.resources?.buoys)
  const ids = useMemo(() => [...new Set([...(baseline ?? []).map(item => item.id), ...(liveBuoys ?? []).map(item => item.id)])], [baseline, liveBuoys])
  return <>{ids.map(id => <BuoyMarker key={id} id={id} baseline={baseline?.find(item => item.id === id)} />)}</>
}
