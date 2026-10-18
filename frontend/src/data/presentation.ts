import type { Detection } from '../types/contract'
import { englishDisplayValue, englishText } from './english'

export function localSonarPath(detection: Detection): string {
  const path = detection.image_url
  // Offline replay must not silently request backend images or remote URLs.
  if (/^\/(?!\/)[a-zA-Z0-9_./-]+\.(png|jpe?g|webp|svg)$/i.test(path) && !path.split('/').includes('..') && !path.startsWith('/api/')) return path
  return `/sonar/${encodeURIComponent(detection.id)}.png`
}
export function metricEntries(value: unknown): [string, string][] {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return []
  return Object.entries(value).map(([key, item]) => [englishText(key), typeof item === 'number' && Number.isFinite(item) ? String(item) : typeof item === 'string' ? englishText(item) : JSON.stringify(englishDisplayValue(item)) ?? '—'])
}
