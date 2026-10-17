# 附录：共享契约 v1

三份任务书里这一节完全相同。B 负责维护，H2 冻结；之后任何改动需三人同意，并把版本号改为 v1.1。

## 进程与端口

| 进程 | 负责人 | 地址 |
| --- | --- | --- |
| 后端：仿真 + 感知 + 决策 | B | http://localhost:8000/api ，ws://localhost:8000/ws |
| Agent 服务 | C | http://localhost:8001 |
| 前端 | A | http://localhost:5173 |
| 本地 LLM（Ollama） | C | http://localhost:11434 |

## 约定

坐标用 WGS84 经纬度；depth_m 向下为正，单位米。

本地米制坐标原点 lat0 = 33.7300，lon0 = −118.2600；换算 x_e = (lon − lon0) × 111320 × cos(lat0)，y_n = (lat − lat0) × 110540。

t 为场景开始后的仿真秒数；速度单位 m/s；角度单位度；航向 0° 为正北，顺时针。

风险权重 C 0.30、P 0.25、B 0.25、Z 0.15、D 0.05；risk = 各分项 × 权重之和。

ID 一律为字符串：浮标 B1…B10，航迹 T1…，警报 A1…，识别 det-1…，方案 opt-1… 和 port-closure；分区、资产 ID 见 data 文件。

## 类型定义（TypeScript 写法；Python 侧用 pydantic 一一对应，字段名完全相同）

```typescript
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
```

WebSocket（ws://localhost:8000/ws，服务器单向推送）：state 每秒 5 次，为完整快照；event 发生即推送，信封为 EventMsg。

| event | data |
| --- | --- |
| alert_raised | {alert} |
| alert_changed | {alert, from_level, to_level} |
| alert_cleared | {alert_id} |
| detection | {detection} |
| options_ready | {alert_id, options, ranked}，ranked 为方案 ID 按推荐顺序 |
| recommendation | {recommendation} |
| decision | {alert_id, option_id, action, operator} |
| zone_changed | {zone_id, state} |
| reopen_plan | ReopenPlan |
| buoy_changed | {buoy_id, status} |
| network_changed | {network} |
| mode_changed | {mode} |
| scenario_changed | {scenario, status}，status 为 started、ended、reset |
| log | {log} |

REST（前缀 http://localhost:8000/api）

| 方法 | 路径 | 请求体 | 返回 |
| --- | --- | --- | --- |
| GET | /health | — | {ok: true} |
| GET | /state | — | 最新 state 快照 |
| GET | /events?since_seq=N | — | seq 大于 N 的事件，最多 500 条 |
| GET | /zones | — | GeoJSON FeatureCollection，properties 含当前 state、coverage |
| GET | /assets | — | Asset[] |
| GET | /buoys | — | Buoy[] |
| GET | /tracks/{id} | — | Track（history 不截断） |
| GET | /alerts/{id} | — | Alert |
| GET | /detections/{id} | — | Detection |
| GET | /options/{alert_id} | — | {alert_id, options, ranked} |
| GET | /sonar/{det_id}.png | — | 已画好框和标签的声呐图 |
| GET | /log?limit=100 | — | LogEntry[]，新的在前 |
| GET | /metrics | — | {yolo, lora}，未就绪的为 null |
| POST | /scenario/{id}/start | {speed?} | {ok}；id 为 a 或 b |
| POST | /control | {action, value?}；action 为 pause、resume、speed、reset | {ok} |
| POST | /mode | {mode} | {ok} |
| POST | /inject | {type, target?}；type 为 buoy_down、buoy_up、network_down、network_up、noise_up、noise_down | {ok} |
| POST | /decision | {alert_id, option_id, action, operator}；action 为 approve 或 reject | {ok} |
| POST | /recommendations | Recommendation（Agent 调用） | {ok}，并广播 recommendation 事件 |
| POST | /log | {level, source, text}（Agent 调用） | {ok}，并广播 log 事件 |
| POST | /agent/ask | {question, track_id?} | {answer, model}；后端转发到 Agent 的 POST /ask |

## 静态数据文件（B 维护，放在仓库 data/）

| 文件 | 内容 |
| --- | --- |
| zones.geojson | 分区多边形；properties：id、name、kind（berth、channel、anchorage）、sensitivity（0–1）、berths（泊位数）、neighbors（相邻分区 ID 数组）、entrance（入口航道为 true） |
| assets.json | 受保护资产：id、name、kind、lat、lon、sensitivity、rings_m（一、二、三级圈半径，默认 [1500, 800, 400]） |
| buoys.json | 浮标：id、lat、lon、range_m |
| vessels.json | 虚构船期：id、name、zone_id、movement（arrive、depart、at_berth）、t_h（距现在小时数） |

## B 与 C 之间的 Python 接口

```python
# C 提供：ml/sonar/render.py
def render_ping(targets: list[dict], *, max_range_m: float = 150.0, fov_deg: float = 120.0,
                noise: float = 0.3, seed: int | None = None, size: int = 640
               ) -> tuple["np.ndarray", list[dict]]:
    """targets 每项: {"cls": "uuv" | "fish_school" | "debris" | "marine_mammal",
                      "range_m": float, "bearing_deg": float,   # 相对声呐正前方，-fov/2 到 fov/2
                      "length_m": float, "width_m": float, "aspect_deg": float}
    返回: (size×size 灰度 uint8 图像，扇形顶点在底部中央,
           标注 [{"cls": str, "bbox": [x1, y1, x2, y2]}]，单位像素)"""

# C 提供：ml/yolo/infer.py
class SonarDetector:
    def __init__(self, weights: str = "ml/yolo/weights/best.pt", conf: float = 0.25): ...
    def detect(self, img: "np.ndarray") -> list[dict]:
        """返回 [{"cls": str, "conf": float, "bbox": [x1, y1, x2, y2]}]，CPU 推理"""

# YOLO 类别 ID：0 uuv，1 fish_school，2 debris，3 marine_mammal
```
