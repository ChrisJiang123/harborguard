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
    { name: 'test50', label: '合成固定测试集', metric: model, sample: object(samples.test50) },
    { name: 'confirm60', label: '合成确认集', metric: object(confirm.lora), sample: object(samples.confirm60) },
  ]
  return <div>
    <p>评估模型：{model.model} · {typeof config.output_format === 'string' && config.output_format.startsWith('format=json') ? 'format=json' : '格式见原始配置'}</p>
    {sets.map(set => {
      if (!set.metric.model) return null
      const counts = object(set.metric.counts)
      const fact = object(counts.id_fact_valid)
      return <div key={set.name}>
        <b>{set.name} · {set.label}（{String(set.sample.n ?? '—')} 条）</b>
        <dl>{([
          ['struct_valid', '结构'], ['id_fact_valid', 'ID + 事实'],
          ['option_agree', '方案一致'], ['null_recommend_correct', 'null 正确'],
        ] as const).map(([key, label]) => {
          const count = object(counts[key])
          return <div key={key}><dt>{label}</dt><dd>{typeof count.pass === 'number' && typeof count.total === 'number' ? `${count.pass}/${count.total}` : '整数分母待提供'}</dd></div>
        })}<div><dt>平均业务生成耗时（含重试）</dt><dd>{String(set.metric.latency_s ?? '—')} 秒</dd></div></dl>
        {typeof fact.pass === 'number' && typeof fact.total === 'number' && <p className="training">事实质量局限：{fact.total - fact.pass}/{fact.total} 条未通过 ID + 确定性事实校验。</p>}
      </div>
    })}
    <p className="muted">两组合成上下文结果分别统计；自由文本事实不能完全验证。模板兜底不计作模型成功，离线评估超时与线上事件预算不同。</p>
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
      if (!value || !('yolo' in value) || !('lora' in value)) { setError('指标响应缺少 yolo / lora 字段。'); return }
      setResult(value); setError(null)
    }).catch((cause: unknown) => { if (!abort.signal.aborted) setError(cause instanceof Error ? cause.message : '指标读取失败。') })
    return () => abort.abort()
  }, [conn, revision])
  return <details className="metrics-card"><summary>合成数据指标</summary><p className="muted">仅展示数据源原值，不代表真实海域效果。{conn === 'replay' && '回放无指标侧车文件，未访问后端。'}</p>{error ? <p role="alert">指标不可用：{error}</p> : result ? (['yolo', 'lora'] as const).map(model => <div className="metric-model" key={model}><b>{model === 'yolo' ? 'YOLO · mAP50 / 各类召回 / CPU 每图延迟' : 'LoRA · 结构 / 事实 / 方案 / 本地延迟'}</b>{result[model] === null ? <p className="training">尚未提供评估结果</p> : <>{model === 'lora' && <LoraSummary value={result[model]} />}<details open={model === 'yolo'}><summary>原始指标与配置（含历史失败）</summary><dl>{metricEntries(result[model]).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl></details>{metricEntries(result[model]).length === 0 && <p>指标格式待对齐，未生成替代数值。</p>}</>}</div>) : <p>正在读取指标…</p>}<button onClick={() => setRevision(value => value + 1)}>刷新指标</button></details>
}
