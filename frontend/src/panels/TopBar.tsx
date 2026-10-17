import { api } from '../data/api'
import { useHarbor } from '../store/useHarbor'
import { runOperation, useOperations } from '../store/useOperations'
import { clock } from '../theme'

const CONN_LABELS = { live: 'LIVE', mock: 'MOCK', replay: 'REPLAY', connecting: 'CONNECTING', disconnected: 'DISCONNECTED' }
function ClockReadout() {
  const t = useHarbor(s => Math.floor(s.latest?.t ?? 0))
  const seq = useHarbor(s => s.latest?.seq ?? 0)
  return <div className="clock-readout"><span>仿真 <b>{clock(t)}</b></span><span className="seq">SEQ {seq.toString().padStart(5, '0')}</span></div>
}
function ConnectionBadge() {
  const conn = useHarbor(s => s.conn)
  const network = useHarbor(s => s.latest?.network)
  const critical = useHarbor(s => Object.values(s.alerts).some(alert => alert.level === 3))
  return <div className="connection-group">{critical && <span className="critical-badge">三级警报</span>}{network === 'offline' && <span className="offline-badge">外网离线</span>}<span className={`connection ${conn}`}><i />{CONN_LABELS[conn]}</span></div>
}
function CommandControls() {
  const conn = useHarbor(s => s.conn)
  const hasState = useHarbor(s => s.latest !== null)
  const paused = useHarbor(s => s.latest?.paused ?? false)
  const speed = useHarbor(s => s.latest?.speed ?? 1)
  const mode = useHarbor(s => s.latest?.mode ?? 'security')
  const network = useHarbor(s => s.latest?.network ?? 'online')
  const scenario = useHarbor(s => s.latest?.scenario)
  const pending = useOperations(s => s.pending)
  const disabled = !!pending || !hasState || (conn !== 'live' && conn !== 'mock')
  const start = (id: 'a' | 'b') => void runOperation(`启动场景 ${id.toUpperCase()}`, async () => {
    await api.startScenario(id)
  })
  return <div className="command-controls" aria-label="场景与仿真控制" aria-busy={!!pending}>
    <button disabled={disabled} className={scenario === 'a' ? 'is-active' : ''} onClick={() => start('a')}>场景 A</button>
    <button disabled={disabled} className={scenario === 'b' ? 'is-active' : ''} onClick={() => start('b')}>场景 B</button>
    <button disabled={disabled} onClick={() => void runOperation('重置', () => api.control({ action: 'reset' }))}>重置</button>
    <select aria-label="安防或灾害模式" value={mode} disabled={disabled} onChange={event => void runOperation('切换模式', () => api.mode(event.target.value as 'security' | 'disaster'))}><option value="security">安防</option><option value="disaster">灾害</option></select>
    <button role="switch" aria-checked={network === 'offline'} className={network === 'offline' ? 'network-offline' : ''} disabled={disabled} onClick={() => void runOperation('切换外网', () => api.inject({ type: network === 'online' ? 'network_down' : 'network_up' }))}>{network === 'online' ? '断外网' : '恢复网'}</button>
    <button disabled={disabled || !scenario} onClick={() => void runOperation(paused ? '继续' : '暂停', () => api.control({ action: paused ? 'resume' : 'pause' }))}>{pending === '暂停' || pending === '继续' ? '处理中…' : paused ? '▶ 继续' : 'Ⅱ 暂停'}</button>
    <select aria-label="演示速度" value={speed} disabled={disabled} onChange={event => void runOperation('设置倍速', () => api.control({ action: 'speed', value: Number(event.target.value) }))}><option value="1">1×</option><option value="4">4×</option><option value="10">10×</option></select>
    {pending && <span className="command-pending" role="status">{pending}中…</span>}
  </div>
}

export function TopBar() {
  const mock = new URLSearchParams(location.search).get('mock') === '1'
  return <header className="topbar"><div className="brand"><span className="brand-icon">H</span><h1>Harbor<span>Guard</span></h1></div><nav className="source-switch" aria-label="数据源"><a className={!location.search ? 'active' : ''} href="/">实时</a><a className={mock ? 'active' : ''} href="/?mock=1">本地演示</a><a className={location.search.includes('replay=') ? 'active' : ''} href="/?replay=demo_b.jsonl">演示回放</a></nav><CommandControls /><div className="topbar-status"><ClockReadout /><ConnectionBadge /></div></header>
}
