import type { Alert, Asset, Buoy, Detection, EventMsg, LogEntry, Option, Recommendation, StateMsg, Track } from '../types/contract'
import { useHarbor } from '../store/useHarbor'
import type { ZoneCollection } from './mapGeometry'
import type { ControlInput, DecisionInput, InjectInput } from './commands'
import { APIError, requestJSON } from './http'
import { getMock } from './mock'
import { loadLocalData } from './staticData'

const BASE = (import.meta.env.VITE_API_BASE || 'http://localhost:8000/api').replace(/\/$/, '')
const id = encodeURIComponent
interface OptionResponse { alert_id: string; options: Option[]; ranked: string[] }
export interface MetricsResponse { yolo: unknown | null; lora: unknown | null }

async function localRequest(path: string, method: 'GET' | 'POST', body?: unknown): Promise<unknown> {
  const state = useHarbor.getState()
  const [route, query = ''] = path.split('?')
  const params = new URLSearchParams(query)
  if (method === 'GET') {
    if (route === '/health') return { ok: true }
    if (route === '/state') { if (!state.latest) throw new APIError('Local state is not ready.'); return state.latest }
    if (route === '/events') return state.events.filter(event => event.seq > Number(params.get('since_seq') ?? 0))
    if (route === '/log') return state.logs.slice(-Math.max(1, Number(params.get('limit') ?? 100))).reverse()
    if (route === '/metrics') return { yolo: null, lora: null }
    if (route === '/assets') return (await loadLocalData()).assets
    if (route === '/buoys') { if (!state.latest) throw new APIError('Local buoy state is not ready.'); return state.latest.buoys }
    if (route === '/zones') {
      const resources = await loadLocalData()
      return { ...resources.zones, features: resources.zones.features.map(feature => ({ ...feature, properties: { ...feature.properties, ...state.latest?.zones.find(zone => zone.id === feature.properties.id) } })) }
    }
    const match = route?.match(/^\/(tracks|alerts|detections|options)\/(.+)$/)
    if (match) {
      const key = decodeURIComponent(match[2]!)
      if (match[1] === 'options') {
        const options = state.optionsByAlert[key]
        if (!options) throw new APIError('Options are not ready.')
        return { alert_id: key, options, ranked: options.map(option => option.id) }
      }
      const value = match[1] === 'tracks' ? state.tracks[key] : match[1] === 'alerts' ? state.alerts[key] : state.detections[key]
      if (!value) throw new APIError('The local record was not found.', 404)
      return value
    }
    throw new APIError('This resource is unavailable in the local demo.', 404)
  }
  const engine = getMock()
  if (!engine) throw new APIError('The local demo is starting. Please try again shortly.')
  if (route === '/control') { const input = body as ControlInput; engine.control(input.action, input.value) }
  else if (route === '/mode') engine.setMode((body as { mode: StateMsg['mode'] }).mode)
  else if (route === '/inject') engine.inject(body as InjectInput)
  else if (route === '/decision') engine.decision(body as DecisionInput)
  else if (route === '/scenario/a/start' || route === '/scenario/b/start') engine.startScenario(route.includes('/a/') ? 'a' : 'b', (body as { speed?: number }).speed)
  else throw new APIError('This endpoint is unavailable in the local demo.')
  return { ok: true }
}

// Agent /ask has an 18s generation budget and a 20s backend proxy timeout.
// Allow 19s here; all other endpoints retain the default 8s timeout.
const ASK_TIMEOUT_MS = 19000

async function request<T>(path: string, method: 'GET' | 'POST' = 'GET', body?: unknown, signal?: AbortSignal, timeoutMs?: number): Promise<T> {
  const conn = useHarbor.getState().conn
  if (method === 'POST' && conn === 'replay') throw new APIError('Actions are disabled during replay.')
  if (method === 'POST' && conn !== 'live' && conn !== 'mock') throw new APIError('Backend disconnected. Wait for LIVE status.')
  if (conn === 'mock' || conn === 'replay') return await localRequest(path, method, body) as T
  return requestJSON<T>(`${BASE}${path}`, { method, signal, ...(body === undefined ? {} : { body: JSON.stringify(body) }) }, timeoutMs)
}

async function command(path: string, body: unknown): Promise<{ ok: true }> {
  const result = await request<{ ok?: boolean }>(path, 'POST', body)
  if (result?.ok !== true) throw new APIError('The backend did not confirm this action.')
  return { ok: true }
}

export const api = {
  health: () => request<{ ok: boolean }>('/health'),
  state: (signal?: AbortSignal) => request<StateMsg>('/state', 'GET', undefined, signal),
  events: (since = 0, signal?: AbortSignal) => request<EventMsg[]>(`/events?since_seq=${Math.max(0, Math.floor(since))}`, 'GET', undefined, signal),
  zones: (signal?: AbortSignal) => request<ZoneCollection>('/zones', 'GET', undefined, signal),
  assets: (signal?: AbortSignal) => request<Asset[]>('/assets', 'GET', undefined, signal),
  buoys: (signal?: AbortSignal) => request<Buoy[]>('/buoys', 'GET', undefined, signal),
  track: (trackId: string) => request<Track>(`/tracks/${id(trackId)}`),
  alert: (alertId: string) => request<Alert>(`/alerts/${id(alertId)}`),
  detection: (detectionId: string, signal?: AbortSignal) => request<Detection>(`/detections/${id(detectionId)}`, 'GET', undefined, signal),
  options: async (alertId: string, signal?: AbortSignal): Promise<OptionResponse> => {
    const result = await request<OptionResponse>(`/options/${id(alertId)}`, 'GET', undefined, signal)
    if (result?.alert_id !== alertId || !Array.isArray(result.options) || !Array.isArray(result.ranked)) throw new APIError('The options response does not match the shared contract.')
    return result
  },
  sonarURL: (detectionId: string) => `${BASE}/sonar/${id(detectionId)}.png`,
  logs: (limit = 100, signal?: AbortSignal) => request<LogEntry[]>(`/log?limit=${Math.min(200, Math.max(1, Math.floor(limit)))}`, 'GET', undefined, signal),
  metrics: (signal?: AbortSignal) => request<MetricsResponse>('/metrics', 'GET', undefined, signal),
  startScenario: (scenario: 'a' | 'b', speed?: number) => command(`/scenario/${scenario}/start`, { speed }),
  control: (body: ControlInput) => command('/control', body),
  mode: (mode: StateMsg['mode']) => command('/mode', { mode }),
  inject: (body: InjectInput) => command('/inject', body),
  decide: async (body: DecisionInput) => {
    const state = useHarbor.getState()
    if (!state.alerts[body.alert_id] || !state.optionsByAlert[body.alert_id]?.some(option => option.id === body.option_id)) throw new APIError('This alert or option is unavailable. Select it again.')
    if (state.decisionsByAlert[body.alert_id] || state.decisionRequests[body.alert_id]) throw new APIError('This alert has already been handled or is awaiting confirmation.')
    if (!body.operator.trim()) throw new APIError('Enter an operator name.')
    const session = state.session
    state.setDecisionRequest(body.alert_id, body)
    try {
      const result = await command('/decision', body)
      if (body.action === 'reject' && useHarbor.getState().session === session && useHarbor.getState().decisionRequests[body.alert_id]) {
        useHarbor.getState().setDecisionRequest(body.alert_id, null)
        useHarbor.getState().markDecisionUncertain(body.alert_id, { ...body, reason: 'reject-without-event' })
      }
      return result
    }
    catch (error) { if (useHarbor.getState().session === session) useHarbor.getState().setDecisionRequest(body.alert_id, null); throw error }
  },
  // Agent-owned endpoints are wrapped for the shared REST surface, not invoked by the UI.
  postRecommendation: (recommendation: Recommendation) => command('/recommendations', recommendation),
  postLog: (log: Pick<LogEntry, 'level' | 'source' | 'text'>) => command('/log', log),
  ask: (question: string, track_id?: string) => request<{ answer: string; model: Recommendation['model'] }>('/agent/ask', 'POST', { question, track_id }, undefined, ASK_TIMEOUT_MS),
}
