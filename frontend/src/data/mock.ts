import type { Alert, Asset, Buoy, EventMsg, HarborMsg, Level, Option, Recommendation, ReopenPlan, StateMsg, Track, ZoneStatus } from '../types/contract'
import { receiveMessage, useHarbor } from '../store/useHarbor'
import { DEMO_ASSETS, DEMO_BUOYS, DEMO_ZONES } from './demoGeometry'
import type { StaticBuoy } from './mapGeometry'
import { loadLocalData } from './staticData'
import type { DecisionInput, InjectInput } from './commands'

export const MOCK_ASSETS: Asset[] = DEMO_ASSETS
function mockOptions(zoneIds: string[]): Option[] {
  return [
    { id: 'opt-1', label: '局部限制通航', is_baseline: false, zones_closed: [...new Set([zoneIds[3] ?? zoneIds[0]!, zoneIds[4] ?? zoneIds[0]!])], speed_limit_zones: zoneIds[5] ? [zoneIds[5]] : [], berths_open_pct: 0.82, vessels_affected: 3, delay_vessel_hours: 4.5, residual_risk: 0.18 },
    { id: 'port-closure', label: '全港关闭', is_baseline: true, zones_closed: zoneIds, speed_limit_zones: [], berths_open_pct: 0, vessels_affected: 18, delay_vessel_hours: 36, residual_risk: 0.03 },
  ]
}
export const MOCK_OPTIONS: Option[] = mockOptions(DEMO_ZONES.features.map(zone => zone.properties.id))

type Sink = (msg: HarborMsg) => void

// The generator represents B for local demonstration only. Production risk values are never recalculated.
export function createMockEngine(sink: Sink, inputBuoys?: (StaticBuoy & { status?: Buoy['status'] })[], inputAsset?: Asset, inputZoneIds?: string[]) {
  let seq = 0
  let t = 0
  let stopped = false
  let paused = false
  let speed = 1
  let mode: StateMsg['mode'] = 'security'
  let network: StateMsg['network'] = 'online'
  let scenario: StateMsg['scenario'] = 'a'
  let decided = false
  let restricted = new Set<string>()
  const delivered = new Set<string>()
  let history: Track['history'] = []
  let vesselHistories: Record<'T3' | 'T4', Track['history']> = { T3: [], T4: [] }
  const asset = inputAsset ?? MOCK_ASSETS[0]!
  const zoneIds = inputZoneIds?.length ? inputZoneIds : DEMO_ZONES.features.map(zone => zone.properties.id)
  const options = mockOptions(zoneIds)
  const primaryZone = options[0]!.zones_closed[0]!
  const buoys: Buoy[] = (inputBuoys?.length ? inputBuoys : DEMO_BUOYS).map(buoy => ({ ...buoy, status: 'status' in buoy && buoy.status === 'down' ? 'down' : 'ok', range_m: Number.isFinite(buoy.range_m) ? buoy.range_m : 650, pinging: false }))
  function event(name: string, data: unknown) {
    sink({ type: 'event', seq: ++seq, t, event: name, data })
  }
  function once(key: string, at: number, fn: () => void) {
    if (t >= at && !delivered.has(key)) { delivered.add(key); fn() }
  }
  function vesselTrack(id: 'T3' | 'T4', start: [number, number], end: [number, number], duration: number, bend: number, speed_mps: number): Track {
    const position = (time: number) => {
      const p = Math.max(0, Math.min(1, time / duration))
      const lat = start[0] + (end[0] - start[0]) * p + Math.sin(Math.PI * p) * bend
      const lon = start[1] + (end[1] - start[1]) * p
      const q = Math.min(1, p + .001)
      const nextLat = start[0] + (end[0] - start[0]) * q + Math.sin(Math.PI * q) * bend
      const nextLon = start[1] + (end[1] - start[1]) * q
      const east = (nextLon - lon) * 111320 * Math.cos(lat * Math.PI / 180)
      const north = (nextLat - lat) * 110540
      const heading = (Math.atan2(east, north) * 180 / Math.PI + 360) % 360
      return { lat, lon, heading }
    }
    const current = position(t)
    const point: Track['history'][number] = [current.lat, current.lon, 0, t]
    if (vesselHistories[id].at(-1)?.[3] !== t) vesselHistories[id] = [...vesselHistories[id], point].slice(-60)
    const distanceE = (end[1] - start[1]) * 111320 * Math.cos(current.lat * Math.PI / 180)
    const distanceN = (end[0] - start[0]) * 110540
    return {
      id, status: 'confirmed', cls: 'vessel', conf: 0.99, cue: 'none', lat: current.lat, lon: current.lon, depth_m: 0,
      vel_e: distanceE / duration, vel_n: distanceN / duration, vel_d: 0, speed_mps, heading_deg: current.heading,
      err: { a_m: 18, b_m: 8, angle_deg: current.heading }, history: vesselHistories[id],
      predicted: Array.from({ length: 10 }, (_, index) => { const future = t + (index + 1) * 30; const next = position(future); return [next.lat, next.lon, 0, future] }),
      level: 0, risk: 0.01, detection_id: null,
    }
  }
  function snapshot(): StateMsg {
    const progress = Math.min(t / 90, 1)
    const lat = asset.lat - 0.018 * (1 - progress)
    const lon = asset.lon - 0.018 * (1 - progress)
    const level: Level = mode !== 'security' || scenario !== 'a' ? 0 : t < 10 ? 0 : t < 35 ? 1 : t < 60 ? 2 : 3
    const risk = level === 0 ? 0.06 : level === 1 ? 0.24 : level === 2 ? 0.55 : 0.89
    const cls = mode === 'disaster' ? 'debris' : t >= 35 ? 'uuv' : 'unknown'
    const point: Track['history'][number] = [lat, lon, 12, t]
    if (history.at(-1)?.[3] !== t) history = [...history, point].slice(-60)
    const target: Track = {
      id: 'T1', status: t >= 10 ? 'confirmed' : 'tentative', cls, conf: t >= 35 ? 0.94 : 0.36,
      cue: 'narrowband', lat, lon, depth_m: 12, vel_e: 18.5, vel_n: 22.1, vel_d: 0,
      speed_mps: 28.8, heading_deg: 40, err: { a_m: t >= 35 ? 35 : 120, b_m: t >= 35 ? 18 : 60, angle_deg: 40 },
      history, predicted: Array.from({ length: 10 }, (_, i) => {
        const futureT = t + (i + 1) * 30
        const p = Math.min(futureT / 90, 1)
        return [asset.lat - 0.018 * (1 - p), asset.lon - 0.018 * (1 - p), 12, futureT]
      }),
      level, risk, detection_id: mode === 'security' && scenario === 'a' && t >= 35 ? 'det-1' : null,
    }
    const fish: Track = {
      ...target, id: 'T2', status: 'confirmed', cls: 'fish_school', conf: 0.97, cue: 'broadband',
      lat: 33.733 + Math.sin(t / 11) * 0.0015, lon: -118.267 + Math.cos(t / 13) * 0.0015,
      depth_m: 7, vel_e: 0.5, vel_n: 0.3, speed_mps: 0.58, heading_deg: 59,
      history: [], predicted: [], level: 0, risk: 0.03, detection_id: null,
    }
    const eastbound = vesselTrack('T3', [asset.lat - .012, asset.lon - .028], [asset.lat - .006, asset.lon + .020], 120, .0018, 7.2)
    const westbound = vesselTrack('T4', [asset.lat + .010, asset.lon + .022], [asset.lat + .006, asset.lon - .026], 150, -.0015, 5.8)
    const alert: Alert = {
      id: 'A1', track_id: 'T1', level: level === 0 ? 1 : level, risk,
      breakdown: { C: risk, P: risk, B: risk, Z: risk, D: risk },
      zone_id: primaryZone, asset_id: asset.id, distance_m: Math.round(2600 * (1 - progress)),
      eta_s: Math.max(0, 90 - t), raised_t: 10, updated_t: t, options_ready: t >= 60,
    }
    return {
      type: 'state', seq: ++seq, t, mode, network, scenario, paused, speed,
      buoys: buoys.map((buoy, i) => ({ ...buoy, pinging: buoy.status === 'ok' && Math.floor(t * 5) % 25 === i * 2 })),
      tracks: [target, fish, eastbound, westbound], alerts: level > 0 ? [alert] : [],
      zones: zoneIds.map((id, i) => mode === 'disaster' ? disasterZone(id, i) : { id, state: restricted.has(id) ? 'restricted' : 'open', coverage: 1 }),
    }
  }
  // Predefined demonstration service responses, not a frontend reopening/risk algorithm.
  function disasterZone(id: string, index: number): ZoneStatus {
    if (scenario !== 'b' || t < 12) return { id, state: 'unsurveyed', coverage: 0 }
    if (index === 4 && t >= 24) return { id, state: 'blocked', coverage: 1 }
    if (index < 3 || (t >= 45 && index >= 5 && index < 8)) return { id, state: 'clear', coverage: 1 }
    return { id, state: 'unsurveyed', coverage: index === 3 ? 0.35 : 0 }
  }
  function disasterPlan(final: boolean): ReopenPlan {
    return { route_zone_ids: zoneIds.slice(0, 2), reopen_berth_zone_ids: final ? [...zoneIds.slice(2, 3), ...zoneIds.slice(5, 8)] : zoneIds.slice(2, 3), unsurveyed_zone_ids: final ? [...zoneIds.slice(3, 4), ...zoneIds.slice(8)] : [...zoneIds.slice(3, 4), ...zoneIds.slice(5)], blocked_zone_ids: zoneIds.slice(4, 5), est_hours_saved: final ? 9 : 4.5 }
  }
  function publish() {
    const state = snapshot()
    sink(state)
    const alert = state.alerts[0]!
    once('started', 0, () => event('log', { log: { t, level: 'info', source: 'sim', text: '本地演示已启动；当前全部为模拟数据。' } }))
    if (mode === 'disaster' && scenario === 'b') {
      for (const at of [12, 24, 45]) once(`survey-${at}`, at, () => {
        state.zones.forEach(zone => event('zone_changed', { zone_id: zone.id, state: zone.state }))
        event('log', { log: { t, level: at === 24 ? 'warn' : 'info', source: 'sim', text: `模拟勘测节点 ${at} 秒：分区状态已更新。` } })
      })
      once('reopen-first', 24, () => event('reopen_plan', disasterPlan(false)))
      once('reopen-final', 45, () => {
        event('reopen_plan', disasterPlan(true))
        event('recommendation', { recommendation: { id: 'rec-b', kind: 'disaster', alert_id: null, model: 'template', summary: '优先开放已勘测航道与指定泊位。', explanation: '本地模板演示：仅展示预设模拟服务给出的分区和节省时间；待勘测与封闭区域不在复航建议内。', recommended_option_id: null, evidence_ids: zoneIds.slice(0, 3), uncertainties: ['示例分区和时间并非真实勘测结果。', '断网演示仍使用模板，不代表已训练本地模型。'], confidence: 'medium', created_t: t, latency_ms: 0 } })
      })
      return
    }
    if (mode !== 'security' || scenario !== 'a') return
    once('level1', 10, () => { event('alert_raised', { alert }); event('log', { log: { t, level: 'info', source: 'sim', text: 'T1 触发一级警报，持续跟踪。' } }) })
    once('level2', 35, () => {
      event('alert_changed', { alert, from_level: 1, to_level: 2 })
      event('detection', { detection: { id: 'det-1', track_id: 'T1', buoy_id: buoys[0]!.id, t, cls: 'uuv', conf: 0.94, bbox: [100, 150, 320, 290], image_url: '/data/sonar-stub.svg', model: 'stub' } })
      event('log', { log: { t, level: 'warn', source: 'perception', text: 'T1 模拟识别为 UUV，警报升级为二级。' } })
    })
    once('level3', 60, () => {
      event('alert_changed', { alert, from_level: 2, to_level: 3 })
      event('options_ready', { alert_id: 'A1', options, ranked: ['opt-1', 'port-closure'] })
      event('log', { log: { t, level: 'critical', source: 'decision', text: '三级警报，模拟处置方案已就绪。' } })
    })
    once('rec', 66, () => {
      const recommendation: Recommendation = {
        id: 'rec-1', kind: 'security', alert_id: 'A1', model: 'template',
        summary: '建议局部限制通航，保留其他泊位运行。',
        explanation: '这是本地模板演示。模拟目标正在接近示例资产，请对照航迹与模拟识别记录，由操作员决定是否批准。',
        recommended_option_id: 'opt-1', evidence_ids: ['T1', 'det-1', primaryZone],
        uncertainties: ['全部为模拟数据，不代表真实港口风险。'], confidence: 'medium', created_t: t, latency_ms: 0,
      }
      event('recommendation', { recommendation })
      event('log', { log: { t, level: 'info', source: 'agent', text: '模板建议已生成，等待人工批准。' } })
    })
  }
  function resetScenario(next: StateMsg['scenario'], nextSpeed = 1) {
    t = 0; paused = next === null; speed = nextSpeed; restricted = new Set(); delivered.clear(); history = []; vesselHistories = { T3: [], T4: [] }
    decided = false; scenario = next; mode = next === 'b' ? 'disaster' : 'security'; network = 'online'
    buoys.forEach(buoy => { buoy.status = 'ok' })
    event('scenario_changed', { scenario: next, status: next ? 'started' : 'reset' })
    publish()
    if (next === 'b') event('log', { log: { t, level: 'info', source: 'sim', text: '灾害演示：12/24/45 秒收到预设勘测节点，45 秒收到最终模板复航建议。' } })
  }
  return {
    start() { publish() },
    advance(seconds: number) {
      if (stopped || paused || scenario === null) return
      t = Math.round((t + seconds * speed) * 1000) / 1000
      publish()
    },
    control(action: 'pause' | 'resume' | 'speed' | 'reset', value?: number) {
      if (action === 'pause') paused = true
      if (action === 'resume') paused = false
      if (action === 'speed' && value && [1, 4, 10].includes(value)) speed = value
      if (action === 'reset') { resetScenario(null); return }
      publish()
    },
    startScenario(id: 'a' | 'b', nextSpeed = 1) {
      if (![1, 4, 10].includes(nextSpeed)) throw new Error('倍速须为 1、4 或 10。')
      resetScenario(id, nextSpeed)
    },
    setMode(next: StateMsg['mode']) { mode = next; event('mode_changed', { mode }); publish() },
    inject(body: InjectInput) {
      if (body.type === 'network_down' || body.type === 'network_up') {
        network = body.type === 'network_down' ? 'offline' : 'online'
        event('network_changed', { network })
      } else if (body.type === 'buoy_down' || body.type === 'buoy_up') {
        const buoy = buoys.find(item => item.id === (body.target ?? buoys[0]!.id))
        if (!buoy) throw new Error('未找到指定浮标。')
        buoy.status = body.type === 'buoy_down' ? 'down' : 'ok'
        event('buoy_changed', { buoy_id: buoy.id, status: buoy.status })
      }
      event('log', { log: { t, level: 'info', source: 'operator', text: `本地注入：${body.type}${body.target ? ` · ${body.target}` : ''}` } })
      publish()
    },
    getOptions(alertId: string) {
      if (alertId !== 'A1' || !delivered.has('level3') || mode !== 'security' || scenario !== 'a') throw new Error('该警报的方案尚未就绪。')
      return { alert_id: alertId, options, ranked: options.map(option => option.id) }
    },
    decision(body: DecisionInput) {
      const option = options.find(item => item.id === body.option_id)
      if (!delivered.has('rec') || body.alert_id !== 'A1' || !option || mode !== 'security' || scenario !== 'a') throw new Error('请等待模拟建议生成后再操作。')
      if (decided) throw new Error('该警报已经处理，请重新开始场景后再演示。')
      decided = true
      if (body.action === 'approve') {
        option.zones_closed.forEach(id => { restricted.add(id); event('zone_changed', { zone_id: id, state: 'restricted' }) })
      }
      event('decision', body)
      event('log', { log: { t, level: 'info', source: 'operator', text: body.action === 'approve' ? `已批准：${option.label}。` : `已驳回：${option.label}。` } })
      publish()
    },
    stop() { stopped = true },
  }
}

let activeMock: ReturnType<typeof createMockEngine> | null = null
export function getMock() { return activeMock }

export function startMock(): () => void {
  let disposed = false
  let timer: ReturnType<typeof setInterval> | undefined
  useHarbor.getState().setConnection('mock')
  const init = async () => {
    const resources = await loadLocalData()
    if (disposed) return
    activeMock = createMockEngine(msg => receiveMessage(msg), resources.buoys, resources.assets[0], resources.zones.features.map(zone => zone.properties.id))
    activeMock.start()
    timer = setInterval(() => activeMock?.advance(0.2), 200)
  }
  void init()
  return () => { disposed = true; clearInterval(timer); activeMock?.stop(); activeMock = null }
}

export const eventTrackId = (event: EventMsg): string | null => {
  const data = event.data as { alert?: Alert; detection?: { track_id: string }; recommendation?: Recommendation }
  return data.alert?.track_id ?? data.detection?.track_id ?? data.recommendation?.evidence_ids.find(id => id.startsWith('T')) ?? null
}
