import { useHarbor } from '../store/useHarbor'
import { clock, ZONE_COLORS } from '../theme'
import { SectionHeading } from './SectionHeading'

export function ReopenPanel() {
  const plan = useHarbor(s => s.reopenPlan)
  const zones = useHarbor(s => s.latest?.zones)
  const conn = useHarbor(s => s.conn)
  const detections = useHarbor(s => s.detections)
  const debris = Object.values(detections).filter(detection => detection.cls === 'debris').sort((a, b) => b.t - a.t)
  return <section className="reopen-section"><SectionHeading index="04" title="Survey & Reopening" note={conn === 'mock' ? 'Simulated results' : 'Source results'} /><div className="reopen-body">{plan ? <><div className="hours-saved">Downtime saved vs. full-port survey: <strong>{Number.isFinite(plan.est_hours_saved) ? plan.est_hours_saved : '—'}</strong> hours</div><p className="muted">Assumes 1.5 hours per zone · Values provided by the data source</p>{([
    ['Recommended channels', plan.route_zone_ids, 'clear'], ['Recommended berths', plan.reopen_berth_zone_ids, 'clear'], ['Unsurveyed', plan.unsurveyed_zone_ids, 'unsurveyed'], ['Blocked', plan.blocked_zone_ids, 'blocked'],
  ] as const).map(([title, ids, state]) => <div className="reopen-group" key={title}><b style={{ color: ZONE_COLORS[state] }}>{title}</b><div>{ids.length ? ids.map(id => <button key={id} onClick={() => useHarbor.setState({ focusedZoneId: id, view: '2d' })}>{id}</button>) : <span className="muted">None</span>}</div></div>)}</> : <p className="muted">Waiting for a reopening plan from the data source. {conn === 'mock' && 'Scenario B: initial plan at 24 s, updated at 45 s.'}</p>}<details className="debris-detections" open><summary>Debris Detection Records <span>{debris.length}</span></summary>{debris.length ? debris.map(detection => <button key={detection.id} onClick={() => useHarbor.setState({ sonarModalDetId: detection.id })}><b>{detection.id}</b><span>{detection.buoy_id} · {Math.round(detection.conf * 100)}% · {clock(detection.t)}</span><small>{detection.model === 'stub' ? 'Demo detection' : detection.model}</small></button>) : <p className="muted">No debris detection records received from the backend.</p>}</details><details className="coverage-list"><summary>Zone Status & Coverage</summary>{zones?.map(zone => <div key={zone.id}><span style={{ color: ZONE_COLORS[zone.state] }}>{zone.id} · {{ open: 'Open', restricted: 'Restricted', clear: 'Ready to reopen', unsurveyed: 'Unsurveyed', blocked: 'Blocked' }[zone.state]}</span><span>{Number.isFinite(zone.coverage) ? `${Math.round(zone.coverage * 100)}%` : '—'}</span></div>)}</details></div></section>
}
