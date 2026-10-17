import { memo, useMemo } from 'react'
import { Polygon, Tooltip } from 'react-leaflet'
import { polygonPositions } from '../data/mapGeometry'
import type { ZoneFeature } from '../data/mapGeometry'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { zoneStyle } from './styles'

const KINDS: Record<string, string> = { berth: '泊位', channel: '航道', anchorage: '锚地' }
const STATE_NAMES = { open: '开放', restricted: '限制通航', clear: '可复航', unsurveyed: '待勘测', blocked: '封闭' }

const Zone = memo(function Zone({ feature }: { feature: ZoneFeature }) {
  const { id, name, kind } = feature.properties
  const state = useHarbor(s => s.latest?.zones.find(zone => zone.id === id)?.state ?? feature.properties.state ?? 'open')
  const coverage = useHarbor(s => s.latest?.zones.find(zone => zone.id === id)?.coverage ?? feature.properties.coverage)
  const highlighted = useHarbor(s => !!s.hoveredOptionId && Object.values(s.optionsByAlert).some(options => options.some(option => option.id === s.hoveredOptionId && option.zones_closed.includes(id))))
  const focused = useHarbor(s => s.focusedZoneId === id)
  const disaster = useHarbor(s => s.latest?.mode === 'disaster')
  const positions = useMemo(() => polygonPositions(feature.geometry), [feature.geometry])
  const style = useMemo(() => zoneStyle(state, highlighted, focused), [state, highlighted, focused])
  return <Polygon positions={positions} pathOptions={style}>
    {disaster && <Tooltip permanent direction="center" className="zone-coverage-label" interactive={false}>{id} · {coverage === undefined ? '—' : `${Math.round(coverage * 100)}%`}</Tooltip>}
    {!disaster && <Tooltip sticky><div className="map-tooltip-content"><strong>{name} · {id}</strong><span>{KINDS[kind] ?? kind} · {STATE_NAMES[state]}</span><span>覆盖率 {coverage === undefined ? '待接收' : `${Math.round(coverage * 100)}%`}</span></div></Tooltip>}
  </Polygon>
})

export function ZoneLayer() {
  const zones = useMapData(s => s.resources?.zones)
  return <>{zones?.features.map(feature => <Zone key={feature.properties.id} feature={feature} />)}</>
}
