import { useHarbor } from '../store/useHarbor'
import { useReplay } from '../store/useReplay'
import { clock } from '../theme'

export function ReplayControls() {
  const conn = useHarbor(s => s.conn)
  const replay = useReplay()
  if (conn !== 'replay') return null
  return <div className="replay-controls" aria-label="Read-only replay player"><div><strong>Read-only Replay</strong><span title={replay.filename}>{replay.filename}</span></div><button disabled={!replay.driver} onClick={() => replay.driver?.play(!replay.playing)}>{replay.playing ? 'Ⅱ Pause' : '▶ Play'}</button><select aria-label="Replay speed" disabled={!replay.driver} value={replay.speed} onChange={e => replay.driver?.setSpeed(Number(e.target.value))}><option value="1">1×</option><option value="2">2×</option></select><input type="range" aria-label="Replay progress" min="0" max={replay.duration || 1} step="100" value={replay.position} disabled={!replay.driver} onChange={e => replay.driver?.seek(Number(e.target.value))} /><span>{clock(replay.position / 1000)} / {clock(replay.duration / 1000)}</span>{replay.loading && <span>Loading…</span>}{replay.error && <span role="alert">Load failed</span>}</div>
}
