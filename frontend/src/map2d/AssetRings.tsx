import { Fragment, memo, useMemo } from 'react'
import { divIcon } from 'leaflet'
import { Circle, Marker, Tooltip } from 'react-leaflet'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { LEVEL_COLORS } from '../theme'
import type { Asset } from '../types/contract'

const AssetMarker = memo(function AssetMarker({ asset }: { asset: Asset }) {
  const level = useHarbor(s => Object.values(s.alerts).reduce((highest, alert) => alert.asset_id === asset.id ? Math.max(highest, alert.level) : highest, 0))
  const center = useMemo<[number, number]>(() => [asset.lat, asset.lon], [asset.lat, asset.lon])
  const icon = useMemo(() => divIcon({ className: 'harbor-asset-icon', iconSize: [24, 24], iconAnchor: [12, 12], html: '<span class="asset-map-symbol"><svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 21 7v6c0 5-9 9-9 9s-9-4-9-9V7Z" fill="none" stroke="currentColor" stroke-width="2"/><path d="M8 12h8m-4-4v8" stroke="currentColor" stroke-width="2"/></svg></span>' }), [])
  return <Fragment>{asset.rings_m.map((radius, i) => <Circle key={`${asset.id}-ring-${i}`} center={center} radius={radius} interactive={false} pathOptions={{ color: LEVEL_COLORS[i + 1], weight: level === i + 1 ? 3 : 1, dashArray: '7 7', opacity: level === i + 1 ? 0.9 : 0.55, fill: false }} />)}<Marker position={center} icon={icon} bubblingMouseEvents={false} title={asset.name}><Tooltip permanent direction="top" offset={[0, -14]} className="asset-label">{asset.name}</Tooltip></Marker></Fragment>
})

export function AssetRings() {
  const assets = useMapData(s => s.resources?.assets)
  return <>{assets?.map(asset => <AssetMarker asset={asset} key={asset.id} />)}</>
}
