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
  return <section className="buoy-section"><SectionHeading index="02" title="浮标阵列" note={`在线 ${online}/${buoys?.length ?? 0}`} />
    <div className="buoy-grid">{buoys?.map(buoy => <div key={buoy.id} className={`buoy-cell ${buoy.status === 'down' ? 'down' : ''}`} title={`${buoy.id} · ${buoy.status === 'ok' ? '在线' : '离线'} · 覆盖 ${buoy.range_m}m`}><span className={buoy.pinging ? 'buoy-light ping' : 'buoy-light'}>{buoy.status === 'down' ? '×' : ''}</span><span>{buoy.id}</span></div>)}</div>
    {!buoys?.length && <p className="muted panel-padding">等待浮标状态</p>}
    <div className="legend"><span><i className="green-dot" />在线</span><span><i className="gray-dot" />离线</span><span><i className="blue-dot" />声呐 ping</span></div>
    <details className="buoy-fault-controls"><summary>浮标故障注入</summary><p className="muted">仅改变数据源状态，不操作实际设备。</p><select aria-label="故障浮标" value={chosen?.id ?? ''} onChange={e => setChoice(e.target.value)}>{buoys?.map(buoy => <option key={buoy.id} value={buoy.id}>{buoy.id}</option>)}</select><button disabled={!chosen || !!pending || (conn !== 'live' && conn !== 'mock')} onClick={() => { if (chosen) void runOperation('注入浮标状态', () => api.inject({ type: chosen.status === 'down' ? 'buoy_up' : 'buoy_down', target: chosen.id })) }}>{chosen?.status === 'down' ? '恢复浮标' : '模拟离线'}</button></details>
  </section>
}
