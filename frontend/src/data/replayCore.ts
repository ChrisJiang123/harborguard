import { initialData, isHarborMessage, reduceMessage } from '../store/useHarbor'
import type { HarborStore } from '../store/useHarbor'
import type { HarborMsg } from '../types/contract'

export interface ReplayRow { wall_ms: number; msg: HarborMsg }
export function replayPath(filename: string): string {
  if (!/^[a-zA-Z0-9_./-]+\.jsonl$/.test(filename) || filename.startsWith('/') || filename.split('/').some(part => part === '..' || part === '.')) throw new Error('回放文件须为 public 内的相对 JSONL 路径。')
  return `/${filename}`
}
export function parseReplay(text: string): ReplayRow[] {
  if (text.length > 30_000_000) throw new Error('回放文件超过 30 MB，请拆分后重试。')
  const rows: ReplayRow[] = []
  for (const [index, line] of text.replace(/^\uFEFF/, '').split(/\r?\n/).entries()) {
    if (!line.trim()) continue
    let row: ReplayRow
    try { row = JSON.parse(line) as ReplayRow } catch { throw new Error(`回放第 ${index + 1} 行不是有效 JSON。`) }
    if (!row || !Number.isFinite(row.wall_ms) || row.wall_ms < 0 || !isHarborMessage(row.msg)) throw new Error(`回放第 ${index + 1} 行不符合 {wall_ms,msg} 契约。`)
    if (rows.length && row.wall_ms < rows.at(-1)!.wall_ms) throw new Error(`回放第 ${index + 1} 行的 wall_ms 倒序。`)
    rows.push(row)
    if (rows.length > 200_000) throw new Error('回放消息过多，请拆分文件。')
  }
  if (!rows.some(row => row.msg.type === 'state')) throw new Error('回放至少需要一条状态快照。')
  return rows
}
export function rebuildReplay(rows: ReplayRow[], end: number, current: HarborStore): HarborStore {
  let state: HarborStore = { ...current, ...initialData(), view: current.view, conn: 'replay', session: current.session + 1 }
  // File order matters at equal wall times. Snapshot-only seeks lose event caches.
  for (let i = 0; i < end; i++) state = { ...state, ...reduceMessage(state, rows[i]!.msg) }
  return state
}
export function createReplayClock(rows: ReplayRow[], publish: (row: ReplayRow) => void, rebuild: (end: number) => void) {
  const first = rows[0]!.wall_ms
  const duration = rows.at(-1)!.wall_ms - first
  let position = 0, cursor = 0, playing = false, speed = 1
  const seek = (value: number) => {
    position = Math.min(duration, Math.max(0, Number.isFinite(value) ? value : 0))
    cursor = 0
    while (cursor < rows.length && rows[cursor]!.wall_ms <= first + position) cursor++
    rebuild(cursor)
    if (position === duration) playing = false
  }
  seek(0)
  return {
    status: () => ({ position, duration, playing, speed }), seek,
    play(value: boolean) { if (value && position >= duration) seek(0); playing = value && duration > 0 },
    setSpeed(value: number) { if (value === 1 || value === 2) speed = value },
    tick(elapsed: number) {
      if (!playing || !Number.isFinite(elapsed) || elapsed <= 0) return
      position = Math.min(duration, position + elapsed * speed)
      while (cursor < rows.length && rows[cursor]!.wall_ms <= first + position) publish(rows[cursor++]!)
      if (position === duration) playing = false
    },
  }
}
