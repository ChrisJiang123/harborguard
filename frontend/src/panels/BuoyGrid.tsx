import { useHarbor } from '../store/useHarbor'
import { useState } from 'react'
import { api } from '../data/api'
import { runOperation, useOperations } from '../store/useOperations'
import { SectionHeading } from './SectionHeading'

export function BuoyGrid() {
  const buoys = useHarbor(s => s.latest?.buoys)
  const online = buoys?.filter(buoy => buoy.status === 'ok').length ?? 0
  const conn = useHarbor(s => s.conn)
  const pending = useOperations(s => s.pending)
  const [choice, setChoice] = useState('')
  const chosen = buoys?.find(buoy => buoy.id === choice) ?? buoys?.[0]
  return <section className="buoy-section"><SectionHeading index="02" title="Buoy Array" note={`Online ${online}/${buoys?.length ?? 0}`} />
    <div className="buoy-grid">{buoys?.map(buoy => <div key={buoy.id} className={`buoy-cell ${buoy.status === 'down' ? 'down' : ''}`} title={`${buoy.id} · ${buoy.status === 'ok' ? 'Online' : 'Offline'} · Range ${buoy.range_m}m`}><span className={buoy.pinging ? 'buoy-light ping' : 'buoy-light'}>{buoy.status === 'down' ? '×' : ''}</span><span>{buoy.id}</span></div>)}</div>
    {!buoys?.length && <p className="muted panel-padding">Waiting for buoy status</p>}
    <div className="legend"><span><i className="green-dot" />Online</span><span><i className="gray-dot" />Offline</span><span><i className="blue-dot" />Sonar ping</span></div>
    <details className="buoy-fault-controls"><summary>Buoy Fault Injection</summary><p className="muted">Changes data-source state only; does not control physical devices.</p><select aria-label="Affected buoy" value={chosen?.id ?? ''} onChange={e => setChoice(e.target.value)}>{buoys?.map(buoy => <option key={buoy.id} value={buoy.id}>{buoy.id}</option>)}</select><button disabled={!chosen || !!pending || (conn !== 'live' && conn !== 'mock')} onClick={() => { if (chosen) void runOperation('Inject buoy state', () => api.inject({ type: chosen.status === 'down' ? 'buoy_up' : 'buoy_down', target: chosen.id })) }}>{chosen?.status === 'down' ? 'Restore buoy' : 'Simulate outage'}</button></details>
  </section>
}
