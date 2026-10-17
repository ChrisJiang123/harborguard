import { useHarbor } from '../store/useHarbor'
import { clock, ZONE_COLORS } from '../theme'
import { SectionHeading } from './SectionHeading'

export function ReopenPanel() {
  const plan = useHarbor(s => s.reopenPlan)
  const zones = useHarbor(s => s.latest?.zones)
  const conn = useHarbor(s => s.conn)
  const detections = useHarbor(s => s.detections)
  const debris = Object.values(detections).filter(detection => detection.cls === 'debris').sort((a, b) => b.t - a.t)
  return <section className="reopen-section"><SectionHeading index="04" title="勘测与复航" note={conn === 'mock' ? '模拟结果' : '数据源结果'} /><div className="reopen-body">{plan ? <><div className="hours-saved">比全港勘测少停摆 <strong>{Number.isFinite(plan.est_hours_saved) ? plan.est_hours_saved : '—'}</strong> 小时</div><p className="muted">按每区勘测 1.5 小时的假设计算 · 数值由数据源提供</p>{([
    ['建议复航航道', plan.route_zone_ids, 'clear'], ['建议开放泊位', plan.reopen_berth_zone_ids, 'clear'], ['待勘测', plan.unsurveyed_zone_ids, 'unsurveyed'], ['封闭', plan.blocked_zone_ids, 'blocked'],
  ] as const).map(([title, ids, state]) => <div className="reopen-group" key={title}><b style={{ color: ZONE_COLORS[state] }}>{title}</b><div>{ids.length ? ids.map(id => <button key={id} onClick={() => useHarbor.setState({ focusedZoneId: id, view: '2d' })}>{id}</button>) : <span className="muted">无</span>}</div></div>)}</> : <p className="muted">等待数据源的复航方案。{conn === 'mock' && '场景 B 在 24 秒提供初步方案，45 秒更新。'}</p>}<details className="debris-detections" open><summary>碎片识别记录 <span>{debris.length}</span></summary>{debris.length ? debris.map(detection => <button key={detection.id} onClick={() => useHarbor.setState({ sonarModalDetId: detection.id })}><b>{detection.id}</b><span>{detection.buoy_id} · {Math.round(detection.conf * 100)}% · {clock(detection.t)}</span><small>{detection.model === 'stub' ? '演示识别' : detection.model}</small></button>) : <p className="muted">尚无后端碎片 detection 记录；前端不会生成假识别结果。</p>}</details><details className="coverage-list"><summary>分区状态与覆盖率</summary>{zones?.map(zone => <div key={zone.id}><span style={{ color: ZONE_COLORS[zone.state] }}>{zone.id} · {{ open: '开放', restricted: '限制', clear: '可复航', unsurveyed: '待勘测', blocked: '封闭' }[zone.state]}</span><span>{Number.isFinite(zone.coverage) ? `${Math.round(zone.coverage * 100)}%` : '—'}</span></div>)}</details></div></section>
}
