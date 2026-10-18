import { englishText, hasHanText, ENGLISH_UNAVAILABLE } from '../data/english'
import { useEffect, useRef, useState } from 'react'
import { useShallow } from 'zustand/react/shallow'
import { api } from '../data/api'
import { localSonarPath } from '../data/presentation'
import { useHarbor } from '../store/useHarbor'
import { useMapData } from '../store/useMapData'
import { notify, runOperation, useOperations } from '../store/useOperations'
import { CLASS_NAMES, clock } from '../theme'
import type { Option, Recommendation } from '../types/contract'
import { activeAlertId, effectiveOptionId } from './selection'
import { SectionHeading } from './SectionHeading'

const EMPTY: Option[] = []
const MODELS = { cloud: 'Cloud', local: 'Local LoRA', template: 'Template' }
const CONFIDENCE = { low: 'Low', medium: 'Medium', high: 'High' }

function EvidenceChips({ recommendation }: { recommendation: Recommendation }) {
  const trackIds = useHarbor(useShallow(s => Object.keys(s.tracks)))
  const detections = useHarbor(s => s.detections)
  const zones = useMapData(s => s.resources?.zones)
  const open = (id: string) => {
    if (trackIds.includes(id)) { useHarbor.getState().selectTrack(id); return }
    if (zones?.features.some(zone => zone.properties.id === id)) { useHarbor.setState({ focusedZoneId: id, view: '2d' }); return }
    if (detections[id]) { useHarbor.setState({ sonarModalDetId: id }); return }
    if (id.startsWith('det-')) void runOperation('Load detection record', async () => {
      const session = useHarbor.getState().session
      const detection = await api.detection(id)
      if (useHarbor.getState().session !== session) return
      useHarbor.getState().cacheDetection(detection)
      useHarbor.setState({ sonarModalDetId: id })
    })
  }
  return <div className="evidence-chips" aria-label="Recommendation evidence">{recommendation.evidence_ids.map(id => {
    const available = trackIds.includes(id) || !!detections[id] || id.startsWith('det-') || zones?.features.some(zone => zone.properties.id === id)
    return <button key={id} disabled={!available} onClick={() => open(id)} title={available ? `Locate evidence ${id}` : 'Waiting for evidence'}>{id}</button>
  })}</div>
}

export function AgentCard() {
  const alertId = useHarbor(activeAlertId)
  const selected = useHarbor(s => s.selectedTrackId)
  const rec = useHarbor(s => alertId ? s.recByAlert[alertId] : !s.selectedTrackId && s.latestRec?.alert_id === null ? s.latestRec : null)
  const options = useHarbor(s => alertId ? s.optionsByAlert[alertId] : undefined) ?? EMPTY
  const chosen = useHarbor(s => s.chosenOptionId)
  const chosenFor = useHarbor(s => s.chosenOptionAlertId)
  const conn = useHarbor(s => s.conn)
  const mode = useHarbor(s => s.latest?.mode)
  const confirmed = useHarbor(s => alertId ? s.decisionsByAlert[alertId] : undefined)
  const requested = useHarbor(s => alertId ? s.decisionRequests[alertId] : undefined)
  const uncertain = useHarbor(s => alertId ? s.uncertainDecisions[alertId] : undefined)
  const recovery = useHarbor(s => s.recovery)
  const pending = useOperations(s => s.pending)
  const [operator, setOperator] = useState('Operator A')
  const effective = effectiveOptionId(alertId, options, rec, chosen, chosenFor)
  const locked = !!pending || !!confirmed || !!requested || !!uncertain || !effective || !operator.trim() || (conn !== 'live' && conn !== 'mock')
  const decide = (action: 'approve' | 'reject') => {
    if (!alertId || !effective || locked) return
    void runOperation(action === 'approve' ? 'Approve option' : 'Reject option', async () => {
      await api.decide({ alert_id: alertId, option_id: effective, action, operator: operator.trim() })
      if (action === 'reject' && useHarbor.getState().uncertainDecisions[alertId]) notify('The rejection request was accepted, but no structured decision event was returned. Status is unconfirmed.')
      else if (useHarbor.getState().decisionRequests[alertId]) notify('Request sent. Waiting for a backend decision event.')
    })
  }
  return <section className="agent-section"><SectionHeading index="03" title="Agent Recommendation" note={alertId ?? 'Standby'} />
    {rec ? <div className="agent-body"><div className="agent-meta"><span className={`model-badge ${rec.model}`}>{MODELS[rec.model]}</span><span>Confidence: {CONFIDENCE[rec.confidence]}</span></div><h3>{englishText(rec.summary)}</h3>{[rec.summary,rec.explanation,...rec.uncertainties].some(hasHanText) && <p className="muted">{[rec.summary,rec.explanation,...rec.uncertainties].some(text => englishText(text) === ENGLISH_UNAVAILABLE) ? 'Some source text has no English translation' : 'English display translation'} · Original source record retained</p>}<details className="agent-explanation"><summary>View recommendation details</summary><p>{englishText(rec.explanation)}</p></details>
      {rec.uncertainties.length > 0 && <ul className="uncertainty-list">{rec.uncertainties.map((text, index) => <li key={index}>{englishText(text)}</li>)}</ul>}
      <EvidenceChips recommendation={rec} />
      {alertId && <div className="decision-area"><label className="operator-label">Operator<input aria-label="Operator name" value={operator} maxLength={32} onChange={event => setOperator(event.target.value)} disabled={!!pending || !!confirmed || !!requested || !!uncertain} /></label>
        {effective ? <p className="decision-option">Selected option: {englishText(options.find(option => option.id === effective)?.label)}</p> : <p className="decision-option muted">Select an available option below first.</p>}
        <div className="decision-buttons"><button className="approve-button" disabled={locked} onClick={() => decide('approve')}>{pending === 'Approve option' ? 'Approving…' : 'Approve'}</button><button className="reject-button" disabled={locked} onClick={() => decide('reject')}>{pending === 'Reject option' ? 'Rejecting…' : 'Reject'}</button></div>
        {confirmed && <p className={`decision-confirmed ${confirmed.action}`} role="status">{confirmed.action === 'approve' ? 'Approved' : 'Rejected'} · {clock(confirmed.t)} · {englishText(confirmed.operator)}</p>}
        {requested && !confirmed && <p className="decision-waiting" role="status">Waiting for a structured backend decision. Do not submit again.</p>}
        {uncertain && !confirmed && <p className="decision-uncertain" role="status">Unconfirmed: the rejection request was accepted, but the current contract provides no structured rejection event.</p>}
        {!requested && !uncertain && !confirmed && conn === 'live' && recovery.phase === 'loading' && <p className="decision-waiting" role="status">Restoring approval history…</p>}
        {!requested && !uncertain && !confirmed && conn === 'live' && (recovery.phase === 'complete' || recovery.phase === 'partial' || recovery.phase === 'failed') && <p className="decision-uncertain" role="status">No structured decision received. The historical status is unconfirmed.</p>}
      </div>}
    </div> : <div className="agent-body"><div className="agent-waiting"><span>✦</span><strong>{selected && !alertId ? 'No active alert for this target' : mode === 'disaster' ? 'Waiting for survey and reopening recommendations' : 'Waiting for alerts and response recommendations'}</strong></div><p>{mode === 'disaster' ? 'Disaster mode shows reopening recommendations from the data source.' : 'Select a target to see its recommendation. Otherwise, the highest-level active alert is shown.'}</p>{confirmed && <p className={`decision-confirmed ${confirmed.action}`} role="status">This alert is {confirmed.action === 'approve' ? 'Approved' : 'Rejected'} · {clock(confirmed.t)} · {englishText(confirmed.operator)}</p>}{requested && !confirmed && <p className="decision-waiting" role="status">Request submitted. Waiting for a structured backend decision.</p>}{uncertain && !confirmed && <p className="decision-uncertain" role="status">Unconfirmed: no structured rejection event was returned.</p>}{alertId && !confirmed && !requested && !uncertain && conn === 'live' && recovery.phase !== 'idle' && <p className="decision-uncertain" role="status">No structured recommendation or decision can be restored. Historical status is unconfirmed.</p>}{conn === 'mock' && <p className="hint">{mode === 'disaster' ? 'Scenario B generates a template recommendation at 45 s.' : 'Scenario A generates a template recommendation at 66 s.'}{' '}Use 10× speed to accelerate.</p>}</div>}
  </section>
}

export function DetectionPreview() {
  const id = useHarbor(s => s.sonarModalDetId)
  const detection = useHarbor(s => id ? s.detections[id] : undefined)
  const dialog = useRef<HTMLDialogElement>(null)
  const conn = useHarbor(s => s.conn)
  useEffect(() => {
    if (id && !dialog.current?.open) dialog.current?.showModal()
    else if (!id && dialog.current?.open) dialog.current.close()
  }, [id])
  return <dialog ref={dialog} className="detection-dialog" onClose={() => useHarbor.setState({ sonarModalDetId: null })} onClick={event => { if (event.target === event.currentTarget) dialog.current?.close() }} aria-labelledby="detection-title"><div className="dialog-content"><div className="dialog-heading"><h2 id="detection-title">Detection Record · {id}</h2><button onClick={() => dialog.current?.close()} aria-label="Close detection record">×</button></div>{detection ? <><dl><dt>Class</dt><dd>{CLASS_NAMES[detection.cls]}</dd><dt>Confidence</dt><dd>{Math.round(detection.conf * 100)}%</dd><dt>Buoy</dt><dd>{detection.buoy_id}</dd><dt>Model</dt><dd>{detection.model}</dd><dt>Time</dt><dd>{clock(detection.t)}</dd></dl><SonarImage key={`${conn}-${detection.id}`} src={conn === 'mock' || conn === 'replay' ? localSonarPath(detection) : api.sonarURL(detection.id)} />{detection.model === 'stub' && <p className="training">Synthetic illustration · Not actual sonar or trained-model output</p>}<p className="muted">Source-provided annotated image. The frontend does not rerun inference or draw detection boxes.</p></> : <p>Waiting for a detection record.</p>}</div></dialog>
}

function SonarImage({ src }: { src: string }) {
  const [failed, setFailed] = useState(false)
  const [revision, setRevision] = useState(0)
  return <div className="sonar-image">{failed ? <div role="alert"><p>Sonar image is unavailable or failed to load.</p><button onClick={() => { setFailed(false); setRevision(value => value + 1) }}>Retry image</button></div> : <img key={revision} src={src} alt="Source-annotated sonar detection image; stub images are synthetic" onError={() => setFailed(true)} />}</div>
}
