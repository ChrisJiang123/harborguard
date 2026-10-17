import { create } from 'zustand'
import type { Alert, Detection, EventMsg, HarborMsg, LogEntry, Option, Recommendation, ReopenPlan, StateMsg, Track } from '../types/contract'
import type { DecisionInput } from '../data/commands'

export type Connection = 'live' | 'mock' | 'replay' | 'connecting' | 'disconnected'
type Payload = Record<string, unknown>
const record = (value: unknown): Payload | null => typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Payload : null
const indexed = <T extends { id: string }>(items: T[]) => Object.fromEntries(items.map(item => [item.id, item]))

export function initialData() {
  return {
    latest: null as StateMsg | null,
    tracks: {} as Record<string, Track>, alerts: {} as Record<string, Alert>,
    events: [] as EventMsg[], logs: [] as LogEntry[],
    optionsByAlert: {} as Record<string, Option[]>,
    recByAlert: {} as Record<string, Recommendation>, latestRec: null as Recommendation | null,
    detections: {} as Record<string, Detection>, reopenPlan: null as ReopenPlan | null,
    selectedTrackId: null as string | null, view: '2d' as '2d' | '3d',
    hoveredOptionId: null as string | null, chosenOptionId: null as string | null,
    sonarModalDetId: null as string | null,
    focusedZoneId: null as string | null,
    chosenOptionAlertId: null as string | null,
    decisionsByAlert: {} as Record<string, DecisionInput & { t: number }>,
    decisionRequests: {} as Record<string, DecisionInput>,
    session: 0,
    error: null as string | null,
  }
}

export type HarborStore = ReturnType<typeof initialData> & {
  conn: Connection
  ingest: (msg: HarborMsg) => void
  reset: () => void
  selectTrack: (id: string | null) => void
  setView: (view: '2d' | '3d') => void
  setConnection: (conn: Connection) => void
  setError: (error: string | null) => void
  chooseOption: (alertId: string, optionId: string) => void
  setDecisionRequest: (alertId: string, body: DecisionInput | null) => void
  cacheOptions: (alertId: string, options: Option[]) => void
  cacheDetection: (detection: Detection) => void
}

export const useHarbor = create<HarborStore>((set) => ({
  ...initialData(), conn: 'connecting',
  reset: () => set(state => ({ ...initialData(), session: state.session + 1, view: state.view })),
  selectTrack: selectedTrackId => set({ selectedTrackId, focusedZoneId: null }),
  setView: view => set({ view }),
  setConnection: conn => set({ conn }),
  setError: error => set({ error }),
  chooseOption: (chosenOptionAlertId, chosenOptionId) => set({ chosenOptionAlertId, chosenOptionId }),
  setDecisionRequest: (alertId, body) => set(state => {
    const decisionRequests = { ...state.decisionRequests }
    if (body) decisionRequests[alertId] = body
    else delete decisionRequests[alertId]
    return { decisionRequests }
  }),
  cacheOptions: (alertId, options) => set(state => ({ optionsByAlert: { ...state.optionsByAlert, [alertId]: options } })),
  cacheDetection: detection => set(state => ({ detections: { ...state.detections, [detection.id]: detection } })),
  ingest: msg => set(state => reduceMessage(state, msg)),
}))

// Replay seeks use the same reducer without publishing thousands of intermediate UI states.
export function reduceMessage(state: HarborStore, msg: HarborMsg): Partial<HarborStore> {
    if (msg.type === 'state') {
      return {
        latest: msg, tracks: indexed(msg.tracks), alerts: indexed(msg.alerts),
        selectedTrackId: state.selectedTrackId && msg.tracks.some(track => track.id === state.selectedTrackId) ? state.selectedTrackId : null,
      }
    }
    // Deduplicate reconnect/event backfill without losing different events at the same seq.
    if (state.events.some(event => event.seq === msg.seq && event.event === msg.event && event.t === msg.t)) return state
    const changes: Partial<HarborStore> = { events: [...state.events, msg].slice(-500) }
    const data = record(msg.data)
    if (!data) return changes
    switch (msg.event) {
      case 'scenario_changed':
        if (data.status === 'started' || data.status === 'reset') return { ...initialData(), view: state.view, session: state.session + 1, events: [msg] }
        break
      case 'alert_raised':
      case 'alert_changed': {
        const alert = record(data.alert)
        if (alert && typeof alert.id === 'string') changes.alerts = { ...state.alerts, [alert.id]: alert as unknown as Alert }
        break
      }
      case 'alert_cleared': {
        const alerts = { ...state.alerts }
        if (typeof data.alert_id === 'string') delete alerts[data.alert_id]
        changes.alerts = alerts
        break
      }
      case 'options_ready':
        if (typeof data.alert_id === 'string' && Array.isArray(data.options)) changes.optionsByAlert = { ...state.optionsByAlert, [data.alert_id]: data.options as Option[] }
        break
      case 'recommendation': {
        const rec = record(data.recommendation)
        if (rec && typeof rec.id === 'string') {
          const recommendation = rec as unknown as Recommendation
          changes.latestRec = recommendation
          if (recommendation.alert_id) changes.recByAlert = { ...state.recByAlert, [recommendation.alert_id]: recommendation }
        }
        break
      }
      case 'detection': {
        const detection = record(data.detection)
        if (detection && typeof detection.id === 'string') changes.detections = { ...state.detections, [detection.id]: detection as unknown as Detection }
        break
      }
      case 'reopen_plan':
        changes.reopenPlan = data as unknown as ReopenPlan
        break
      case 'log':
        if (record(data.log)) changes.logs = [...state.logs, data.log as LogEntry].slice(-200)
        break
      case 'decision':
        if (typeof data.alert_id === 'string' && typeof data.option_id === 'string' && typeof data.operator === 'string' && (data.action === 'approve' || data.action === 'reject')) {
          const decisionRequests = { ...state.decisionRequests }
          delete decisionRequests[data.alert_id]
          changes.decisionRequests = decisionRequests
          changes.decisionsByAlert = { ...state.decisionsByAlert, [data.alert_id]: { alert_id: data.alert_id, option_id: data.option_id, action: data.action, operator: data.operator, t: msg.t } }
        }
        break
      case 'zone_changed':
        if (state.latest) changes.latest = { ...state.latest, zones: state.latest.zones.map(zone => zone.id === data.zone_id ? { ...zone, state: data.state as typeof zone.state } : zone) }
        break
      case 'buoy_changed':
        if (state.latest) changes.latest = { ...state.latest, buoys: state.latest.buoys.map(buoy => buoy.id === data.buoy_id ? { ...buoy, status: data.status as typeof buoy.status } : buoy) }
        break
      case 'network_changed':
        if (state.latest && (data.network === 'online' || data.network === 'offline')) changes.latest = { ...state.latest, network: data.network }
        break
      case 'mode_changed':
        if (state.latest && (data.mode === 'security' || data.mode === 'disaster')) changes.latest = { ...state.latest, mode: data.mode }
        break
    }
    return changes
}

// All three transports use the same entry point; malformed envelopes never crash the UI.
export function isHarborMessage(value: unknown): value is HarborMsg {
  const msg = record(value)
  if (!msg || !Number.isFinite(msg.seq) || !Number.isFinite(msg.t)) return false
  if (msg.type === 'state') {
    if (!['buoys', 'tracks', 'alerts', 'zones'].every(key => Array.isArray(msg[key]))) return false
    if (msg.mode !== 'security' && msg.mode !== 'disaster') return false
    if (msg.network !== 'online' && msg.network !== 'offline') return false
    const arrays = [msg.buoys, msg.tracks, msg.alerts, msg.zones] as unknown[][]
    if (!arrays.every(items => items.every(item => typeof record(item)?.id === 'string'))) return false
  } else if (msg.type !== 'event' || typeof msg.event !== 'string' || !record(msg.data)) return false
  return true
}

export function receiveMessage(value: unknown): boolean {
  if (!isHarborMessage(value)) return false
  useHarbor.getState().ingest(value)
  return true
}
