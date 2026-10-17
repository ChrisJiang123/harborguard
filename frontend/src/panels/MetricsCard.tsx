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
      if (!value || !('yolo' in value) || !('lora' in value)) { setError('Metrics response is missing yolo / lora fields.'); return }
      setResult(value); setError(null)
    }).catch((cause: unknown) => { if (!abort.signal.aborted) setError(cause instanceof Error ? cause.message : 'Could not load metrics.') })
    return () => abort.abort()
  }, [conn, revision])
  return <details className="metrics-card"><summary>Synthetic Data Metrics</summary><p className="muted">Source-provided values; not a measure of real-world marine performance.{conn === 'replay' && 'No metrics sidecar in replay. Backend was not queried.'}</p>{error ? <p role="alert">Metrics unavailable: {error}</p> : result ? (['yolo', 'lora'] as const).map(model => <div className="metric-model" key={model}><b>{model === 'yolo' ? 'YOLO · mAP50 / Recall by class / CPU latency per image' : 'LoRA · Valid JSON / Option agreement / Local latency'}</b>{result[model] === null ? <p className="training">Training · Evaluation results not available</p> : <><p className="muted">Metric names and units follow backend fields: </p><dl>{metricEntries(result[model]).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>{metricEntries(result[model]).length === 0 && <p>Unsupported metrics format. No substitute values were generated.</p>}</>}</div>) : <p>Loading metrics…</p>}<button onClick={() => setRevision(value => value + 1)}>Refresh metrics</button></details>
}
