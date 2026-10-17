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
  const source = conn === 'live' ? '后端实时数据' : conn === 'mock' ? '本地模拟数据' : conn === 'replay' ? '文件回放数据' : '等待数据源'
  return <div className="three-selected-readout"><div className="three-readout-source"><span className={`connection ${conn}`}><i />{source}</span><span>{latest?.scenario ? `场景 ${latest.scenario.toUpperCase()}` : '未启动场景'} · {clock(latest?.t ?? 0)} · {paused ? '已暂停' : '运行中'}</span></div>{selected && track ? <div className="three-readout-target"><strong>{selected} · {CLASS_NAMES[track.cls]}</strong><span>{track.status === 'confirmed' ? '已确认' : '暂定'}</span><span>航向 {Math.round(track.heading_deg)}°</span><span>航速 {track.speed_mps.toFixed(1)} m/s</span><span>深度 {track.depth_m.toFixed(1)} m</span><span>风险 {track.risk.toFixed(2)} · L{track.level}</span></div> : <span>点击场景中的目标进行选中；位置、航向、状态与当前数据源时间同步</span>}</div>
}

function ObjectPicker() {
  const tracks = useHarbor(s => s.tracks)
  const selected = useHarbor(s => s.selectedTrackId)
  const options = Object.values(tracks).sort((a, b) => a.id.localeCompare(b.id))
  return <label className="three-object-picker">目标<select aria-label="选择三维目标" value={selected ?? ''} onChange={event => useHarbor.getState().selectTrack(event.target.value || null)}><option value="">未选中</option>{options.map(track => <option key={track.id} value={track.id}>{track.id} · {CLASS_NAMES[track.cls]}</option>)}</select></label>
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
  const [labelMode, setLabelMode] = useState<'auto' | 'all' | 'minimal'>('auto')
  const [simple, setSimple] = useState(false)
  const [showStats, setShowStats] = useState(() => new URLSearchParams(location.search).get('stats') === '1')
  const [contextLost, setContextLost] = useState(false)
  const [rendererVersion, setRendererVersion] = useState(0)
  const container = useRef<HTMLDivElement>(null)
  const [fps, setFps] = useState<number | null>(null)
  const updateFps = useCallback((value: number) => setFps(value), [])
  const bounds = useMemo(() => sceneBounds(resources, grid), [resources, grid])
  const camera = useMemo(() => ({ fov: 45, near: .25, far: Math.max(50000, bounds.span * 10), position: cameraPreset('overview', bounds, undefined, undefined, verticalScale).position }), [bounds, verticalScale])
  const mode: CameraMode = selected && selected !== choice.selectedAtChoice ? 'follow' : choice.mode === 'follow' && !selected ? 'overview' : choice.mode
  const choose = (next: CameraMode) => setChoice(current => ({ mode: next, selectedAtChoice: selected, revision: current.revision + 1 }))
  const setLayer = (key: keyof Layers, value: boolean) => setLayers(current => ({ ...current, [key]: value }))
  const onLoss = useMemo(() => () => setContextLost(true), [])
  useEffect(() => { void ensureMapData(); void ensureBathymetry() }, [])
  const maxDepth = grid?.metadata.max_depth_m ?? 40
  const triangleCount = grid ? Math.max(0, (grid.metadata.width - 1) * (grid.metadata.height - 1) * 2 - grid.metadata.nodata_cells * 2) : 0
  return <div className="three-stage" ref={container} aria-label="港口水上与水下三维数字孪生">
    <SceneBoundary><Canvas key={rendererVersion} camera={camera} dpr={[1, 1.35]} performance={{ min: .65 }} gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }} fallback={<div className="three-fallback"><h3>浏览器未提供 3D 渲染支持</h3><button onClick={() => useHarbor.getState().setView('2d')}>返回 2D 地图</button></div>} onPointerMissed={() => useHarbor.getState().selectTrack(null)}>
      <color attach="background" args={['#071522']} /><fog attach="fog" args={['#071522', bounds.span * .65, bounds.span * 3.2]} /><ambientLight intensity={1.25} /><hemisphereLight args={['#d7efff', '#324b42', 1.55]} /><directionalLight position={[2000, 3500, 1500]} intensity={2.4} />
      <SceneLabelMode.Provider value={labelMode}><AdaptiveDpr pixelated />{waterVisible && <Water bounds={bounds} opacity={waterOpacity} />}{layers.seabed && grid && <Seabed grid={grid} verticalScale={verticalScale} showContours={layers.contours} />}{layers.models && <HarborModels3D />}{layers.risks && <Zone3D />}{layers.routes && <NavigationRoute3D />}{layers.risks && <AlertVolume simple={simple} verticalScale={verticalScale} maxDepth={maxDepth} />}{layers.buoys && <><Buoy3D verticalScale={verticalScale} maxDepth={maxDepth} /><BlindAreas3D /></>}{layers.vessels && <><Track3D verticalScale={verticalScale} /><Target3D verticalScale={verticalScale} /></>}<CameraRig mode={mode} revision={choice.revision} bounds={bounds} verticalScale={verticalScale} /><RendererLifecycle onLoss={onLoss} /><PerformanceProbe onSample={updateFps} /></SceneLabelMode.Provider>
    </Canvas></SceneBoundary>
    {showStats && <div className="three-fps" aria-label="三维帧率"><strong>{fps ?? '—'}</strong><span>FPS</span></div>}
    <div className="three-camera-controls" aria-label="三维相机预设"><button className={mode === 'overview' ? 'active' : ''} onClick={() => choose('overview')}>整体总览</button><button className={mode === 'surface' ? 'active' : ''} onClick={() => choose('surface')}>水上视角</button><button className={mode === 'underwater' ? 'active' : ''} onClick={() => choose('underwater')}>水下视角</button><button className={mode === 'follow' ? 'active' : ''} disabled={!selected} onClick={() => choose('follow')}>跟随选中</button><button onClick={() => choose('overview')}>视角复位</button><ObjectPicker /></div>
    <div className={`three-source-note ${grid?.metadata.source_kind === 'synthetic' ? 'demo' : ''}`}>{loading || demLoading ? '正在加载港区与海底数据…' : demError ? <>海底 DEM 不可用：{demError} <button onClick={() => void ensureBathymetry(true)}>重试</button></> : grid?.metadata.source_kind === 'synthetic' ? '演示地形 · 非真实测深 · 固定参考水位' : '测深格式数据已加载 · 来源与基准仍需人工验收'}</div>
    <SelectedReadout />
    <DisasterLegend className="three-disaster-legend" />
    <div className="three-layer-controls"><strong>图层</strong>{(Object.keys(layers) as (keyof Layers)[]).map(key => <label key={key}><input type="checkbox" checked={layers[key]} disabled={key === 'contours' && !layers.seabed} onChange={event => setLayer(key, event.target.checked)} />{{ models: '港区白模', seabed: '海底地形', contours: '海底等深线', vessels: '船舶目标', buoys: '浮标覆盖', routes: '航线', risks: '风险区域' }[key]}</label>)}</div>
    <div className="three-display-controls"><label><input type="checkbox" checked={waterVisible} onChange={event => setWaterVisible(event.target.checked)} />显示水面</label><label className="three-range">水面透明度 <input aria-label="水面透明度" type="range" min="0.05" max="0.6" step="0.05" value={waterOpacity} disabled={!waterVisible} onChange={event => setWaterOpacity(Number(event.target.value))} /><span>{Math.round(waterOpacity * 100)}%</span></label><label>垂直显示 <select aria-label="垂直夸张倍数" value={verticalScale} onChange={event => setVerticalScale(Number(event.target.value))}><option value="1">1× 真实比例</option><option value="4">4× 增强显示</option><option value="8">8× 地形观察</option></select></label><label>标签密度 <select aria-label="三维标签密度" value={labelMode} onChange={event => setLabelMode(event.target.value as typeof labelMode)}><option value="auto">自动避让</option><option value="minimal">仅重点</option><option value="all">全部标签</option></select></label><label><input type="checkbox" checked={simple} onChange={event => setSimple(event.target.checked)} />简化风险体</label><label><input type="checkbox" checked={showStats} onChange={event => setShowStats(event.target.checked)} />显示帧率面板</label></div>
    <div className="three-legend"><span>垂直 {verticalScale}× {verticalScale === 1 ? '（真实比例）' : '（增强显示，非真实比例）'} · 水面 0 m（演示参考，非实时潮位）</span><span>{grid ? `${grid.metadata.title} · ${grid.metadata.width}×${grid.metadata.height} · ${grid.metadata.min_depth_m.toFixed(1)}–${grid.metadata.max_depth_m.toFixed(1)} m · NoData ${grid.metadata.nodata_cells} · 约 ${triangleCount.toLocaleString()} 三角面` : '尚未加载海底网格'}</span>{grid && <span>来源：{grid.metadata.source} · 垂直基准：{grid.metadata.vertical_datum} · 参考水位 {grid.metadata.reference_water_level_m.toFixed(2)} m</span>}<span>EPSG:4326 → 本地 ENU 米制 · 深度向下为正 · <b>{fps === null ? '采样中' : `${fps} FPS`}</b> · 拖动旋转 / 滚轮缩放 / 右键平移</span></div>
    {contextLost && <div className="three-context-notice" role="alert">3D 渲染连接已中断。<button onClick={() => { setContextLost(false); setRendererVersion(version => version + 1) }}>重新加载 3D</button><button onClick={() => useHarbor.getState().setView('2d')}>返回 2D</button></div>}
  </div>
}
