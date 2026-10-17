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
// local 目前是 Ollama 基座（qwen3:1.7b）；harborguard-lora 部署后如需标"本地 LoRA"再改回。
// 在 LoRA 未部署前不得把本地路由标成已训练 LoRA（演示集成验收第 6 条）。
const MODELS = { cloud: '云端', local: '本地模型', template: '模板' }
const CONFIDENCE = { low: '低', medium: '中', high: '高' }

function EvidenceChips({ recommendation }: { recommendation: Recommendation }) {
  const trackIds = useHarbor(useShallow(s => Object.keys(s.tracks)))
  const detections = useHarbor(s => s.detections)
  const zones = useMapData(s => s.resources?.zones)
  const open = (id: string) => {
    if (trackIds.includes(id)) { useHarbor.getState().selectTrack(id); return }
    if (zones?.features.some(zone => zone.properties.id === id)) { useHarbor.setState({ focusedZoneId: id, view: '2d' }); return }
    if (detections[id]) { useHarbor.setState({ sonarModalDetId: id }); return }
    if (id.startsWith('det-')) void runOperation('读取识别记录', async () => {
      const session = useHarbor.getState().session
      const detection = await api.detection(id)
      if (useHarbor.getState().session !== session) return
      useHarbor.getState().cacheDetection(detection)
      useHarbor.setState({ sonarModalDetId: id })
    })
  }
  return <div className="evidence-chips" aria-label="建议证据">{recommendation.evidence_ids.map(id => {
    const available = trackIds.includes(id) || !!detections[id] || id.startsWith('det-') || zones?.features.some(zone => zone.properties.id === id)
    return <button key={id} disabled={!available} onClick={() => open(id)} title={available ? `定位证据 ${id}` : '等待对应证据数据'}>{id}</button>
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
  const pending = useOperations(s => s.pending)
  const [operator, setOperator] = useState('操作员 A')
  const effective = effectiveOptionId(alertId, options, rec, chosen, chosenFor)
  const locked = !!pending || !!confirmed || !!requested || !effective || !operator.trim() || (conn !== 'live' && conn !== 'mock')
  const decide = (action: 'approve' | 'reject') => {
    if (!alertId || !effective || locked) return
    void runOperation(action === 'approve' ? '批准方案' : '驳回方案', async () => {
      await api.decide({ alert_id: alertId, option_id: effective, action, operator: operator.trim() })
      if (useHarbor.getState().decisionRequests[alertId]) notify('操作请求已送达，等待后端决策事件确认。')
    })
  }
  return <section className="agent-section"><SectionHeading index="03" title="Agent 建议" note={alertId ?? '待命'} />
    {rec ? <div className="agent-body"><div className="agent-meta"><span className={`model-badge ${rec.model}`}>{MODELS[rec.model]}</span><span>置信度：{CONFIDENCE[rec.confidence]}</span></div><h3>{rec.summary}</h3><details className="agent-explanation"><summary>查看建议解读</summary><p>{rec.explanation}</p></details>
      {rec.uncertainties.length > 0 && <ul className="uncertainty-list">{rec.uncertainties.map((text, index) => <li key={index}>{text}</li>)}</ul>}
      <EvidenceChips recommendation={rec} />
      {alertId && <div className="decision-area"><label className="operator-label">操作员<input aria-label="操作员名称" value={operator} maxLength={32} onChange={event => setOperator(event.target.value)} disabled={!!pending || !!confirmed || !!requested} /></label>
        {effective ? <p className="decision-option">当前方案：{options.find(option => option.id === effective)?.label}</p> : <p className="decision-option muted">请先在下方选择一个可用方案。</p>}
        <div className="decision-buttons"><button className="approve-button" disabled={locked} onClick={() => decide('approve')}>{pending === '批准方案' ? '批准中…' : '批准'}</button><button className="reject-button" disabled={locked} onClick={() => decide('reject')}>{pending === '驳回方案' ? '驳回中…' : '驳回'}</button></div>
        {confirmed && <p className={`decision-confirmed ${confirmed.action}`} role="status">{confirmed.action === 'approve' ? '已批准' : '已驳回'} · {clock(confirmed.t)} · {confirmed.operator}</p>}
        {requested && !confirmed && <p className="decision-waiting" role="status">等待后端确认，请勿重复操作。</p>}
      </div>}
    </div> : <div className="agent-body"><div className="agent-waiting"><span>✦</span><strong>{selected && !alertId ? '该目标暂无活动警报' : mode === 'disaster' ? '等待勘测与复航建议' : '等待警报与处置建议'}</strong></div><p>{mode === 'disaster' ? '灾害模式下显示数据源发来的复航建议。' : '选中目标后显示对应建议；未选中时显示等级最高的活动警报。'}</p>{conn === 'mock' && <p className="hint">{mode === 'disaster' ? '场景 B 第 45 秒生成模板建议。' : '场景 A 第 66 秒生成模板建议。'}可使用 10× 加速。</p>}</div>}
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
  return <dialog ref={dialog} className="detection-dialog" onClose={() => useHarbor.setState({ sonarModalDetId: null })} onClick={event => { if (event.target === event.currentTarget) dialog.current?.close() }} aria-labelledby="detection-title"><div className="dialog-content"><div className="dialog-heading"><h2 id="detection-title">识别记录 · {id}</h2><button onClick={() => dialog.current?.close()} aria-label="关闭识别记录">×</button></div>{detection ? <><dl><dt>类别</dt><dd>{CLASS_NAMES[detection.cls]}</dd><dt>置信度</dt><dd>{Math.round(detection.conf * 100)}%</dd><dt>浮标</dt><dd>{detection.buoy_id}</dd><dt>模型</dt><dd>{detection.model}</dd><dt>时间</dt><dd>{clock(detection.t)}</dd></dl><SonarImage key={`${conn}-${detection.id}`} src={conn === 'mock' || conn === 'replay' ? localSonarPath(detection) : api.sonarURL(detection.id)} />{detection.model === 'stub' && <p className="training">合成示意图 · 非真实声呐 / 非训练模型输出</p>}<p className="muted">展示数据源预标框图像，前端不重复推理或绘制检测框。</p></> : <p>等待识别记录。</p>}</div></dialog>
}

function SonarImage({ src }: { src: string }) {
  const [failed, setFailed] = useState(false)
  const [revision, setRevision] = useState(0)
  return <div className="sonar-image">{failed ? <div role="alert"><p>声呐图像未提供或加载失败。</p><button onClick={() => { setFailed(false); setRevision(value => value + 1) }}>重试图像</button></div> : <img key={revision} src={src} alt="数据源已标框的声呐识别图；stub 为合成示意图" onError={() => setFailed(true)} />}</div>
}
