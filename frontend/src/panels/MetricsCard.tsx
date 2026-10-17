import { useEffect, useState } from 'react'
import { api } from '../data/api'
import type { MetricsResponse } from '../data/api'
import { metricEntries } from '../data/presentation'
import { useHarbor } from '../store/useHarbor'

export function MetricsCard() {
  const conn = useHarbor(s => s.conn)
  const [result, setResult] = useState<MetricsResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const abort = new AbortController()
    void api.metrics(abort.signal).then(value => {
      if (abort.signal.aborted) return
      if (!value || !('yolo' in value) || !('lora' in value)) { setError('指标响应缺少 yolo / lora 字段。'); return }
      setResult(value); setError(null)
    }).catch((cause: unknown) => { if (!abort.signal.aborted) setError(cause instanceof Error ? cause.message : '指标读取失败。') })
    return () => abort.abort()
  }, [conn, revision])
  return <details className="metrics-card"><summary>合成数据指标</summary><p className="muted">仅展示数据源原值，不代表真实海域效果。{conn === 'replay' && '回放无指标侧车文件，未访问后端。'}</p>{error ? <p role="alert">指标不可用：{error}</p> : result ? (['yolo', 'lora'] as const).map(model => <div className="metric-model" key={model}><b>{model === 'yolo' ? 'YOLO · mAP50 / 各类召回 / CPU 每图延迟' : 'LoRA · JSON 合法率 / 方案一致率 / 本地延迟'}</b>{result[model] === null ? <p className="training">训练中 · 尚未提供评估结果</p> : <><p className="muted">指标名与单位沿用后端字段：</p><dl>{metricEntries(result[model]).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>{metricEntries(result[model]).length === 0 && <p>指标格式待对齐，未生成替代数值。</p>}</>}</div>) : <p>正在读取指标…</p>}<button onClick={() => setRevision(value => value + 1)}>刷新指标</button></details>
}
