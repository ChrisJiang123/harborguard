import { useEffect, useRef, useState } from 'react'
import { useRecording } from '../demo/useRecording'
import { clock } from '../theme'
import { notify } from '../store/useOperations'

export function DemoTools() {
  const [open, setOpen] = useState(false)
  const [viewport, setViewport] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  const recording = useRecording()
  const busy = recording.status === 'recording' || recording.status === 'choosing'
  useEffect(() => {
    const update = () => setViewport(`${window.innerWidth} × ${window.innerHeight}`)
    update(); window.addEventListener('resize', update)
    return () => window.removeEventListener('resize', update)
  }, [])
  useEffect(() => {
    const node = dialog.current
    if (!node) return
    if (open && !node.open) node.showModal()
    if (!open && node.open) node.close()
  }, [open])
  const fullscreen = () => {
    setOpen(false)
    const operation = document.fullscreenElement ? document.exitFullscreen() : document.documentElement.requestFullscreen?.()
    if (!operation) { notify('Page fullscreen is unavailable. Use the browser fullscreen shortcut.', 'error'); return }
    void operation.catch(() => notify('Could not enter fullscreen. Use the browser fullscreen shortcut.', 'error'))
  }
  return <><button className="demo-tools-button" onClick={() => setOpen(true)}>Demo Setup</button>
    {busy && <div className="recording-banner" role="status"><span>● {recording.status === 'choosing' ? 'Waiting for you to select a shared tab' : `Recording ${clock(recording.elapsed / 1000)} / 03:00 · No audio`}</span>{recording.status === 'recording' && <button onClick={recording.stop}>Stop recording</button>}<button onClick={() => setOpen(true)}>Open recording panel</button></div>}
    {recording.status === 'ready' && !open && <button className="recording-ready" onClick={() => setOpen(true)}>Recording ready · Open to save</button>}
    <dialog ref={dialog} className="demo-dialog" aria-labelledby="demo-title" onClose={() => setOpen(false)} onClick={event => { if (event.target === event.currentTarget) setOpen(false) }}><div className="dialog-content"><div className="dialog-heading"><h2 id="demo-title">Presentation & Recording Setup</h2><button aria-label="Close demo setup" onClick={() => setOpen(false)}>×</button></div>
      <p>Current viewport: <strong>{viewport}</strong>. Presentation target: 1920 × 1080, body text at least 14 px and key figures at least 20 px. Verify readability from 3 m on the projector.</p><div className="demo-action-row"><button onClick={fullscreen}>Toggle fullscreen</button><a href="/?replay=demo_full.jsonl">Open 3-minute simulated replay</a></div>
      <h3>Backup Video Recording</h3><p>Records only the display selected in the browser dialog, without microphone or system audio, for up to 3 minutes. Select the HarborGuard tab. Video stays on this device.</p><p className="muted">Open the page before recording. Do not reload, change data source, or close it while recording. A replay file is not a video; record and download a backup video separately.</p>
      <div className="demo-action-row"><button disabled={busy || !!recording.result} onClick={() => { void recording.start() }}>{recording.status === 'choosing' ? 'Waiting for tab selection…' : 'Select tab & start recording'}</button><button disabled={recording.status !== 'recording'} onClick={recording.stop}>Stop recording</button></div>
      {recording.status === 'recording' && <p role="status">Recording: {clock(recording.elapsed / 1000)} / 03:00. You can close this panel and continue the demo.</p>}{recording.error && <p role="alert" className="demo-error">{recording.error}</p>}
      {recording.result && <div className="recording-result"><p>Created {clock(recording.elapsed / 1000)} video. Download it and verify playback.</p><video controls preload="metadata" src={recording.result.url} aria-label="Recording preview" /><div className="demo-action-row"><a href={recording.result.url} download={recording.result.filename}>Download recording</a><button onClick={recording.discard}>Clear local preview & record again</button></div><p className="muted">Clears this page preview only; downloaded files are unchanged. Reloading or closing the page prevents another download.</p></div>}
      <h3>3-minute Simulated Demo</h3><ol className="demo-route"><li>00:00–00:35: Scenario A tracking and alert escalation.</li><li>00:35–01:06: Sonar evidence, Level 3 alert, and template recommendation.</li><li>01:06–01:20: Review options; simulated approval appears at 01:10.</li><li>01:20–02:05: Switch to Scenario B; inspect survey zones and reopening recommendations.</li><li>02:05–03:00: Buoy outage and simulated network loss; switch between 2D and 3D.</li></ol><p className="muted">This is a synthetic replay, not actual backend output. A simulated network outage does not disable Wi-Fi. Use a system recorder or OBS if browser recording is unavailable.</p>
    </div></dialog></>
}
