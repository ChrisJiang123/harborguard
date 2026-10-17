export const RECORDING_LIMIT_MS = 180_000
export const RECORDING_MAX_BYTES = 120_000_000
export const RECORDING_MIMES = ['video/webm;codecs=vp8', 'video/webm', 'video/mp4'] as const

interface Callbacks {
  progress: (elapsedMs: number) => void
  complete: (blob: Blob, elapsedMs: number) => void
  error: (message: string) => void
}
export interface RecordingRuntime {
  Recorder: typeof MediaRecorder
  now: () => number
  every: typeof setInterval
  cancelEvery: typeof clearInterval
  later: typeof setTimeout
  cancelLater: typeof clearTimeout
}

export function videoExtension(mime: string): 'mp4' | 'webm' {
  return mime.startsWith('video/mp4') ? 'mp4' : 'webm'
}

// Only receives the screen stream explicitly selected by the user. No camera,
// microphone, upload, browser automation, or automatic permission acceptance.
export function recordStream(stream: MediaStream, callbacks: Callbacks, supplied?: RecordingRuntime) {
  const runtime = supplied ?? { Recorder: MediaRecorder, now: () => performance.now(), every: setInterval, cancelEvery: clearInterval, later: setTimeout, cancelLater: clearTimeout }
  let recorder: MediaRecorder
  try {
    const mimeType = RECORDING_MIMES.find(mime => runtime.Recorder.isTypeSupported(mime))
    if (!mimeType) throw new Error('浏览器不支持本页视频格式，请使用系统录屏。')
    recorder = new runtime.Recorder(stream, { mimeType, videoBitsPerSecond: 4_000_000 })
  } catch (error) { stream.getTracks().forEach(track => track.stop()); throw error }
  const chunks: Blob[] = []
  const started = runtime.now()
  let bytes = 0, done = false, cancelled = false, failed = false
  let ticker: ReturnType<typeof setInterval> | undefined
  let deadline: ReturnType<typeof setTimeout> | undefined
  const elapsed = () => Math.max(0, runtime.now() - started)
  const release = () => {
    runtime.cancelEvery(ticker); runtime.cancelLater(deadline)
    stream.getVideoTracks().forEach(track => track.removeEventListener('ended', stop))
    stream.getTracks().forEach(track => track.stop())
    recorder.ondataavailable = null; recorder.onerror = null; recorder.onstop = null
  }
  const finish = () => {
    if (done) return
    done = true; release()
    if (!cancelled && !failed) {
      const blob = new Blob(chunks, { type: recorder.mimeType })
      if (blob.size) callbacks.complete(blob, elapsed())
      else callbacks.error('未收到视频数据，请重新录制或使用系统录屏。')
    }
    chunks.length = 0
  }
  function stop() {
    if (done) return
    if (recorder.state === 'inactive') { finish(); return }
    try { recorder.stop() } catch { failed = true; callbacks.error('停止录屏失败，请使用浏览器“停止共享”。'); finish() }
  }
  recorder.ondataavailable = event => {
    if (done || failed || cancelled || !event.data.size) return
    bytes += event.data.size
    if (bytes > RECORDING_MAX_BYTES) { failed = true; callbacks.error('视频数据超过 120 MB，本次录制已终止，请降低分辨率后重试。'); stop(); return }
    chunks.push(event.data)
  }
  recorder.onstop = finish
  recorder.onerror = () => { failed = true; callbacks.error('浏览器录制发生错误，本次视频不可用。'); stop() }
  try {
    recorder.start(1000)
    stream.getVideoTracks().forEach(track => track.addEventListener('ended', stop, { once: true }))
    ticker = runtime.every(() => { callbacks.progress(elapsed()); if (elapsed() >= RECORDING_LIMIT_MS) stop() }, 250)
    deadline = runtime.later(stop, RECORDING_LIMIT_MS)
  } catch (error) { done = true; release(); throw error }
  return { stop, cancel() { cancelled = true; stop() } }
}
