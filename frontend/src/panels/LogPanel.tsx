import { useHarbor } from '../store/useHarbor'
import { clock } from '../theme'
import { SectionHeading } from './SectionHeading'

const SOURCES = { sim: '仿真', perception: '感知', decision: '决策', agent: 'Agent', operator: '操作员' }
export function LogPanel() {
  const logs = useHarbor(s => s.logs)
  return <section className="events-section"><SectionHeading index="05" title="运行日志" note={`最近 ${Math.min(logs.length, 50)} 条`} /><div className="event-list" aria-label="运行日志">{logs.length === 0 && <p className="muted panel-padding">等待第一条日志…</p>}{logs.slice(-50).reverse().map((log, i) => <div className={`event-row log-${log.level}`} key={`${logs.length - i}-${log.t}-${log.source}`}><time>{clock(log.t)}</time><div><span className="log-source">{SOURCES[log.source]}</span><p>{log.text}</p></div></div>)}</div></section>
}
