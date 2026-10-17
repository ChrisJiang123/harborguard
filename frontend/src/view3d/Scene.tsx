import { useEffect, useMemo, useRef, useState } from 'react'
import type { RefObject } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { AdaptiveDpr, Stats } from '@react-three/drei'
import { useHarbor } from '../store/useHarbor'
import { ensureMapData, useMapData } from '../store/useMapData'
import { CLASS_NAMES, clock, SEABED_DEPTH_M, VZ } from '../theme'
import { AlertVolume } from './AlertVolume'
import { Buoy3D } from './Buoy3D'
import { CameraRig } from './CameraRig'
import { cameraPreset, sceneBounds } from './coordinates'
import type { CameraMode } from './coordinates'
import { SceneBoundary } from './SceneBoundary'
import { Seabed } from './Seabed'
import { Target3D } from './Target3D'
import { Track3D } from './Track3D'
import { Water } from './Water'
import { Zone3D } from './Zone3D'
import { BlindAreas3D } from './BlindAreas3D'
import { DisasterLegend } from '../panels/DisasterLegend'
import { NavigationRoute3D } from './NavigationRoute3D'
import { useReplay } from '../store/useReplay'

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
function SelectedReadout() {
  const selected = useHarbor(s => s.selectedTrackId)
  const track = useHarbor(s => selected ? s.tracks[selected] : undefined)
  const latest = useHarbor(s => s.latest)
  const conn = useHarbor(s => s.conn)
  const replayPlaying = useReplay(s => s.playing)
  const paused = conn === 'replay' ? !replayPlaying : latest?.paused
  const source = conn === 'live' ? '后端实时数据' : conn === 'mock' ? '本地模拟数据' : conn === 'replay' ? '文件回放数据' : '等待数据源'
  return <div className="three-selected-readout"><div className="three-readout-source"><span className={`connection ${conn}`}><i />{source}</span><span>{latest?.scenario ? `场景 ${latest.scenario.toUpperCase()}` : '未启动场景'} · {clock(latest?.t ?? 0)} · {paused ? '已暂停' : '运行中'}</span></div>{selected && track ? <div className="three-readout-target"><strong>{selected} · {CLASS_NAMES[track.cls]}</strong><span>{track.status === 'confirmed' ? '已确认' : '暂定'}</span><span>航向 {Math.round(track.heading_deg)}°</span><span>航速 {track.speed_mps.toFixed(1)} m/s</span><span>深度 {track.depth_m.toFixed(1)} m</span><span>风险 {track.risk.toFixed(2)} · L{track.level}</span></div> : <span>点击场景中的目标进行选中；船舶、航迹和状态随当前数据源时间同步</span>}</div>
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
  const [choice, setChoice] = useState<{ mode: CameraMode; selectedAtChoice: string | null; revision: number }>({ mode: 'overview', selectedAtChoice: null, revision: 0 })
  const [simple, setSimple] = useState(false)
  const [showStats, setShowStats] = useState(() => new URLSearchParams(location.search).get('stats') === '1')
  const [contextLost, setContextLost] = useState(false)
  const [rendererVersion, setRendererVersion] = useState(0)
  const container = useRef<HTMLDivElement>(null)
  const bounds = useMemo(() => sceneBounds(resources), [resources])
  const camera = useMemo(() => ({ fov: 45, near: 1, far: Math.max(50000, bounds.span * 10), position: cameraPreset('overview', bounds).position }), [bounds])
  const mode: CameraMode = selected && selected !== choice.selectedAtChoice ? 'follow' : choice.mode === 'follow' && !selected ? 'overview' : choice.mode
  const choose = (next: CameraMode) => setChoice(current => ({ mode: next, selectedAtChoice: selected, revision: current.revision + 1 }))
  const onLoss = useMemo(() => () => setContextLost(true), [])
  useEffect(() => { void ensureMapData() }, [])
  return <div className="three-stage" ref={container} aria-label="港口三维水下态势视图">
    <SceneBoundary><Canvas key={rendererVersion} camera={camera} dpr={[1, 1.35]} performance={{ min: .65 }} gl={{ antialias: true, alpha: false, powerPreference: 'high-performance' }} fallback={<div className="three-fallback"><h3>浏览器未提供 3D 渲染支持</h3><button onClick={() => useHarbor.getState().setView('2d')}>返回 2D 地图</button></div>} onPointerMissed={() => useHarbor.getState().selectTrack(null)}>
      <color attach="background" args={['#071522']} /><ambientLight intensity={1.2} /><hemisphereLight args={['#b1ddff', '#514737', 1.4]} /><directionalLight position={[2000, 3500, 1500]} intensity={2.2} />
      <AdaptiveDpr pixelated /><Water bounds={bounds} />{!simple && <Seabed bounds={bounds} />}<Zone3D /><NavigationRoute3D /><AlertVolume simple={simple} /><Buoy3D /><BlindAreas3D /><Track3D /><Target3D /><CameraRig mode={mode} revision={choice.revision} bounds={bounds} /><RendererLifecycle onLoss={onLoss} />
      {showStats && <Stats className="three-fps" parent={container as RefObject<HTMLElement>} />}
    </Canvas></SceneBoundary>
    <div className="three-camera-controls" aria-label="三维相机预设"><button className={mode === 'overview' ? 'active' : ''} onClick={() => choose('overview')}>全港俯视</button><button className={mode === 'follow' ? 'active' : ''} disabled={!selected} onClick={() => choose('follow')}>跟随选中</button><button className={mode === 'dock' ? 'active' : ''} disabled={!resources?.assets.length} onClick={() => choose('dock')}>码头视角</button><ObjectPicker /></div>
    <div className="three-source-note">{loading ? '正在加载港区、航道与设施…' : resources && Object.values(resources.sources).some(source => source === 'demo') ? '含示例港区图层 · 数据源状态见下方' : '港区图层来自后端或本地业务文件'}</div>
    <SelectedReadout />
    <DisasterLegend className="three-disaster-legend" />
    <div className="three-display-controls"><label><input type="checkbox" checked={simple} onChange={event => setSimple(event.target.checked)} />简化视图</label><label><input type="checkbox" checked={showStats} onChange={event => setShowStats(event.target.checked)} />显示帧率</label></div>
    <div className="three-legend"><span>深度 ×{VZ} · 目标 ×5</span><span>{simple ? '简化视图：隐藏海底与警戒柱' : `演示海底：基准 ${SEABED_DEPTH_M} m，起伏 ±2 m`}</span><span>拖动旋转 · 滚轮缩放 · 右键平移</span></div>
    {contextLost && <div className="three-context-notice" role="alert">3D 渲染连接已中断。<button onClick={() => { setContextLost(false); setRendererVersion(version => version + 1) }}>重新加载 3D</button><button onClick={() => useHarbor.getState().setView('2d')}>返回 2D</button></div>}
  </div>
}
