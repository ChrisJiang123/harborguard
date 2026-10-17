import { eventTrackId } from '../data/mock'
import { useShallow } from 'zustand/react/shallow'
import { useHarbor } from '../store/useHarbor'
import { clock, LEVEL_COLORS } from '../theme'
import type { Alert } from '../types/contract'

const LABELS: Record<string, string> = { alert_raised: 'Alert raised', alert_changed: 'Alert escalated', detection: 'Target classified', options_ready: 'Options ready', recommendation: 'Recommendation', decision: 'Operator decision', reopen_plan: 'Reopening plan', network_changed: 'Network change' }
export function Timeline() {
  const t = useHarbor(s => Math.floor(s.latest?.t ?? 0))
  const events = useHarbor(s => s.events)
  const trackIds = useHarbor(useShallow(s => Object.keys(s.tracks)))
  const alertTracks = useHarbor(useShallow(s => Object.fromEntries(Object.values(s.alerts).map(alert => [alert.id, alert.track_id]))))
  const relevant = events.filter(event => LABELS[event.event])
  const duration = Math.max(1, t)
  return <section className="timeline"><div className="timeline-title"><span className="section-index">06</span><h2>Event Timeline</h2><span className="muted">00:00 — {clock(t)}</span></div><div className="timeline-rail"><div className="timeline-progress" style={{ width: '100%' }} />{relevant.map(event => {
    const data = event.data as { alert?: Alert; alert_id?: string }
    const trackId = eventTrackId(event) ?? (data.alert_id ? alertTracks[data.alert_id] ?? null : null)
    const color = data.alert ? LEVEL_COLORS[data.alert.level] : '#38bdf8'
    return <button key={`${event.seq}-${event.event}-${event.t}`} className="timeline-marker" style={{ left: `${Math.max(0, Math.min(1, event.t / duration)) * 100}%`, background: color }} title={`${clock(event.t)} · ${LABELS[event.event]}`} aria-label={`${clock(event.t)} ${LABELS[event.event]}`} disabled={!trackId || !trackIds.includes(trackId)} onClick={() => { if (trackId) useHarbor.getState().selectTrack(trackId) }} />
  })}</div><div className="timeline-labels">{[0, .25, .5, .75, 1].map(ratio => <span key={ratio}>{clock(t * ratio)}</span>)}</div></section>
}
