import { useHarbor } from '../store/useHarbor'
import { CLASS_NAMES, LEVEL_COLORS } from '../theme'
import { SectionHeading } from './SectionHeading'

export function TargetList() {
  const alerts = useHarbor(s => s.alerts)
  const tracks = useHarbor(s => s.tracks)
  const selected = useHarbor(s => s.selectedTrackId)
  const select = useHarbor(s => s.selectTrack)
  const conn = useHarbor(s => s.conn)
  const mode = useHarbor(s => s.latest?.mode)
  const scenario = useHarbor(s => s.latest?.scenario)
  const preview = conn === 'mock' && !scenario
  const grouped = Object.values(alerts)
  return <section className="targets-section"><SectionHeading index="01" title="Alert Targets" note={`${grouped.length} ${grouped.length === 1 ? "alert" : "alerts"}`} />
    {!grouped.length && <div className="empty-state"><span className="empty-symbol">◎</span><strong>{preview ? 'Ready to explore' : mode === 'disaster' ? 'No security alerts' : conn === 'live' || conn === 'mock' || conn === 'replay' ? 'All Clear' : 'Waiting for connection'}</strong><p>{preview ? 'Choose Scenario A or B to start a local demo, or Live to join the shared session.' : mode === 'disaster' ? 'Disaster mode is active. Survey and reopening plans appear on the right.' : conn === 'mock' ? 'A Level 1 alert appears 10 seconds into Scenario A.' : 'Targets appear here after receiving backend state.'}</p></div>}
    {([3, 2, 1] as const).map(level => {
      const items = grouped.filter(alert => alert.level === level).sort((a, b) => b.risk - a.risk)
      if (!items.length) return null
      return <div className="target-group" key={level}><div className="group-label" style={{ color: LEVEL_COLORS[level] }}><span className="level-dot" style={{ background: LEVEL_COLORS[level] }} />{['', 'Level 1 · Monitor', 'Level 2 · Warning', 'Level 3 · Critical'][level]}<span>{items.length}</span></div>{items.map(alert => {
        const track = tracks[alert.track_id]
        return <button className={`target-row ${selected === alert.track_id ? 'selected' : ''} ${level === 3 ? 'critical-target' : ''}`} key={alert.id} onClick={() => select(selected === alert.track_id ? null : alert.track_id)}>
          <span className="target-row-top"><b>{alert.track_id}</b><span className="muted">{track ? CLASS_NAMES[track.cls] : 'Waiting for track'}</span><span className="risk-value" style={{ color: LEVEL_COLORS[level] }}>{alert.risk.toFixed(2)}</span></span>
          <span className="target-row-bottom"><span>Asset distance {Math.round(alert.distance_m)} m</span><span>ETA {alert.eta_s === null ? '—' : `${Math.ceil(alert.eta_s)}s`}</span></span>
          <span className="risk-meter"><span style={{ width: `${Math.max(0, Math.min(1, alert.risk)) * 100}%`, background: LEVEL_COLORS[level] }} /></span>
        </button>
      })}</div>
    })}
  </section>
}
