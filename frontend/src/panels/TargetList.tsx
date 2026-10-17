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
  const grouped = Object.values(alerts)
  return <section className="targets-section"><SectionHeading index="01" title="分级目标" note={`${grouped.length} 个警报`} />
    {!grouped.length && <div className="empty-state"><span className="empty-symbol">◎</span><strong>{mode === 'disaster' ? '暂无安防警报' : conn === 'live' || conn === 'mock' || conn === 'replay' ? '全港正常' : '等待数据连接'}</strong><p>{mode === 'disaster' ? '当前为灾害模式，右侧显示勘测与复航方案。' : conn === 'mock' ? '场景 A 开始 10 秒后出现一级警报。' : '收到后端状态后将在这里显示目标。'}</p></div>}
    {([3, 2, 1] as const).map(level => {
      const items = grouped.filter(alert => alert.level === level).sort((a, b) => b.risk - a.risk)
      if (!items.length) return null
      return <div className="target-group" key={level}><div className="group-label" style={{ color: LEVEL_COLORS[level] }}><span className="level-dot" style={{ background: LEVEL_COLORS[level] }} />{['', '一级 · 关注', '二级 · 预警', '三级 · 紧急'][level]}<span>{items.length}</span></div>{items.map(alert => {
        const track = tracks[alert.track_id]
        return <button className={`target-row ${selected === alert.track_id ? 'selected' : ''} ${level === 3 ? 'critical-target' : ''}`} key={alert.id} onClick={() => select(selected === alert.track_id ? null : alert.track_id)}>
          <span className="target-row-top"><b>{alert.track_id}</b><span className="muted">{track ? CLASS_NAMES[track.cls] : '等待航迹'}</span><span className="risk-value" style={{ color: LEVEL_COLORS[level] }}>{alert.risk.toFixed(2)}</span></span>
          <span className="target-row-bottom"><span>距资产 {Math.round(alert.distance_m)} m</span><span>ETA {alert.eta_s === null ? '—' : `${Math.ceil(alert.eta_s)}s`}</span></span>
          <span className="risk-meter"><span style={{ width: `${Math.max(0, Math.min(1, alert.risk)) * 100}%`, background: LEVEL_COLORS[level] }} /></span>
        </button>
      })}</div>
    })}
  </section>
}
