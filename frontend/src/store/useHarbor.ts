import { create } from 'zustand'
import type { Alert, Detection, EventMsg, HarborMsg, LogEntry, Option, Recommendation, ReopenPlan, StateMsg, Track } from '../types/contract'
import type { DecisionInput } from '../data/commands'

export type Connection = 'live' | 'mock' | 'replay' | 'connecting' | 'disconnected'
export type RecoveryPhase = 'idle' | 'loading' | 'complete' | 'partial' | 'failed'
export interface RecoveryState {
  phase: RecoveryPhase
  eventsReturned: number
  detailFailures: number
  checkedAt: number | null
  message: string | null
}
export interface RecoveryMeta {
  eventsAvailable: boolean
  eventsReturned: number
  eventLimitReached: boolean
  detailFailures: number
  previousSnapshotSeq?: number
}
export interface UncertainDecision extends DecisionInput {
  reason: 'reject-without-event'
}
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
    uncertainDecisions: {} as Record<string, UncertainDecision>,
    recovery: { phase: 'idle', eventsReturned: 0, detailFailures: 0, checkedAt: null, message: null } as RecoveryState,
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
  markDecisionUncertain: (alertId: string, body: UncertainDecision | null) => void
  setRecoveryLoading: (expectedSession?: number) => void
  cacheOptions: (alertId: string, options: Option[]) => void
  cacheDetection: (detection: Detection) => void
  recoverLive: (snapshot: StateMsg, events: EventMsg[], logs: LogEntry[], options: Record<string, Option[]>, detections: Record<string, Detection>, meta?: RecoveryMeta, expectedSession?: number) => void
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
  markDecisionUncertain: (alertId, body) => set(state => {
    const uncertainDecisions = { ...state.uncertainDecisions }
    if (body) uncertainDecisions[alertId] = body
    else delete uncertainDecisions[alertId]
    return { uncertainDecisions }
  }),
  setRecoveryLoading: expectedSession => set(state => expectedSession !== undefined && state.session !== expectedSession ? state : { recovery: { phase: 'loading', eventsReturned: 0, detailFailures: 0, checkedAt: null, message: null } }),
  cacheOptions: (alertId, options) => set(state => ({ optionsByAlert: { ...state.optionsByAlert, [alertId]: options } })),
  cacheDetection: detection => set(state => ({ detections: { ...state.detections, [detection.id]: detection } })),
  recoverLive: (snapshot, events, logs, options, detections, meta, expectedSession) => set(state => expectedSession !== undefined && state.session !== expectedSession ? state : recoverLiveState(state, snapshot, events, logs, options, detections, meta)),
  ingest: msg => set(state => reduceMessage(state, msg)),
}))

/** Rebuild event-derived UI state after refresh/reconnect, then keep the newest live snapshot. */
export function eventIdentity(event: EventMsg): string {
  const data = record(event.data)
  const recommendation = record(data?.recommendation)
  const detection = record(data?.detection)
  const alert = record(data?.alert)
  if (typeof recommendation?.id === 'string') return `recommendation:${recommendation.id}`
  if (typeof detection?.id === 'string') return `detection:${detection.id}`
  if (typeof alert?.id === 'string') return `${event.event}:${alert.id}:${String(alert.updated_t ?? event.t)}`
  if (typeof data?.alert_id === 'string' && event.event === 'decision') return `decision:${data.alert_id}:${String(data.option_id)}:${String(data.action)}:${event.t}`
  if (typeof data?.alert_id === 'string' && event.event === 'options_ready') return `options:${data.alert_id}:${event.t}`
  return `${event.seq}:${event.event}:${event.t}`
}

function logIdentity(log: LogEntry): string {
  return `${log.t}:${log.level}:${log.source}:${log.text}`
}

/** Keep bounded REST history first, then append any logs observed while its request was pending. */
export function mergeRecoveredLogs(newestFirstHistory: LogEntry[], recoveredEventLogs: LogEntry[], liveLogs: LogEntry[]): LogEntry[] {
  const seen = new Set<string>()
  const merged: LogEntry[] = []
  for (const log of [...newestFirstHistory].reverse().concat(recoveredEventLogs, liveLogs)) {
    const identity = logIdentity(log)
    if (seen.has(identity)) continue
    seen.add(identity)
    merged.push(log)
  }
  return merged.slice(-200)
}

export function recoverLiveState(state: HarborStore, snapshot: StateMsg, events: EventMsg[], logs: LogEntry[], options: Record<string, Option[]> = {}, detections: Record<string, Detection> = {}, meta?: RecoveryMeta): Partial<HarborStore> {
  // This is a connection-start baseline, not the snapshot that may have arrived
  // while asynchronous REST recovery was still in flight.
  const previousSnapshotSeq = meta?.previousSnapshotSeq
  const serverRestarted = previousSnapshotSeq !== undefined && snapshot.seq < previousSnapshotSeq
  const byIdentity = new Map<string, EventMsg>()
  for (const event of [...events, ...(serverRestarted ? [] : state.events)]) byIdentity.set(eventIdentity(event), event)
  const ordered = [...byIdentity.values()].sort((a, b) => a.seq - b.seq || a.t - b.t)
  let recovered = { ...state, ...initialData(), conn: state.conn, view: state.view } as HarborStore
  for (const event of ordered) recovered = { ...recovered, ...reduceMessage(recovered, event) }
  const latest = !serverRestarted && state.latest && state.latest.seq > snapshot.seq ? state.latest : snapshot
  recovered = { ...recovered, ...reduceMessage(recovered, latest) }
  const decisionsByAlert = recovered.decisionsByAlert
  const decisionRequests = serverRestarted ? {} : Object.fromEntries(Object.entries(state.decisionRequests).filter(([alertId]) => !decisionsByAlert[alertId]))
  const uncertainDecisions = serverRestarted ? {} : Object.fromEntries(Object.entries(state.uncertainDecisions).filter(([alertId]) => !decisionsByAlert[alertId]))
  const effectiveMeta = meta ?? { eventsAvailable: true, eventsReturned: events.length, eventLimitReached: events.length >= 500, detailFailures: 0 }
  const phase: RecoveryPhase = !effectiveMeta.eventsAvailable ? 'failed' : serverRestarted || effectiveMeta.eventLimitReached || effectiveMeta.detailFailures > 0 ? 'partial' : 'complete'
  const message = !effectiveMeta.eventsAvailable
    ? '历史加载失败：当前态势仍会实时更新，但刷新前的建议与审批状态无法恢复。'
    : serverRestarted
      ? '检测到后端事件序列回退，已清除旧会话缓存；重启前的建议与审批状态无法确认。'
    : effectiveMeta.eventLimitReached
      ? '历史不完整：服务器返回已达到 500 条缓存上限，较早的建议与审批状态可能无法恢复。'
      : effectiveMeta.detailFailures > 0
        ? `历史部分恢复：${effectiveMeta.detailFailures} 条当前详情读取失败。`
        : null
  return {
    ...recovered,
    logs: mergeRecoveredLogs(logs, recovered.logs, state.logs),
    optionsByAlert: { ...recovered.optionsByAlert, ...options },
    detections: { ...recovered.detections, ...detections },
    decisionRequests,
    uncertainDecisions,
    recovery: { phase, eventsReturned: effectiveMeta.eventsReturned, detailFailures: effectiveMeta.detailFailures, checkedAt: Date.now(), message },
    // A sequence rollback is handled synchronously by ws.ts before the new
    // snapshot is ingested. Do not advance the session a second time here.
    session: state.session,
    error: state.error,
    selectedTrackId: state.selectedTrackId && latest.tracks.some(track => track.id === state.selectedTrackId) ? state.selectedTrackId : null,
  }
}

// Replay seeks use the same reducer without publishing thousands of intermediate UI states.
export function reduceMessage(state: HarborStore, msg: HarborMsg): Partial<HarborStore> {
    if (msg.type === 'state') {
      return {
        latest: msg, tracks: indexed(msg.tracks), alerts: indexed(msg.alerts),
        selectedTrackId: state.selectedTrackId && msg.tracks.some(track => track.id === state.selectedTrackId) ? state.selectedTrackId : null,
      }
    }
    // Deduplicate reconnect/event backfill without losing different events at the same seq.
    if (state.events.some(event => eventIdentity(event) === eventIdentity(msg))) return state
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
          const uncertainDecisions = { ...state.uncertainDecisions }
          delete decisionRequests[data.alert_id]
          delete uncertainDecisions[data.alert_id]
          changes.decisionRequests = decisionRequests
          changes.uncertainDecisions = uncertainDecisions
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
