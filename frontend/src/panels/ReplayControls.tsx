import { useHarbor } from '../store/useHarbor'
import { useReplay } from '../store/useReplay'
import { clock } from '../theme'

export function ReplayControls() {
  const conn = useHarbor(s => s.conn)
  const replay = useReplay()
  if (conn !== 'replay') return null
  return <div className="replay-controls" aria-label="只读回放播放器"><div><strong>只读回放</strong><span title={replay.filename}>{replay.filename}</span></div><button disabled={!replay.driver} onClick={() => replay.driver?.play(!replay.playing)}>{replay.playing ? 'Ⅱ 暂停' : '▶ 播放'}</button><select aria-label="回放速度" disabled={!replay.driver} value={replay.speed} onChange={e => replay.driver?.setSpeed(Number(e.target.value))}><option value="1">1×</option><option value="2">2×</option></select><input type="range" aria-label="回放进度" min="0" max={replay.duration || 1} step="100" value={replay.position} disabled={!replay.driver} onChange={e => replay.driver?.seek(Number(e.target.value))} /><span>{clock(replay.position / 1000)} / {clock(replay.duration / 1000)}</span>{replay.loading && <span>读取中…</span>}{replay.error && <span role="alert">加载失败</span>}</div>
}
