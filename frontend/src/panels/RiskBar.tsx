import { useHarbor } from '../store/useHarbor'
import { activeAlertId, numberText, riskContributions } from './selection'

const COLORS = { C: '#38bdf8', P: '#818cf8', B: '#f59e0b', Z: '#22c55e', D: '#f472b6' }
export function RiskBar() {
  const alertId = useHarbor(activeAlertId)
  const alert = useHarbor(s => alertId ? s.alerts[alertId] : undefined)
  if (!alert) return <section className="risk-section"><div className="risk-title"><h2>风险贡献</h2><span className="muted">暂无活动警报</span></div><p className="muted">选择警报目标后显示 C / P / B / Z / D 分项。</p></section>
  const contributions = riskContributions(alert)
  const sum = contributions.reduce((total, item) => total + item.weighted, 0)
  return <section className="risk-section"><div className="risk-title"><h2>风险贡献 · {alert.track_id}</h2><span>后端总分 <b>{numberText(alert.risk, 2)}</b></span></div><div className="risk-contribution-track" role="img" aria-label={`警报 ${alert.id} 风险贡献，后端总分 ${numberText(alert.risk, 2)}`}>{contributions.map(item => <span key={item.key} style={{ width: `${Math.max(0, Math.min(1, item.weighted)) * 100}%`, background: COLORS[item.key] }} title={`${item.key}：${item.raw} × ${item.weight} = ${numberText(item.weighted, 3)}`} />)}</div><div className="risk-values">{contributions.map(item => <span key={item.key}><i style={{ background: COLORS[item.key] }} />{item.key} {numberText(item.raw, 2)}</span>)}</div>{(!Number.isFinite(sum) || Math.abs(sum - alert.risk) > .01) && <p className="risk-mismatch" role="status">分项与后端总分不一致，请核对契约数据。</p>}</section>
}
