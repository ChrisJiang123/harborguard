import { useEffect, useRef, useState } from 'react'
import { recordStream, videoExtension } from './recording'

type RecordingStatus = 'idle' | 'choosing' | 'recording' | 'ready' | 'error'
export function useRecording() {
  const [status, setStatus] = useState<RecordingStatus>('idle')
  const [elapsed, setElapsed] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ url: string; filename: string } | null>(null)
  const active = useRef<ReturnType<typeof recordStream> | null>(null)
  const choosing = useRef(false)
  const mounted = useRef(false)
  const blobURL = useRef<string | null>(null)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; active.current?.cancel(); if (blobURL.current) URL.revokeObjectURL(blobURL.current) }
  }, [])
  useEffect(() => {
    if (!['choosing', 'recording', 'ready'].includes(status)) return
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', warn)
    return () => window.removeEventListener('beforeunload', warn)
  }, [status])
  const start = async () => {
    if (active.current || choosing.current || blobURL.current) return
    if (!navigator.mediaDevices?.getDisplayMedia || typeof MediaRecorder === 'undefined') { setError('当前浏览器不支持页面录屏，请使用系统录屏或 OBS。'); setStatus('error'); return }
    choosing.current = true; setStatus('choosing'); setError(null); setElapsed(0)
    try {
      // Must stay directly in the button's user-activation chain. Never request audio.
      const stream = await navigator.mediaDevices.getDisplayMedia({ video: { width: { ideal: 1920 }, height: { ideal: 1080 }, frameRate: { ideal: 30, max: 30 } }, audio: false })
      if (!mounted.current) { stream.getTracks().forEach(track => track.stop()); return }
      if (!stream.getVideoTracks().length) { stream.getTracks().forEach(track => track.stop()); throw new Error('未选择可录制画面。') }
      active.current = recordStream(stream, {
        progress(ms) { if (mounted.current) setElapsed(ms) },
        complete(blob, ms) {
          active.current = null
          if (!mounted.current) return
          blobURL.current = URL.createObjectURL(blob)
          setResult({ url: blobURL.current, filename: `HarborGuard-demo-${new Date().toISOString().replace(/[:.]/g, '-')}.${videoExtension(blob.type)}` })
          setElapsed(ms); setStatus('ready')
        },
        error(message) { active.current = null; if (mounted.current) { setError(message); setStatus('error') } },
      })
      setStatus('recording')
    } catch (cause) {
      if (mounted.current) { setError(cause instanceof Error && cause.name === 'NotAllowedError' ? '未授权或已取消共享，未开始录屏。' : cause instanceof Error ? cause.message : '无法开始录屏。'); setStatus('error') }
    } finally { choosing.current = false }
  }
  const discard = () => {
    if (active.current || choosing.current) return
    if (blobURL.current) URL.revokeObjectURL(blobURL.current)
    blobURL.current = null; setResult(null); setElapsed(0); setError(null); setStatus('idle')
  }
  return { status, elapsed, error, result, start, stop: () => active.current?.stop(), discard }
}
