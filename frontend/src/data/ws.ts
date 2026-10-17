import { isHarborMessage, receiveMessage, useHarbor } from '../store/useHarbor'
import { beginLiveRecoveryGeneration, invalidateLiveRecoveryGeneration, recoverLiveFromBackend } from './liveRecovery'

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
const DELAYS = [1000, 2000, 5000]

export function startLive(): () => void {
  let stopped = false
  let attempt = 0
  let socket: WebSocket | null = null
  let retry: ReturnType<typeof setTimeout> | undefined
  let watchdog: ReturnType<typeof setTimeout> | undefined
  let recovery: AbortController | undefined

  function connect() {
    if (stopped) return
    // Capture before opening the socket; later WebSocket state updates must not
    // change the baseline used to identify a backend sequence reset.
    const previousSnapshotSeq = useHarbor.getState().latest?.seq
    const generation = beginLiveRecoveryGeneration()
    useHarbor.getState().setConnection('connecting')
    socket = new WebSocket(WS_URL)
    const current = socket
    let recoveryStarted = false
    // A silent half-open connection must also trigger the normal reconnect path.
    const armWatchdog = () => {
      clearTimeout(watchdog)
      watchdog = setTimeout(() => current.close(), 6000)
    }
    armWatchdog()
    current.onopen = () => {
      if (stopped || current !== socket) return
      attempt = 0
      useHarbor.getState().setError(null)
      armWatchdog()
    }
    current.onmessage = event => {
      if (stopped || current !== socket) return
      try {
        const message: unknown = JSON.parse(String(event.data))
        const isInitialState = !recoveryStarted && typeof message === 'object' && message !== null && (message as { type?: unknown }).type === 'state'
        if (isInitialState && isHarborMessage(message) && previousSnapshotSeq !== undefined && message.seq < previousSnapshotSeq) {
          // Clear stale decisions/events synchronously, before ingesting the
          // first snapshot from the restarted backend session.
          useHarbor.getState().reset()
        }
        if (!receiveMessage(message)) throw new Error('数据格式与共享契约不一致')
        useHarbor.getState().setConnection('live')
        if (isInitialState) {
          recoveryStarted = true
          recovery?.abort()
          recovery = new AbortController()
          const session = useHarbor.getState().session
          useHarbor.getState().setRecoveryLoading(session)
          void recoverLiveFromBackend(message as import('../types/contract').StateMsg, recovery.signal, { generation, session, previousSnapshotSeq })
        }
        armWatchdog()
      } catch {
        useHarbor.getState().setError('收到无法解析的数据，请和后端核对共享契约 v1。')
      }
    }
    current.onerror = () => current.close()
    current.onclose = () => {
      if (current !== socket) return
      clearTimeout(watchdog)
      recovery?.abort()
      invalidateLiveRecoveryGeneration(generation)
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
    recovery?.abort()
    socket?.close()
  }
}
