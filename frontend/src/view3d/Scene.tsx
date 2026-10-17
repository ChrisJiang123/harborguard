import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { AdaptiveDpr } from '@react-three/drei'
import { useHarbor } from '../store/useHarbor'
import { ensureMapData, useMapData } from '../store/useMapData'
import { ensureBathymetry, useBathymetry } from '../store/useBathymetry'
import { CLASS_NAMES, clock } from '../theme'
import { AlertVolume } from './AlertVolume'
import { Buoy3D } from './Buoy3D'
import { CameraRig } from './CameraRig'
import { cameraPreset, sceneBounds } from './coordinates'
import type { CameraMode } from './coordinates'
import { SceneBoundary } from './SceneBoundary'
import { Seabed } from './Seabed'
import { SceneLabelMode } from './SceneLabelContext'
import { Target3D } from './Target3D'
import { Track3D } from './Track3D'
import { Water } from './Water'
import { Zone3D } from './Zone3D'
import { BlindAreas3D } from './BlindAreas3D'
import { DisasterLegend } from '../panels/DisasterLegend'
import { NavigationRoute3D } from './NavigationRoute3D'
import { HarborModels3D } from './HarborModels3D'
import { useReplay } from '../store/useReplay'

interface Layers { models: boolean; seabed: boolean; contours: boolean; vessels: boolean; buoys: boolean; routes: boolean; risks: boolean }
const initialLayers: Layers = { models: true, seabed: true, contours: true, vessels: true, buoys: true, routes: true, risks: true }

function RendererLifecycle({ onLoss }: { onLoss: () => void }) {
  const gl = useThree(s => s.gl)
  useEffect(() => {
    const canvas = gl.domElement
    const lost = (event: Event) => { event.preventDefault(); onLoss() }
    canvas.addEventListener('webglcontextlost', lost)
    return () => canvas.removeEventListener('webglcontextlost', lost)
  }, [gl, onLoss])
  return null
}

function PerformanceProbe({ onSample }: { onSample: (fps: number) => void }) {
  const sample = useRef({ started: 0, frames: 0 })
  useFrame(({ clock }) => {
    sample.current.frames++
    const now = clock.elapsedTime
    if (sample.current.started === 0) { sample.current.started = now; return }
    const elapsed = now - sample.current.started
    if (elapsed < 1) return
    onSample(Math.round(sample.current.frames / elapsed))
    sample.current = { started: now, frames: 0 }
  })
  return null
}

function SelectedReadout() {
  const selected = useHarbor(s => s.selectedTrackId)
  const track = useHarbor(s => selected ? s.tracks[selected] : undefined)
  const latest = useHarbor(s => s.latest)
  const conn = useHarbor(s => s.conn)
  const replayPlaying = useReplay(s => s.playing)
  const paused = conn === 'replay' ? !replayPlaying : latest?.paused
  const source = conn === 'live' ? 'Live backend data' : conn === 'mock' ? 'Local simulated data' : conn === 'replay' ? 'Replay data' : 'Waiting for data source'
  return <div className="three-selected-readout"><div className="three-readout-source"><span className={`connection ${conn}`}><i />{source}</span><span>{latest?.scenario ? `Scenario ${latest.scenario.toUpperCase()}` : 'No active scenario'} · {clock(latest?.t ?? 0)} · {paused ? 'Paused' : 'Running'}</span></div>{selected && track ? <div className="three-readout-target"><strong>{selected} · {CLASS_NAMES[track.cls]}</strong><span>{track.status === 'confirmed' ? 'Confirmed' : 'Tentative'}</span><span>Heading {Math.round(track.heading_deg)}°</span><span>Speed {track.speed_mps.toFixed(1)} m/s</span><span>Depth {track.depth_m.toFixed(1)} m</span><span>Risk {track.risk.toFixed(2)} · L{track.level}</span></div> : <span>Select a target to inspect it. Position, heading, and status follow the current data-source time.</span>}</div>
}

function ObjectPicker() {
  const tracks = useHarbor(s => s.tracks)
  const selected = useHarbor(s => s.selectedTrackId)
  const options = Object.values(tracks).sort((a, b) => a.id.localeCompare(b.id))
  return <label className="three-object-picker">Target<select aria-label="Select 3D target" value={selected ?? ''} onChange={event => useHarbor.getState().selectTrack(event.target.value || null)}><option value="">None selected</option>{options.map(track => <option key={track.id} value={track.id}>{track.id} · {CLASS_NAMES[track.cls]}</option>)}</select></label>
}

export default function Scene() {
  const selected = useHarbor(s => s.selectedTrackId)
  const resources = useMapData(s => s.resources)
  const loading = useMapData(s => s.loading)
  const grid = useBathymetry(s => s.grid)
  const demLoading = useBathymetry(s => s.loading)
  const demError = useBathymetry(s => s.error)
  const [choice, setChoice] = useState<{ mode: CameraMode; selectedAtChoice: string | null; revision: number }>({ mode: 'overview', selectedAtChoice: null, revision: 0 })
  const [layers, setLayers] = useState<Layers>(initialLayers)
  const [waterVisible, setWaterVisible] = useState(true)
  const [waterOpacity, setWaterOpacity] = useState(.24)
  const [verticalScale, setVerticalScale] = useState(1)
  const [environmentStatus, setEnvironmentStatus] = useState('Loading real harbor geometry…')
  const [labelMode, setLabelMode] = useState<'auto' | 'all' | 'minimal'>('auto')
  const [simple, setSimple] = useState(false)
  const [showStats, setShowStats] = useState(() => new URLSearchParams(location.search).get('stats') === '1')
  const [contextLost, setContextLost] = useState(false)
  const [rendererVersion, setRendererVersion] = useState(0)
  const container = useRef<HTMLDivElement>(null)
  const [fps, setFps] = useState<number | null>(null)
  const updateFps = useCallback((value: number) => setFps(value), [])
  const updateEnvironmentStatus = useCallback((status: string) => setEnvironmentStatus(status), [])
  const bounds = useMemo(() => sceneBounds(resources, grid), [resources, grid])
  const camera = useMemo(() => ({ fov: 45, near: .25, far: Math.max(50000, bounds.span * 10), position: cameraPreset('overview', bounds, undefined, undefined, verticalScale).position }), [bounds, verticalScale])
  const mode: CameraMode = selected && selected !== choice.selectedAtChoice ? 'follow' : choice.mode === 'follow' && !selected ? 'overview' : choice.mode
  const choose = (next: CameraMode) => setChoice(current => ({ mode: next, selectedAtChoice: selected, revision: current.revision + 1 }))
  const setLayer = (key: keyof Layers, value: boolean) => setLayers(current => ({ ...current, [key]: value }))
  const onLoss = useMemo(() => () => setContextLost(true), [])
  useEffect(() => { void ensureMapData(); void ensureBathymetry() }, [])
  const maxDepth = grid?.metadata.max_depth_m ?? 40
  const triangleCount = grid ? Math.max(0, (grid.metadata.width - 1) * (grid.metadata.height - 1) * 2 - grid.metadata.nodata_cells * 2) : 0
  return <div className="three-stage" ref={container} aria-label="Harbor surface and underwater 3D digital twin">
    <SceneBoundary><Canvas key={rendererVersion} camera={camera} dpr={[1, 1.35]} performance={{ min: .65 }} gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }} fallback={<div className="three-fallback"><h3>3D rendering is unavailable in this browser</h3><button onClick={() => useHarbor.getState().setView('2d')}>Return to 2D map</button></div>} onPointerMissed={() => useHarbor.getState().selectTrack(null)}>
      <color attach="background" args={['#071522']} /><fog attach="fog" args={['#071522', bounds.span * .65, bounds.span * 3.2]} /><ambientLight intensity={1.25} /><hemisphereLight args={['#d7efff', '#324b42', 1.55]} /><directionalLight position={[2000, 3500, 1500]} intensity={2.4} />
      <SceneLabelMode.Provider value={labelMode}><AdaptiveDpr pixelated />{waterVisible && <Water bounds={bounds} opacity={waterOpacity} grid={grid} />}{layers.seabed && grid && <Seabed grid={grid} verticalScale={verticalScale} showContours={layers.contours} />}{layers.models && <HarborModels3D verticalScale={verticalScale} onStatus={updateEnvironmentStatus} />}{layers.risks && <Zone3D />}{layers.routes && <NavigationRoute3D />}{layers.risks && <AlertVolume simple={simple} verticalScale={verticalScale} maxDepth={maxDepth} />}{layers.buoys && <><Buoy3D verticalScale={verticalScale} maxDepth={maxDepth} /><BlindAreas3D /></>}{layers.vessels && <><Track3D verticalScale={verticalScale} /><Target3D verticalScale={verticalScale} /></>}<CameraRig mode={mode} revision={choice.revision} bounds={bounds} verticalScale={verticalScale} /><RendererLifecycle onLoss={onLoss} /><PerformanceProbe onSample={updateFps} /></SceneLabelMode.Provider>
    </Canvas></SceneBoundary>
    {showStats && <div className="three-fps" aria-label="3D frame rate"><strong>{fps ?? '—'}</strong><span>FPS</span></div>}
    <div className="three-camera-controls" aria-label="3D camera presets"><button className={mode === 'overview' ? 'active' : ''} onClick={() => choose('overview')}>Overview</button><button className={mode === 'surface' ? 'active' : ''} onClick={() => choose('surface')}>Surface</button><button className={mode === 'underwater' ? 'active' : ''} onClick={() => choose('underwater')}>Underwater</button><button className={mode === 'follow' ? 'active' : ''} disabled={!selected} onClick={() => choose('follow')}>Follow Selected</button><button onClick={() => choose('overview')}>Reset View</button><ObjectPicker /></div>
    <div className={`three-source-note ${grid?.metadata.source_kind !== 'survey' ? 'demo' : ''}`}>{loading || demLoading ? 'Loading harbor and seabed data…' : demError ? <>Seabed DEM unavailable: {demError} <button onClick={() => void ensureBathymetry(true)}>Retry</button></> : grid?.metadata.source_kind === 'synthetic' ? 'Demo terrain · Not surveyed bathymetry · Fixed reference water level' : grid?.metadata.source_kind === 'regional_dem' ? 'NOAA regional coastal DEM · MSL · 1″ grid · Not a detailed harbor survey / Not for navigation' : 'Bathymetric survey loaded · Source and datum require manual acceptance'}</div>
    <div className="three-environment-note" role="status">{environmentStatus} · © OSM contributors · © LA County / LARIAC / Pictometry / EagleView · Land DEM: NAVD88; seabed/water: MSL; no vertical datum transformation applied</div>
    <SelectedReadout />
    <DisasterLegend className="three-disaster-legend" />
    <div className="three-layer-controls"><strong>Layers</strong>{(Object.keys(layers) as (keyof Layers)[]).map(key => <label key={key}><input type="checkbox" checked={layers[key]} disabled={key === 'contours' && !layers.seabed} onChange={event => setLayer(key, event.target.checked)} />{{ models: 'Buildings & land terrain', seabed: 'Seabed terrain', contours: 'Depth contours', vessels: 'Vessel targets', buoys: 'Buoy coverage', routes: 'Routes', risks: 'Risk areas' }[key]}</label>)}</div>
    <div className="three-display-controls"><label><input type="checkbox" checked={waterVisible} onChange={event => setWaterVisible(event.target.checked)} />Show water</label><label className="three-range">Water opacity <input aria-label="Water opacity" type="range" min="0.05" max="0.6" step="0.05" value={waterOpacity} disabled={!waterVisible} onChange={event => setWaterOpacity(Number(event.target.value))} /><span>{Math.round(waterOpacity * 100)}%</span></label><label>Vertical scale <select aria-label="Vertical exaggeration" value={verticalScale} onChange={event => setVerticalScale(Number(event.target.value))}><option value="1">1× True scale</option><option value="4">4× Enhanced</option><option value="8">8× Terrain inspection</option></select></label><label>Labels <select aria-label="3D label density" value={labelMode} onChange={event => setLabelMode(event.target.value as typeof labelMode)}><option value="auto">Auto declutter</option><option value="minimal">Key labels only</option><option value="all">All labels</option></select></label><label><input type="checkbox" checked={simple} onChange={event => setSimple(event.target.checked)} />Simplify risk volumes</label><label><input type="checkbox" checked={showStats} onChange={event => setShowStats(event.target.checked)} />Show frame rate</label></div>
    <div className="three-legend">
      <span>Vertical {verticalScale}× {verticalScale === 1 ? '(true scale)' : '(enhanced, not true scale)'} · Water 0 m (reference, not live tide)</span>
      <span>{grid ? `${grid.metadata.width}×${grid.metadata.height} grid · Depth ${grid.metadata.min_depth_m.toFixed(1)}–${grid.metadata.max_depth_m.toFixed(1)} m · NoData ${grid.metadata.nodata_cells} · ~${triangleCount.toLocaleString()} triangles` : 'Seabed grid not loaded'}</span>
      {grid && <span title={`${grid.metadata.title}\n${grid.metadata.source}\n${grid.metadata.vertical_datum}`}>Source: {grid.metadata.source_kind === 'regional_dem' ? 'NOAA/NCEI regional DEM · MSL' : grid.metadata.source_kind === 'synthetic' ? 'Synthetic demo terrain' : grid.metadata.source} · Reference {grid.metadata.reference_water_level_m.toFixed(2)} m</span>}
      <span>Local ENU meters · Depth positive down · <b>{fps === null ? 'Sampling' : `${fps} FPS`}</b> · Drag: orbit / Scroll: zoom / Right-drag: pan</span>
    </div>
    {contextLost && <div className="three-context-notice" role="alert">3D rendering context lost.<button onClick={() => { setContextLost(false); setRendererVersion(version => version + 1) }}>Reload 3D</button><button onClick={() => useHarbor.getState().setView('2d')}>Return to 2D</button></div>}
  </div>
}
