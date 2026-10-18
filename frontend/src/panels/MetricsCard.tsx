import { useEffect, useState } from 'react'
import { api } from '../data/api'
import type { MetricsResponse } from '../data/api'
import { metricEntries } from '../data/presentation'
import { useHarbor } from '../store/useHarbor'

function object(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function LoraSummary({ value }: { value: unknown }) {
  const metrics = object(value)
  const config = object(metrics.eval_config)
  const samples = object(metrics.sample_sets)
  const confirm = object(metrics.confirm60_synthetic)
  const model = object(metrics.lora)
  if (typeof model.model !== 'string') return null
  const sets = [
    { name: 'test50', label: 'Synthetic fixed test set', metric: model, sample: object(samples.test50) },
    { name: 'confirm60', label: 'Synthetic confirmation set', metric: object(confirm.lora), sample: object(samples.confirm60) },
  ]
  return <div>
    <p>Evaluated model: {model.model} · {typeof config.output_format === 'string' && config.output_format.startsWith('format=json') ? 'format=json' : 'See raw format configuration'}</p>
    {sets.map(set => {
      if (!set.metric.model) return null
      const counts = object(set.metric.counts)
      const fact = object(counts.id_fact_valid)
      return <div key={set.name}>
        <b>{set.name} · {set.label} ({String(set.sample.n ?? '—')} samples)</b>
        <dl>{([
          ['struct_valid', 'Structure'], ['id_fact_valid', 'IDs + facts'],
          ['option_agree', 'Option agreement'], ['null_recommend_correct', 'Correct null'],
        ] as const).map(([key, label]) => {
          const count = object(counts[key])
          return <div key={key}><dt>{label}</dt><dd>{typeof count.pass === 'number' && typeof count.total === 'number' ? `${count.pass}/${count.total}` : 'Integer counts unavailable'}</dd></div>
        })}<div><dt>Mean generation time (including retries)</dt><dd>{String(set.metric.latency_s ?? '—')} s</dd></div></dl>
        {typeof fact.pass === 'number' && typeof fact.total === 'number' && <p className="training">Fact quality limit: {fact.total - fact.pass}/{fact.total} samples failed ID + deterministic fact checks.</p>}
      </div>
    })}
    <p className="muted">The synthetic sets are reported separately. Free-text facts are not fully verified. Template fallbacks are not model successes; offline timeouts differ from the runtime event budget.</p>
  </div>
}

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
  return <details className="metrics-card"><summary>Synthetic Data Metrics</summary><p className="muted">Source-provided values; not a measure of real-world marine performance.{conn === 'replay' && 'No metrics sidecar in replay. Backend was not queried.'}</p>{error ? <p role="alert">Metrics unavailable: {error}</p> : result ? (['yolo', 'lora'] as const).map(model => <div className="metric-model" key={model}><b>{model === 'yolo' ? 'YOLO · mAP50 / Recall by class / CPU latency per image' : 'LoRA · Structure / Facts / Options / Local latency'}</b>{result[model] === null ? <p className="training">Evaluation results not available</p> : <>{model === 'lora' && <LoraSummary value={result[model]} />}<details open={model === 'yolo'}><summary>Raw metrics and configuration (including historical failures)</summary><dl>{metricEntries(result[model]).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl></details>{metricEntries(result[model]).length === 0 && <p>Unsupported metrics format. No substitute values were generated.</p>}</>}</div>) : <p>Loading metrics…</p>}<button onClick={() => setRevision(value => value + 1)}>Refresh metrics</button></details>
}
