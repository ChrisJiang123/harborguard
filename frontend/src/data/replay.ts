import { receiveMessage, useHarbor } from '../store/useHarbor'
import { useReplay } from '../store/useReplay'
import { createReplayClock, parseReplay, rebuildReplay, replayPath } from './replayCore'

export function startReplay(filename: string): () => void {
  const abort = new AbortController()
  let timer: ReturnType<typeof setInterval> | undefined
  let disposed = false
  useHarbor.getState().setConnection('replay')
  useReplay.setState({ loading: true, filename, position: 0, duration: 0, playing: false, speed: 1, driver: null, error: null })
  void (async () => {
    const response = await fetch(replayPath(filename), { signal: AbortSignal.any([abort.signal, AbortSignal.timeout(15000)]) })
    if (!response.ok) throw new Error(`回放读取失败（HTTP ${response.status}）。请检查 public 中的文件。`)
    if (Number(response.headers.get('content-length')) > 30_000_000) throw new Error('回放文件超过 30 MB。')
    const rows = parseReplay(await response.text())
    if (disposed) return
    const clock = createReplayClock(rows, row => receiveMessage(row.msg), end => useHarbor.setState(rebuildReplay(rows, end, useHarbor.getState())))
    let last = performance.now()
    const sync = () => useReplay.setState(clock.status())
    const tick = () => { const now = performance.now(); clock.tick(now - last); last = now; sync() }
    useReplay.setState({ loading: false, driver: {
      play(value) { tick(); clock.play(value); last = performance.now(); sync() },
      seek(value) { clock.seek(value); last = performance.now(); sync() },
      setSpeed(value) { tick(); clock.setSpeed(value); sync() },
    } })
    sync()
    timer = setInterval(tick, 50)
  })().catch((error: unknown) => {
    if (disposed) return
    const message = error instanceof Error ? error.message : '回放加载失败。'
    useHarbor.getState().setError(message)
    useReplay.setState({ loading: false, error: message })
  })
  return () => { disposed = true; abort.abort(); clearInterval(timer); useReplay.setState({ playing: false, driver: null }) }
}
