import { api } from '../data/api'
import { useHarbor } from '../store/useHarbor'
import { runOperation, useOperations } from '../store/useOperations'
import { clock } from '../theme'

const CONN_LABELS = { live: 'LIVE', mock: 'MOCK', replay: 'REPLAY', connecting: 'CONNECTING', disconnected: 'DISCONNECTED' }
function ClockReadout() {
  const t = useHarbor(s => Math.floor(s.latest?.t ?? 0))
  const seq = useHarbor(s => s.latest?.seq ?? 0)
  return <div className="clock-readout"><span>Simulation <b>{clock(t)}</b></span><span className="seq">SEQ {seq.toString().padStart(5, '0')}</span></div>
}
function ConnectionBadge() {
  const conn = useHarbor(s => s.conn)
  const network = useHarbor(s => s.latest?.network)
  const critical = useHarbor(s => Object.values(s.alerts).some(alert => alert.level === 3))
  return <div className="connection-group">{critical && <span className="critical-badge">Level 3 Alert</span>}{network === 'offline' && <span className="offline-badge">Network Offline</span>}<span className={`connection ${conn}`}><i />{CONN_LABELS[conn]}</span></div>
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
  const start = (id: 'a' | 'b') => void runOperation(`Start scenario ${id.toUpperCase()}`, async () => {
    await api.startScenario(id)
  })
  return <div className="command-controls" aria-label="Scenario and simulation controls" aria-busy={!!pending}>
    <button disabled={disabled} className={scenario === 'a' ? 'is-active' : ''} onClick={() => start('a')}>Scenario A</button>
    <button disabled={disabled} className={scenario === 'b' ? 'is-active' : ''} onClick={() => start('b')}>Scenario B</button>
    <button disabled={disabled} onClick={() => void runOperation('Reset', () => api.control({ action: 'reset' }))}>Reset</button>
    <select aria-label="Security or disaster mode" value={mode} disabled={disabled} onChange={event => void runOperation('Switch mode', () => api.mode(event.target.value as 'security' | 'disaster'))}><option value="security">Security</option><option value="disaster">Disaster</option></select>
    <button role="switch" aria-checked={network === 'offline'} className={network === 'offline' ? 'network-offline' : ''} disabled={disabled} onClick={() => void runOperation('Toggle external network', () => api.inject({ type: network === 'online' ? 'network_down' : 'network_up' }))}>{network === 'online' ? 'Disconnect' : 'Reconnect'}</button>
    <button disabled={disabled || !scenario} onClick={() => void runOperation(paused ? 'Resume' : 'Pause', () => api.control({ action: paused ? 'resume' : 'pause' }))}>{pending === 'Pause' || pending === 'Resume' ? 'Working…' : paused ? '▶ Resume' : 'Ⅱ Pause'}</button>
    <select aria-label="Demo speed" value={speed} disabled={disabled} onChange={event => void runOperation('Set speed', () => api.control({ action: 'speed', value: Number(event.target.value) }))}><option value="1">1×</option><option value="4">4×</option><option value="10">10×</option></select>
    {pending && <span className="command-pending" role="status">{pending} in progress…</span>}
  </div>
}

export function TopBar() {
  const mock = new URLSearchParams(location.search).get('mock') === '1'
  return <header className="topbar"><div className="brand"><span className="brand-icon">H</span><h1>Harbor<span>Guard</span></h1></div><nav className="source-switch" aria-label="Data source"><a className={!location.search ? 'active' : ''} href="/">Live</a><a className={mock ? 'active' : ''} href="/?mock=1">Local Demo</a><a className={location.search.includes('replay=') ? 'active' : ''} href="/?replay=demo_b.jsonl">Demo Replay</a></nav><CommandControls /><div className="topbar-status"><ClockReadout /><ConnectionBadge /></div></header>
}
