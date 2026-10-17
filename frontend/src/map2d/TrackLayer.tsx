import { Fragment, memo, useEffect, useMemo, useRef, useState } from 'react'
import { divIcon } from 'leaflet'
import type { Marker as LeafletMarker } from 'leaflet'
import { Marker, Polygon, Polyline, Tooltip } from 'react-leaflet'
import { useHarbor } from '../store/useHarbor'
import { CLASS_NAMES, LEVEL_COLORS } from '../theme'
import { errorEllipse, trailPositions } from './geo'
import { targetIconHTML } from './styles'

const TrackMarker = memo(function TrackMarker({ id }: { id: string }) {
  const track = useHarbor(s => s.tracks[id])
  const selected = useHarbor(s => s.selectedTrackId === id)
  const marker = useRef<LeafletMarker>(null)
  const frame = useRef(0)
  const [initial] = useState<[number, number]>(() => [track?.lat ?? 33.735, track?.lon ?? -118.255])
  const lat = track?.lat
  const lon = track?.lon
  const icon = useMemo(() => divIcon({ className: 'harbor-target-icon', html: targetIconHTML(track?.cls ?? 'unknown', track?.level ?? 0, selected), iconSize: [40, 40], iconAnchor: [20, 20] }), [track?.cls, track?.level, selected])
  const events = useMemo(() => ({ click: () => useHarbor.getState().selectTrack(id) }), [id])
  const history = useMemo(() => trailPositions(track?.history ?? []), [track?.history])
  const prediction = useMemo<[number, number][]>(() => track ? [[track.lat, track.lon], ...trailPositions(track.predicted)] : [], [track])
  const ellipse = useMemo(() => track ? errorEllipse(track) : [], [track])
  useEffect(() => {
    if (lat === undefined || lon === undefined || !marker.current) return
    cancelAnimationFrame(frame.current)
    const start = marker.current.getLatLng()
    const destination = { lat, lng: lon }
    const startTime = performance.now()
    const animate = (now: number) => {
      const p = Math.min((now - startTime) / 200, 1)
      marker.current?.setLatLng([start.lat + (destination.lat - start.lat) * p, start.lng + (destination.lng - start.lng) * p])
      if (p < 1) frame.current = requestAnimationFrame(animate)
    }
    frame.current = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame.current)
  }, [lat, lon])
  if (!track || !Number.isFinite(track.lat) || !Number.isFinite(track.lon)) return null
  const color = LEVEL_COLORS[track.level]
  const opacity = track.status === 'tentative' ? .5 : 1
  return <Fragment>
    {history.length > 1 && <Polyline positions={history} interactive={false} pathOptions={{ color, weight: selected ? 3 : 2, opacity: opacity * .9 }} />}
    {prediction.length > 1 && <Polyline positions={prediction} interactive={false} pathOptions={{ color, weight: 1.5, opacity: opacity * .65, dashArray: '7 7' }} />}
    <Polygon positions={ellipse} interactive={false} pathOptions={{ color, weight: 1, opacity: opacity * .5, fillColor: color, fillOpacity: .08 }} />
    <Marker ref={marker} position={initial} icon={icon} opacity={opacity} zIndexOffset={selected ? 1000 : 200} eventHandlers={events} bubblingMouseEvents={false} title={`${id} · ${CLASS_NAMES[track.cls]} · L${track.level}`}>
      <Tooltip permanent direction="right" offset={[21, 0]} className={`track-label ${selected ? 'selected' : ''}`}>{id} · {track.cls} · L{track.level}</Tooltip>
    </Marker>
  </Fragment>
})

export function TrackLayer() {
  // Subscribe to IDs separately so individual markers own their 5 Hz updates.
  const ids = useHarbor(s => Object.keys(s.tracks).sort().join('\u0000'))
  return <>{ids ? ids.split('\u0000').map(id => <TrackMarker key={id} id={id} />) : null}</>
}
