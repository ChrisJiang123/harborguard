import { useId } from 'react'
import { Circle, Tooltip } from 'react-leaflet'
import { useShallow } from 'zustand/react/shallow'
import { useHarbor } from '../store/useHarbor'

export function BlindAreas() {
  const id = `blind-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`
  const buoys = useHarbor(useShallow(s => s.latest?.buoys.filter(buoy => buoy.status === 'down') ?? []))
  return <><svg className="map-pattern-defs" aria-hidden="true"><defs><pattern id={id} width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(35)"><rect width="9" height="9" fill="#6B7280" fillOpacity=".16" /><path d="M0 0V9" stroke="#a0a8b4" strokeWidth="3" /></pattern></defs></svg>{buoys.map(buoy => <Circle key={buoy.id} center={[buoy.lat, buoy.lon]} radius={buoy.range_m} pathOptions={{ color: '#9ca3af', weight: 1, dashArray: '5 4', fillColor: `url(#${id})`, fillOpacity: .7 }}><Tooltip sticky>{buoy.id} offline · Potential blind spot (coverage illustration; overlapping buoy coverage is not subtracted)</Tooltip></Circle>)}</>
}
