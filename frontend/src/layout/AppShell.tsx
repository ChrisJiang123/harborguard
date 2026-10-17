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
  return <div className="view-footer"><span><i className="status-dot" />{conn === 'mock' ? '本地模拟数据 · 非真实港口态势' : conn === 'live' ? '后端实时数据' : conn === 'replay' ? '文件回放 · 只读 · 不连接后端' : '等待后端 · 可切换本地演示'}</span><span>{mode === 'disaster' ? '灾害模式 · 复航方案由数据源提供' : '安防模式 · 方案指标由数据源提供'}</span></div>
}
function MainView() {
  const view = useHarbor(s => s.view)
  return <section className="main-view"><div className="view-toolbar"><div><span className="eyebrow">PORT OF LOS ANGELES</span><h2>港口态势总览</h2></div><div className="view-tabs"><button className={view === '2d' ? 'active' : ''} onClick={() => useHarbor.getState().setView('2d')}>2D 地图</button><button className={view === '3d' ? 'active' : ''} onClick={() => useHarbor.getState().setView('3d')}>3D 水下</button><DemoTools /></div></div><ReplayControls />{view === '2d' ? <MapView /> : <Suspense fallback={<div className="three-loading" role="status">正在加载 3D 水下视图…</div>}><Scene /></Suspense>}<ViewFooter /></section>
}
function StatusNotice() {
  const error = useHarbor(s => s.error)
  const conn = useHarbor(s => s.conn)
  const recovery = useHarbor(s => s.recovery)
  if (error) return <div className="status-notice error" role="alert">{error}<button onClick={() => useHarbor.getState().setError(null)} aria-label="关闭提示">×</button></div>
  if (conn === 'disconnected' || conn === 'connecting') return <div className="status-notice">{conn === 'connecting' ? '正在连接后端…' : '后端未连接，正在自动重连。'} 可以点击顶栏“本地演示”继续查看。</div>
  if (conn === 'live' && recovery.phase === 'loading') return <div className="status-notice">正在衔接实时事件并恢复刷新前记录…</div>
  if (conn === 'live' && recovery.message) return <div className="status-notice warning" role="status">{recovery.message} 不会从自由文本日志推断审批结果。</div>
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
  return <div className="network-notice" role="status">{conn === 'mock' ? '模拟外网已断开' : conn === 'replay' ? '记录状态：外网已断开' : '外网已断开'} · {model === 'local' ? 'Agent 已切换本地模型' : model === 'template' ? '当前为模板建议，未运行本地模型' : '等待 Agent 确认本地模型状态'}</div>
}
