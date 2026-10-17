import type { Alert, Option, Recommendation } from '../types/contract'
import { W } from '../theme'

interface AlertContext { alerts: Record<string, Alert>; selectedTrackId: string | null }
export function activeAlertId(state: AlertContext): string | null {
  const alerts = Object.values(state.alerts)
  const relevant = state.selectedTrackId ? alerts.filter(alert => alert.track_id === state.selectedTrackId) : alerts
  relevant.sort((a, b) => b.level - a.level || b.risk - a.risk || a.id.localeCompare(b.id))
  return relevant[0]?.id ?? null
}

export function effectiveOptionId(alertId: string | null, options: Option[], rec: Recommendation | null | undefined, chosen: string | null, chosenAlert: string | null): string | null {
  if (!alertId) return null
  const candidate = chosenAlert === alertId && chosen ? chosen : rec?.alert_id === alertId ? rec.recommended_option_id : null
  return candidate && options.some(option => option.id === candidate) ? candidate : null
}

export function riskContributions(alert: Alert) {
  // Display-only contributions; never replace alert.risk or infer a warning level.
  return (Object.keys(W) as (keyof typeof W)[]).map(key => ({ key, raw: alert.breakdown[key], weighted: W[key] * alert.breakdown[key], weight: W[key] }))
}

export const numberText = (value: number, digits = 1) => Number.isFinite(value) ? value.toFixed(digits) : '—'
