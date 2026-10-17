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
    if (!operation) { notify('当前浏览器不支持页面全屏，请使用浏览器全屏快捷键。', 'error'); return }
    void operation.catch(() => notify('无法进入全屏，请使用浏览器全屏快捷键。', 'error'))
  }
  return <><button className="demo-tools-button" onClick={() => setOpen(true)}>演示准备</button>
    {busy && <div className="recording-banner" role="status"><span>● {recording.status === 'choosing' ? '等待你选择共享页面' : `正在录屏 ${clock(recording.elapsed / 1000)} / 03:00 · 无声音`}</span>{recording.status === 'recording' && <button onClick={recording.stop}>停止录屏</button>}<button onClick={() => setOpen(true)}>打开录屏面板</button></div>}
    {recording.status === 'ready' && !open && <button className="recording-ready" onClick={() => setOpen(true)}>录屏已生成 · 打开保存</button>}
    <dialog ref={dialog} className="demo-dialog" aria-labelledby="demo-title" onClose={() => setOpen(false)} onClick={event => { if (event.target === event.currentTarget) setOpen(false) }}><div className="dialog-content"><div className="dialog-heading"><h2 id="demo-title">投屏与录屏准备</h2><button aria-label="关闭演示准备" onClick={() => setOpen(false)}>×</button></div>
      <p>当前网页视口：<strong>{viewport}</strong>。投屏目标为 1920 × 1080，正文至少 14px，关键数字至少 20px；仍需在投影仪上从 3 米外确认可读。</p><div className="demo-action-row"><button onClick={fullscreen}>切换全屏</button><a href="/?replay=demo_full.jsonl">打开三分钟模拟回放</a></div>
      <h3>备用视频录制</h3><p>只录制你在浏览器提示中亲自选择的画面，不录麦克风或系统声音，最多 3 分钟。请只选择 HarborGuard 页签，避免带入其他窗口的私人信息。视频留在本机，不上传。</p><p className="muted">请先打开要录制的页面，再开始录屏；录制中不要刷新、跳转数据源或关闭本页。回放文件不是视频，只有实际录制并下载后才有备用视频。</p>
      <div className="demo-action-row"><button disabled={busy || !!recording.result} onClick={() => { void recording.start() }}>{recording.status === 'choosing' ? '等待选择页面…' : '选择页面并开始录屏'}</button><button disabled={recording.status !== 'recording'} onClick={recording.stop}>停止录屏</button></div>
      {recording.status === 'recording' && <p role="status">正在录制：{clock(recording.elapsed / 1000)} / 03:00。可关闭此面板继续演示。</p>}{recording.error && <p role="alert" className="demo-error">{recording.error}</p>}
      {recording.result && <div className="recording-result"><p>已生成 {clock(recording.elapsed / 1000)} 视频，请下载后确认可播放。</p><video controls preload="metadata" src={recording.result.url} aria-label="本次录屏预览" /><div className="demo-action-row"><a href={recording.result.url} download={recording.result.filename}>下载本次录屏</a><button onClick={recording.discard}>清除本页副本并重录</button></div><p className="muted">清除只影响本页内存副本，不删除已下载文件。刷新或关闭本页后将无法重新下载。</p></div>}
      <h3>三分钟模拟演示路线</h3><ol className="demo-route"><li>00:00–00:35：场景 A 跟踪与警报变化。</li><li>00:35–01:06：声呐证据、三级警报与模板建议。</li><li>01:06–01:20：查看方案，录制事件中的模拟批准在 01:10 出现。</li><li>01:20–02:05：切入场景 B，观察勘测分区与复航建议。</li><li>02:05–03:00：浮标离线、模拟外网断开，切换 2D/3D 说明结果。</li></ol><p className="muted">三分钟文件是合成回放，不是真实后端结果；“模拟外网断开”也不等于电脑 Wi-Fi 已关闭。浏览器不支持录屏时，请使用系统录屏或 OBS。</p>
    </div></dialog></>
}
