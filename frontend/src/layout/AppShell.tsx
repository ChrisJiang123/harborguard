import { MapView } from '../map2d/MapView'
import { useHarbor } from '../store/useHarbor'
import { lazy, Suspense } from 'react'
import { TopBar } from '../panels/TopBar'
import { TargetList } from '../panels/TargetList'
import { BuoyGrid } from '../panels/BuoyGrid'
import { AgentCard, DetectionPreview } from '../panels/AgentCard'
import { ImpactCard } from '../panels/ImpactCard'
import { LogPanel } from '../panels/LogPanel'
import { RiskBar } from '../panels/RiskBar'
import { Timeline } from '../panels/Timeline'
import { ToastHost } from '../panels/ToastHost'
import { ReopenPanel } from '../panels/ReopenPanel'
import { ReplayControls } from '../panels/ReplayControls'
import { MetricsCard } from '../panels/MetricsCard'
import { DemoTools } from '../panels/DemoTools'

const Scene = lazy(() => import('../view3d/Scene'))
function ViewFooter() {
  const conn = useHarbor(s => s.conn)
  const mode = useHarbor(s => s.latest?.mode)
  return <div className="view-footer"><span><i className="status-dot" />{conn === 'mock' ? 'Local simulated data · Not live port conditions' : conn === 'live' ? 'Live backend data' : conn === 'replay' ? 'File replay · Read-only · Backend disconnected' : 'Waiting for backend · Local demo available'}</span><span>{mode === 'disaster' ? 'Disaster mode · Source-provided reopening plan' : 'Security mode · Source-provided response metrics'}</span></div>
}
function MainView() {
  const view = useHarbor(s => s.view)
  return <section className="main-view"><div className="view-toolbar"><div><span className="eyebrow">PORT OF LOS ANGELES</span><h2>Port Overview</h2></div><div className="view-tabs"><button className={view === '2d' ? 'active' : ''} onClick={() => useHarbor.getState().setView('2d')}>2D Map</button><button className={view === '3d' ? 'active' : ''} onClick={() => useHarbor.getState().setView('3d')}>3D View</button><DemoTools /></div></div><ReplayControls />{view === '2d' ? <MapView /> : <Suspense fallback={<div className="three-loading" role="status">Loading 3D view…</div>}><Scene /></Suspense>}<ViewFooter /></section>
}
function StatusNotice() {
  const error = useHarbor(s => s.error)
  const conn = useHarbor(s => s.conn)
  const recovery = useHarbor(s => s.recovery)
  if (error) return <div className="status-notice error" role="alert">{error}<button onClick={() => useHarbor.getState().setError(null)} aria-label="Dismiss message">×</button></div>
  if (conn === 'disconnected' || conn === 'connecting') return <div className="status-notice">{conn === 'connecting' ? 'Connecting to backend…' : 'Backend disconnected. Reconnecting automatically.'} Select Local Demo in the top bar to continue.</div>
  if (conn === 'live' && recovery.phase === 'loading') return <div className="status-notice">Restoring history and joining live events…</div>
  if (conn === 'live' && recovery.message) return <div className="status-notice warning" role="status">{recovery.message} Approval status is never inferred from free-text logs.</div>
  return null
}
export function AppShell() {
  const disaster = useHarbor(s => s.latest?.mode === 'disaster')
  return <main className="app-shell"><TopBar /><aside className="left-panel"><TargetList /><BuoyGrid /><MetricsCard /></aside><div className="center-panel"><NetworkNotice /><StatusNotice /><MainView /></div><aside className="right-panel"><AgentCard />{disaster ? <ReopenPanel /> : <ImpactCard />}<LogPanel /></aside><footer className="bottom-panel"><Timeline /><RiskBar /></footer><ToastHost /><DetectionPreview /></main>
}

function NetworkNotice() {
  const offline = useHarbor(s => s.latest?.network === 'offline')
  const model = useHarbor(s => s.latestRec?.model)
  const conn = useHarbor(s => s.conn)
  if (!offline) return null
  return <div className="network-notice" role="status">{conn === 'mock' ? 'Simulated external network outage' : conn === 'replay' ? 'Recorded state: external network offline' : 'External network offline'} · {model === 'local' ? 'Agent switched to the local model' : model === 'template' ? 'Template recommendation active; local model is not running' : 'Waiting for Agent local-model status'}</div>
}
