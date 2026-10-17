import { receiveMessage, useHarbor } from '../store/useHarbor'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
const DELAYS = [1000, 2000, 5000]

export function startLive(): () => void {
  let stopped = false
  let attempt = 0
  let socket: WebSocket | null = null
  let retry: ReturnType<typeof setTimeout> | undefined
  let watchdog: ReturnType<typeof setTimeout> | undefined

  function connect() {
    if (stopped) return
    useHarbor.getState().setConnection('connecting')
    socket = new WebSocket(WS_URL)
    const current = socket
    // A silent half-open connection must also trigger the normal reconnect path.
    const armWatchdog = () => {
      clearTimeout(watchdog)
      watchdog = setTimeout(() => current.close(), 6000)
    }
    armWatchdog()
    current.onopen = () => {
      if (stopped) return
      attempt = 0
      useHarbor.getState().setError(null)
      armWatchdog()
    }
    current.onmessage = event => {
      if (stopped) return
      try {
        if (!receiveMessage(JSON.parse(String(event.data)))) throw new Error('数据格式与共享契约不一致')
        useHarbor.getState().setConnection('live')
        armWatchdog()
      } catch {
        useHarbor.getState().setError('收到无法解析的数据，请和后端核对共享契约 v1。')
      }
    }
    current.onerror = () => current.close()
    current.onclose = () => {
      clearTimeout(watchdog)
      if (stopped) return
      useHarbor.getState().setConnection('disconnected')
      retry = setTimeout(connect, DELAYS[Math.min(attempt++, DELAYS.length - 1)])
    }
  }
  connect()
  return () => {
    stopped = true
    clearTimeout(retry)
    clearTimeout(watchdog)
    socket?.close()
  }
}
