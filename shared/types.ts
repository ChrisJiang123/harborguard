// Shared contract v1, copied verbatim from the taskbook.
type Cls = "unknown" | "uuv" | "fish_school" | "debris" | "marine_mammal" | "vessel";
type Level = 0 | 1 | 2 | 3;   // 0 = 背景，不进警报列表
type ZoneState = "open" | "restricted" | "clear" | "unsurveyed" | "blocked";

interface StateMsg {
  type: "state"; seq: number; t: number;
  mode: "security" | "disaster"; network: "online" | "offline";
  scenario: "a" | "b" | null; paused: boolean; speed: number;
  buoys: Buoy[]; tracks: Track[]; alerts: Alert[]; zones: ZoneStatus[];
}
interface Buoy { id: string; lat: number; lon: number; status: "ok" | "down"; range_m: number; pinging: boolean; }
interface Track {
  id: string; status: "tentative" | "confirmed";
  cls: Cls; conf: number;                              // 未经主动 ping 识别时 cls = "unknown"
  cue: "narrowband" | "broadband" | "call" | "none";   // 被动声学线索
  lat: number; lon: number; depth_m: number;
  vel_e: number; vel_n: number; vel_d: number; speed_mps: number; heading_deg: number;
  err: { a_m: number; b_m: number; angle_deg: number }; // 1σ 误差椭圆
  history: [number, number, number, number][];         // [lat, lon, depth_m, t]，state 中最多 60 点
  predicted: [number, number, number, number][];       // 未来 5 分钟，每 30 秒一点
  level: Level; risk: number; detection_id: string | null;
}
interface Alert {
  id: string; track_id: string; level: 1 | 2 | 3; risk: number;
  breakdown: { C: number; P: number; B: number; Z: number; D: number };  // 各 0–1，未加权
  zone_id: string | null; asset_id: string; distance_m: number; eta_s: number | null;
  raised_t: number; updated_t: number; options_ready: boolean;
}
interface ZoneStatus { id: string; state: ZoneState; coverage: number; }   // coverage 0–1
interface Asset { id: string; name: string; kind: string; lat: number; lon: number; sensitivity: number; rings_m: [number, number, number]; }
interface Detection {
  id: string; track_id: string; buoy_id: string; t: number;
  cls: Cls; conf: number; bbox: [number, number, number, number];   // 像素 x1, y1, x2, y2
  image_url: string; model: "yolo26n" | "stub";
}
interface Option {
  id: string; label: string; is_baseline: boolean;
  zones_closed: string[]; speed_limit_zones: string[];
  berths_open_pct: number;      // 0–1
  vessels_affected: number; delay_vessel_hours: number; residual_risk: number;  // residual 0–1
}
interface ReopenPlan {
  route_zone_ids: string[]; reopen_berth_zone_ids: string[];
  unsurveyed_zone_ids: string[]; blocked_zone_ids: string[];
  est_hours_saved: number;      // 按每区勘测 survey_h 小时的假设计算
}
interface Recommendation {
  id: string; kind: "security" | "disaster" | "buoy"; alert_id: string | null;
  model: "cloud" | "local" | "template";
  summary: string;              // ≤ 60 字
  explanation: string;          // ≤ 300 字
  recommended_option_id: string | null;
  evidence_ids: string[];       // 只能引用存在的 ID
  uncertainties: string[];
  confidence: "low" | "medium" | "high";
  created_t: number; latency_ms: number;
}
interface LogEntry { t: number; level: "info" | "warn" | "critical"; source: "sim" | "perception" | "decision" | "agent" | "operator"; text: string; }
interface EventMsg { type: "event"; seq: number; t: number; event: string; data: unknown; }
