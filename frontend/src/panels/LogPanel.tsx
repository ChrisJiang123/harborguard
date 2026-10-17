import { englishText } from '../data/english'
import { useHarbor } from '../store/useHarbor'
import { clock } from '../theme'
import { SectionHeading } from './SectionHeading'

const SOURCES = { sim: 'Simulation', perception: 'Perception', decision: 'Decision', agent: 'Agent', operator: 'Operator' }
export function LogPanel() {
  const logs = useHarbor(s => s.logs)
  return <section className="events-section"><SectionHeading index="05" title="Activity Log" note={`Last ${Math.min(logs.length, 50)} ${logs.length === 1 ? "entry" : "entries"}`} /><div className="event-list" aria-label="Activity Log">{logs.length === 0 && <p className="muted panel-padding">Waiting for the first log entry…</p>}{logs.slice(-50).reverse().map((log, i) => <div className={`event-row log-${log.level}`} key={`${logs.length - i}-${log.t}-${log.source}`}><time>{clock(log.t)}</time><div><span className="log-source">{SOURCES[log.source]}</span><p>{englishText(log.text)}</p></div></div>)}</div></section>
}
