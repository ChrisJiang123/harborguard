// 共享契约 v1。字段名与任务书一致，B 维护契约。
export type Cls = 'unknown' | 'uuv' | 'fish_school' | 'debris' | 'marine_mammal' | 'vessel'
export type Level = 0 | 1 | 2 | 3
export type ZoneState = 'open' | 'restricted' | 'clear' | 'unsurveyed' | 'blocked'

export interface StateMsg {
  type: 'state'; seq: number; t: number
  mode: 'security' | 'disaster'; network: 'online' | 'offline'
  scenario: 'a' | 'b' | null; paused: boolean; speed: number
  buoys: Buoy[]; tracks: Track[]; alerts: Alert[]; zones: ZoneStatus[]
}
export interface Buoy { id: string; lat: number; lon: number; status: 'ok' | 'down'; range_m: number; pinging: boolean }
export interface Track {
  id: string; status: 'tentative' | 'confirmed'
  cls: Cls; conf: number
  cue: 'narrowband' | 'broadband' | 'call' | 'none'
  lat: number; lon: number; depth_m: number
  vel_e: number; vel_n: number; vel_d: number; speed_mps: number; heading_deg: number
  err: { a_m: number; b_m: number; angle_deg: number }
  history: [number, number, number, number][]
  predicted: [number, number, number, number][]
  level: Level; risk: number; detection_id: string | null
}
export interface Alert {
  id: string; track_id: string; level: 1 | 2 | 3; risk: number
  breakdown: { C: number; P: number; B: number; Z: number; D: number }
  zone_id: string | null; asset_id: string; distance_m: number; eta_s: number | null
  raised_t: number; updated_t: number; options_ready: boolean
}
export interface ZoneStatus { id: string; state: ZoneState; coverage: number }
export interface Asset { id: string; name: string; kind: string; lat: number; lon: number; sensitivity: number; rings_m: [number, number, number] }
export interface Detection {
  id: string; track_id: string; buoy_id: string; t: number
  cls: Cls; conf: number; bbox: [number, number, number, number]
  image_url: string; model: 'yolo26n' | 'stub'
}
export interface Option {
  id: string; label: string; is_baseline: boolean
  zones_closed: string[]; speed_limit_zones: string[]
  berths_open_pct: number
  vessels_affected: number; delay_vessel_hours: number; residual_risk: number
}
export interface ReopenPlan {
  route_zone_ids: string[]; reopen_berth_zone_ids: string[]
  unsurveyed_zone_ids: string[]; blocked_zone_ids: string[]
  est_hours_saved: number
}
export interface Recommendation {
  id: string; kind: 'security' | 'disaster' | 'buoy'; alert_id: string | null
  model: 'cloud' | 'local' | 'template'
  summary: string; explanation: string
  recommended_option_id: string | null
  evidence_ids: string[]; uncertainties: string[]
  confidence: 'low' | 'medium' | 'high'
  created_t: number; latency_ms: number
}
export interface LogEntry { t: number; level: 'info' | 'warn' | 'critical'; source: 'sim' | 'perception' | 'decision' | 'agent' | 'operator'; text: string }
export interface EventMsg { type: 'event'; seq: number; t: number; event: string; data: unknown }
export type HarborMsg = StateMsg | EventMsg
