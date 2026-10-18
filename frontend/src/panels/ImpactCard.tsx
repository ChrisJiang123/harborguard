import { englishText } from '../data/english'
import { useEffect, useState } from 'react'
import { api } from '../data/api'
import { useHarbor } from '../store/useHarbor'
import { notify, useOperations } from '../store/useOperations'
import type { Option } from '../types/contract'
import { activeAlertId, effectiveOptionId, numberText } from './selection'
import { SectionHeading } from './SectionHeading'

const EMPTY: Option[] = []
export function ImpactCard() {
  const alertId = useHarbor(activeAlertId)
  const session = useHarbor(s => s.session)
  return <ImpactContent key={`${session}-${alertId}`} alertId={alertId} />
}

function ImpactContent({ alertId }: { alertId: string | null }) {
  const ready = useHarbor(s => alertId ? s.alerts[alertId]?.options_ready : false)
  const storedOptions = useHarbor(s => alertId ? s.optionsByAlert[alertId] : undefined)
  const options = storedOptions ?? EMPTY
  const rec = useHarbor(s => alertId ? s.recByAlert[alertId] : undefined)
  const chosen = useHarbor(s => s.chosenOptionId)
  const chosenFor = useHarbor(s => s.chosenOptionAlertId)
  const conn = useHarbor(s => s.conn)
  const locked = useHarbor(s => alertId ? !!s.decisionsByAlert[alertId] || !!s.decisionRequests[alertId] : true)
  const pending = useOperations(s => s.pending)
  const [failure, setFailure] = useState<string | null>(null)
  const [retry, setRetry] = useState(0)
  const effective = effectiveOptionId(alertId, options, rec, chosen, chosenFor)
  const loading = !!alertId && !!ready && !storedOptions && conn === 'live' && !failure
  useEffect(() => {
    if (!alertId || !ready || storedOptions || conn !== 'live') return
    let disposed = false
    const abort = new AbortController()
    const session = useHarbor.getState().session
    api.options(alertId, abort.signal).then(result => {
      if (!disposed && useHarbor.getState().session === session) useHarbor.getState().cacheOptions(alertId, result.options)
    }).catch(error => {
      if (disposed || abort.signal.aborted) return
      const message = error instanceof Error ? error.message : 'Could not load options.'
      setFailure(message); notify(`Could not load options: ${message}`, 'error')
    })
    return () => { disposed = true; abort.abort() }
  }, [alertId, ready, storedOptions, conn, retry])
  const hover = (id: string | null) => useHarbor.setState({ hoveredOptionId: id })
  useEffect(() => () => { useHarbor.setState({ hoveredOptionId: null }) }, [alertId])
  return <section className="impact-section"><SectionHeading index="04" title="Response Options" note={options.length ? `${options.length}  options` : 'Awaiting options'} />
    {options.length ? <div className="impact-scroll"><table className="impact-table"><caption className="sr-only">Alert {alertId}  source-provided option metrics. Hover a row to preview restricted zones</caption><thead><tr><th scope="col">Option</th><th scope="col">Berths<br />%</th><th scope="col">Vessels</th><th scope="col">Delay<br />h</th><th scope="col">Risk<br />%</th></tr></thead><tbody>{options.map(option => <tr key={option.id} className={`${option.is_baseline ? 'baseline' : ''} ${effective === option.id ? 'chosen' : ''}`} onMouseEnter={() => hover(option.id)} onMouseLeave={() => hover(null)} onFocus={() => hover(option.id)} onBlur={() => hover(null)}><td><label className="option-label"><input type="radio" name={`option-${alertId}`} value={option.id} checked={effective === option.id} disabled={locked || !!pending || conn === 'replay'} onChange={() => { if (alertId) useHarbor.getState().chooseOption(alertId, option.id) }} /><span>{option.id === rec?.recommended_option_id && <span className="recommended-star" title="Agent recommendation">★ </span>}{englishText(option.label)}{option.is_baseline && <small>Baseline</small>}</span></label></td><td>{numberText(option.berths_open_pct * 100, 0)}%</td><td>{numberText(option.vessels_affected, 0)}</td><td>{numberText(option.delay_vessel_hours)}</td><td>{numberText(option.residual_risk * 100, 0)}%</td></tr>)}</tbody></table><p className="impact-footnote">Metrics from {conn === 'mock' ? 'Local simulated data' : 'Backend'} · Hover an option to preview restrictions</p></div> : <div className="impact-empty"><p>{loading ? 'Loading options…' : englishText(failure) || (alertId ? 'Options are not ready. Waiting for a backend event.' : 'No active alerts.')}</p>{failure && <button onClick={() => { setFailure(null); setRetry(value => value + 1) }}>Reload options</button>}</div>}
  </section>
}
