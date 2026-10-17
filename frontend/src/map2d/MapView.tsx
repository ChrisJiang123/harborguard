import { useEffect, useMemo, useState } from 'react'
import { latLngBounds } from 'leaflet'
import { MapContainer, ScaleControl, TileLayer, useMap, useMapEvents, ZoomControl } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { useHarbor } from '../store/useHarbor'
import { ensureMapData, useMapData } from '../store/useMapData'
import { LEVEL_COLORS } from '../theme'
import { AssetRings } from './AssetRings'
import { BuoyLayer } from './BuoyLayer'
import { TrackLayer } from './TrackLayer'
import { ZoneLayer } from './ZoneLayer'
import { PORT_CENTER } from './geo'
import { polygonPositions } from '../data/mapGeometry'
import { LocalBaseLayer } from './LocalBaseLayer'
import { BlindAreas } from './BlindAreas'
import { DisasterLegend } from '../panels/DisasterLegend'
import { loadLocalBase } from '../data/localBase'
import { api } from '../data/api'
import { runOperation } from '../store/useOperations'

function MapEvents() {
  const selected = useHarbor(s => s.selectedTrackId)
  const focusedZone = useHarbor(s => s.focusedZoneId)
  const map = useMapEvents({ click: () => useHarbor.getState().selectTrack(null) })
  useEffect(() => {
    const container = map.getContainer()
    const observer = new ResizeObserver(() => map.invalidateSize({ pan: false }))
    observer.observe(container)
    return () => observer.disconnect()
  }, [map])
  useEffect(() => {
    const track = selected ? useHarbor.getState().tracks[selected] : undefined
    if (track && !map.getBounds().pad(-.12).contains([track.lat, track.lon])) map.panTo([track.lat, track.lon], { animate: true, duration: .5 })
  }, [selected, map])
  useEffect(() => {
    const feature = useMapData.getState().resources?.zones.features.find(zone => zone.properties.id === focusedZone)
    if (feature) map.fitBounds(latLngBounds(polygonPositions(feature.geometry).flat(2)), { maxZoom: 16, padding: [30, 30], animate: true })
  }, [focusedZone, map])
  return null
}

function HomeButton() {
  const map = useMap()
  return <div className="map-home-control"><button onClick={() => map.setView(PORT_CENTER, 14)} title="恢复洛杉矶港默认视野">⌖ 港口全景</button></div>
}

function SelectedDetails() {
  const selected = useHarbor(s => s.selectedTrackId)
  const track = useHarbor(s => selected ? s.tracks[selected] : undefined)
  if (!track) return <div className="map-selection-hint">点击地图目标查看 · 点击空白取消选中</div>
  const openSonar = () => void runOperation('读取声呐记录', async () => {
    const state = useHarbor.getState(), id = track.detection_id
    if (!id) return
    const detection = state.detections[id] ?? await api.detection(id)
    if (useHarbor.getState().session !== state.session) return
    useHarbor.getState().cacheDetection(detection)
    useHarbor.setState({ sonarModalDetId: id })
  })
  return <div className="map-selection-details"><b style={{ color: LEVEL_COLORS[track.level] }}>{track.id} · L{track.level}</b><span>深度 {track.depth_m.toFixed(1)} m</span><span>{track.lat.toFixed(5)}, {track.lon.toFixed(5)}</span>{track.detection_id && <button onClick={openSonar}>声呐图</button>}<button onClick={() => useHarbor.getState().selectTrack(null)} aria-label="取消选中目标">×</button></div>
}

export function MapView() {
  const resources = useMapData(s => s.resources)
  const loading = useMapData(s => s.loading)
  const error = useMapData(s => s.error)
  const [showBase, setShowBase] = useState(true)
  const [tileError, setTileError] = useState(false)
  const [tileVersion, setTileVersion] = useState(0)
  const [browserOnline, setBrowserOnline] = useState(navigator.onLine)
  const [localReady, setLocalReady] = useState(false)
  const offline = useHarbor(s => s.latest?.network === 'offline')
  const replay = useHarbor(s => s.conn === 'replay')
  const disaster = useHarbor(s => s.latest?.mode === 'disaster')
  const useOSM = showBase && browserOnline && !offline && !replay && !tileError
  useEffect(() => { void ensureMapData() }, [])
  useEffect(() => {
    let disposed = false
    void loadLocalBase().then(() => { if (!disposed) setLocalReady(true) }).catch(() => {})
    const update = () => setBrowserOnline(navigator.onLine)
    window.addEventListener('online', update); window.addEventListener('offline', update)
    return () => { disposed = true; window.removeEventListener('online', update); window.removeEventListener('offline', update) }
  }, [])
  const events = useMemo(() => ({ tileerror: () => setTileError(true) }), [])
  const demo = resources && Object.values(resources.sources).some(source => source === 'demo')
  return <div className="map-stage" aria-label="洛杉矶港二维态势地图">
    <MapContainer center={PORT_CENTER} zoom={14} minZoom={10} maxZoom={19} zoomControl={false} className="harbor-map" scrollWheelZoom>
      {useOSM && <TileLayer key={tileVersion} url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" attribution='&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors' eventHandlers={events} updateWhenIdle keepBuffer={1} />}
      <LocalBaseLayer visible={!useOSM} />
      <ZoomControl position="topleft" /><ScaleControl position="bottomleft" imperial={false} />
      <MapEvents /><ZoneLayer /><AssetRings /><BuoyLayer /><BlindAreas /><TrackLayer /><HomeButton />
    </MapContainer>
    <div className="map-layer-note">{loading ? '正在加载业务图层…' : error ?? (demo ? '含示例业务图层 · 模拟数据' : '团队业务图层已加载')}<button onClick={() => { const params = new URLSearchParams(location.search); if (params.get('mock') === '1' || params.has('replay')) location.reload(); else void ensureMapData(true) }} disabled={loading} title="重新读取业务图层（本地演示将重新开始）">↻</button></div>
    {!useOSM && <div className="map-tile-notice" role="status">{localReady ? '本地 OSM 岸线简图 · 非完整瓦片底图' : '纯业务图层 · 本地岸线不可用'}{!offline && !replay && browserOnline && <button onClick={() => { setShowBase(true); setTileError(false); setTileVersion(v => v + 1) }}>显示在线底图</button>}</div>}
    {useOSM && <button className="map-show-base" onClick={() => setShowBase(false)}>切换离线简图</button>}
    {disaster ? <DisasterLegend /> : <div className="map-legend" aria-label="地图图例"><span><i style={{ background: LEVEL_COLORS[1] }} />一级</span><span><i style={{ background: LEVEL_COLORS[2] }} />二级</span><span><i style={{ background: LEVEL_COLORS[3] }} />三级</span><span className="predicted-legend">┄ 预测航迹</span></div>}
    <SelectedDetails />
  </div>
}
