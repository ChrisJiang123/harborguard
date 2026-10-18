import { initialData, isHarborMessage, reduceMessage } from '../store/useHarbor'
import type { HarborStore } from '../store/useHarbor'
import type { HarborMsg } from '../types/contract'

export interface ReplayRow { wall_ms: number; msg: HarborMsg }
export function replayPath(filename: string): string {
  if (!/^[a-zA-Z0-9_./-]+\.jsonl$/.test(filename) || filename.startsWith('/') || filename.split('/').some(part => part === '..' || part === '.')) throw new Error('Use a relative JSONL replay path inside public.')
  return `/${filename}`
}
export function parseReplay(text: string): ReplayRow[] {
  if (text.length > 30_000_000) throw new Error('The replay file exceeds 30 MB. Split it and try again.')
  const rows: ReplayRow[] = []
  for (const [index, line] of text.replace(/^\uFEFF/, '').split(/\r?\n/).entries()) {
    if (!line.trim()) continue
    let row: ReplayRow
    try { row = JSON.parse(line) as ReplayRow } catch { throw new Error(`Replay line  ${index + 1}  is not valid JSON.`) }
    if (!row || !Number.isFinite(row.wall_ms) || row.wall_ms < 0 || !isHarborMessage(row.msg)) throw new Error(`Replay line  ${index + 1}  does not match the {wall_ms,msg} contract.`)
    if (rows.length && row.wall_ms < rows.at(-1)!.wall_ms) throw new Error(`Replay line  ${index + 1}  has an out-of-order wall_ms value.`)
    rows.push(row)
    if (rows.length > 200_000) throw new Error('Too many replay messages. Split the file.')
  }
  if (!rows.some(row => row.msg.type === 'state')) throw new Error('A replay must contain at least one state snapshot.')
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
