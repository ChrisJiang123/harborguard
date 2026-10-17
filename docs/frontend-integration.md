# 前后端与 AI 联调交接（冻结契约 v1）

本文整理现有实现，不新增或修改字段、路由与事件。权威契约：[shared/contract.md](../shared/contract.md)、[shared/types.ts](../shared/types.ts)、[C 的契约副本](shared-contract-v1.md)。参数约束与响应 Schema 见 [OpenAPI JSON](integration/openapi.json)，路由实现见 [rest.py](../backend/app/api/rest.py)。

## 启动与环境

Python >=3.11，本机已验证 Python 3.11.17。所有命令从仓库根目录执行。

```powershell
# Windows：已安装 Python 3.11 时
py -3.11 -m venv .venv
./dev.ps1 setup
./dev.ps1 backend
# 若脚本执行策略阻止启动，可直接运行：
# ./.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```bash
# macOS / Linux
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

仅运行一个 worker。运行依赖为 FastAPI、Uvicorn、Pydantic 2、NumPy、Shapely、PyYAML、Pillow、OpenCV headless、httpx；确切版本及测试工具见 requirements-lock.txt。B 独立演示无需密钥、Ollama 或模型权重；C 未就绪时识别标记 stub，问答返回 502。完整 C 环境还需其 requirements-runtime.txt，安装顺序见 backend/README.md。

| 用途 | 地址 |
| --- | --- |
| REST 基址 | `http://localhost:8000/api` |
| 交互式文档 / Schema | `http://localhost:8000/docs` / `http://localhost:8000/openapi.json` |
| WebSocket | `ws://localhost:8000/ws`，没有 `/api` 前缀 |
| A 前端 | `http://localhost:5173`；也允许 127.0.0.1:5173 跨域 |
| C Agent / Ollama | `http://localhost:8001` / `http://localhost:11434` |

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/scenario/a/start -ContentType application/json -Body '{"speed":10}'
Invoke-RestMethod http://localhost:8000/api/state
```

health/start 预期 `{"ok":true}`。场景启动前 scenario 为 null、航迹为空。场景 A 在 10× 下约 48.31 秒触发三级；不要因刚启动没有方案就判定失败。

## 所有 REST 请求与响应

共 13 GET、8 POST；成功均为 200。JSON POST 使用 `Content-Type: application/json`，除 start 的 body 可省略，其他 body 必传；额外字段不被接受。

**逐个接口的完整、可复制 JSON** 位于 [frontend/public/mock/backend.json](../frontend/public/mock/backend.json) 的 `rest` 数组，每项包含 method、冻结 route、实际示例 path、request（POST）、status、response；PNG 项含 content_type/asset_url。所有请求经真实 FastAPI 路由执行和响应模型校验，只有 Agent 成功回答使用 MockTransport。T1/A1 等是静态样例 ID；实时调用使用当前服务返回的 ID。

| GET 路径 | 请求参数 | 200 响应 / 完整示例位置 |
| --- | --- | --- |
| `/api/health` | 无 | `{"ok":true}` |
| `/api/state` | 无 | StateMsg；backend.json 的 state 与对应 REST 条目 |
| `/api/events?since_seq=0` | since_seq 整数 >=0，默认 0 | seq 严格大于该值的 EventMsg[]，最多最近 500 个事件；示例在 events |
| `/api/zones` | 无 | GeoJSON FeatureCollection；REST 条目含完整 12 区多边形 |
| `/api/assets` | 无 | Asset[]，示例含 5 个资产 |
| `/api/buoys` | 无 | Buoy[]，示例含 10 个浮标及 status/pinging |
| `/api/tracks/{track_id}` | 例如 T1 | Track，完整 history；示例 `/api/tracks/T1` |
| `/api/alerts/{alert_id}` | 例如 A1 | Alert；示例 `/api/alerts/A1` |
| `/api/detections/{det_id}` | 例如 det-1 | Detection；示例 `/api/detections/det-1` |
| `/api/options/{alert_id}` | 例如 A1 | `{alert_id,options:Option[],ranked:string[]}`；示例含 3 个方案 |
| `/api/sonar/{det_id}.png` | 例如 det-1 | image/png 二进制，640×640，已绘制框和标签；不是 JSON |
| `/api/log?limit=100` | limit 整数 1–1000，默认 100 | LogEntry[]，新的在前；无日志为 [] |
| `/api/metrics` | 无 | 未就绪为 `{"yolo":null,"lora":null}`；就绪时读取 C 的 metrics.json |

| POST 路径 | JSON 请求示例 / 约束 | 200 响应 |
| --- | --- | --- |
| `/api/scenario/{scenario_id}/start` | id 为 a/b；body 可省略，或 `{}`、`{"speed":10}`；speed 可空，数值须 >0 且 <=100 | `{"ok":true}` |
| `/api/control` | `{"action":"pause"}` / `{"action":"resume"}` / `{"action":"reset"}` / `{"action":"speed","value":4}`；speed 必带 >0 且 <=100 的 value | `{"ok":true}` |
| `/api/mode` | `{"mode":"security"}` 或 `{"mode":"disaster"}` | `{"ok":true}` |
| `/api/inject` | `{"type":"buoy_down","target":"B4"}`；浮标 down/up 必带有效 target | `{"ok":true}` |
| `/api/decision` | `{"alert_id":"A1","option_id":"opt-1","action":"approve","operator":"demo"}`；action approve/reject，operator 非空且 <=100 字符 | `{"ok":true}` |
| `/api/recommendations` | 完整 Recommendation，见下方 JSON，引用 ID 必须有效 | `{"ok":true}`，广播 recommendation |
| `/api/log` | `{"level":"info","source":"agent","text":"联调日志"}`；text 1–2000 字符 | `{"ok":true}`，广播 log |
| `/api/agent/ask` | `{"question":"当前风险如何？","track_id":"T1"}`；question 1–4000 字符，track_id 可省略/null | 示例 `{"answer":"这是联调 Mock 回答；请由操作员审核当前方案。","model":"template"}` |

inject.type：buoy_down/buoy_up/network_down/network_up/noise_up/noise_down；例如 `{"type":"network_down"}`。网络故障只改变仿真状态，不断开 HTTP/WS，由 C 根据 network 选择模型；噪声开关幂等。Log.level 为 info/warn/critical，source 为 sim/perception/decision/agent/operator。

错误响应为 `{"detail":...}`，先检查 response.ok：404 表示 ID/场景/浮标不存在；409 表示过期或非当前三级审批、方案不属于警报、无活动场景时 resume；422 为参数类型/范围/多余字段或无效 Recommendation 引用；502 为 Agent 不可达/无效响应；504 为 Agent 超过 20 秒；503 为仿真异常暂停后的 health。参数 422 的 detail 为数组，业务错误的 detail 为字符串。实际 404/409/422 示例在 backend.json 的 errors；例如 `{"detail":"Unknown track: missing"}`。Detection/PNG 缓存最多 64 条，旧 ID 可 404。

## WebSocket 和事件交接

浏览器原生 WS，无鉴权、无子协议、无需发送订阅消息。连接即收到一个 state，后续 state 为 5 Hz 完整快照，event 实时发送；控制操作均走 REST，WS 不处理命令。

```js
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data);
  if (msg.type === 'state') console.log('替换当前快照', msg);
  if (msg.type === 'event') console.log('处理事件', msg.event, msg.data);
};
ws.onclose = ({ code }) => console.log('连接关闭，重连后恢复视图', code);
ws.onerror = () => console.log('后端连接失败');
```

state 信封为 `{type:"state",seq,t,mode,network,scenario,paused,speed,buoys,tracks,alerts,zones}`，完整可解析 JSON 在 backend.json 的 state。t 是仿真秒；seq 为进程内 state/event 共用序列，事件间 seq 跳号正常。完整事件信封示例：

```json
{"type":"event","seq":10,"t":120,"event":"decision","data":{"alert_id":"A1","option_id":"opt-1","action":"approve","operator":"demo"}}
```

| event | data 结构 | A / C 处理 |
| --- | --- | --- |
| alert_raised | `{alert:Alert}` | 新增警报，C 获取证据 |
| alert_changed | `{alert:Alert,from_level,to_level}` | 更新等级，三级等待 options_ready |
| alert_cleared | `{alert_id}` | 移除警报，禁用旧审批 |
| detection | `{detection:Detection}` | 识别卡片与图片 |
| options_ready | `{alert_id,options:Option[],ranked:string[]}` | 按 ranked 的 ID 顺序展示方案 |
| recommendation | `{recommendation:Recommendation}` | 展示建议、证据、不确定性、模型来源 |
| decision | `{alert_id,option_id,action,operator}` | 记录批准；reject 当前只产生日志 |
| zone_changed | `{zone_id,state}` | 更新分区，coverage 从 state/zones 获取 |
| reopen_plan | `{route_zone_ids,reopen_berth_zone_ids,unsurveyed_zone_ids,blocked_zone_ids,est_hours_saved}` | 灾后复航展示 |
| buoy_changed | `{buoy_id,status}` | 浮标状态 |
| network_changed | `{network}` | 联网提示，C 模型切换 |
| mode_changed | `{mode}` | security/disaster 展示 |
| scenario_changed | `{scenario,status}`，status started/ended/reset | 清除旧场景派生缓存与按钮 |
| log | `{log:{t,level,source,text}}` | 事件日志 |

14 种完整独立样例见 backend.json 的 event_catalogue 与 [shared/sample_events.json](../shared/sample_events.json)。它们是格式目录，不能按序当成一次演示；backend.json 的 events 与其 state 则是同一静态时点。

重连：先打开 WS 并缓冲消息，用首个 state 恢复实体视图，然后以断线前的**事件游标**调用 `/api/events?since_seq=N` 补日志，按 seq 排序去重。历史事件不要倒放覆盖新快照；只将快照之后缓冲的消息用于更新当前视图。不要先把游标提升到新快照 seq 再请求补偿，否则会漏历史事件。

新快照 seq 小于上次所见 seq 表示进程重启，应丢弃旧游标及缓存。断线过久可能超过 500 条缓存；响应没有缺口标志，不保证永久日志，应从快照重建并提示日志可能不完整。慢客户端队列满会以 1013 关闭，再按上述步骤恢复。reset/start 不重置进程 seq；同一进程内警报、检测 ID 不复用。

## 目标位置、声呐观测、航迹与风险结构

| 类型 | 字段 / 单位 |
| --- | --- |
| 位置 | WGS84 lat/lon；depth_m 米，向下为正；history/predicted 点为 **[lat,lon,depth_m,t]**，GeoJSON 坐标为 **[lon,lat]** |
| 运动 | vel_e/vel_n/vel_d 为东/北/向下速度 m/s；heading_deg 从北顺时针；speed_mps 是水平速度 |
| Track 标识与分类 | id；status tentative/confirmed；cls unknown/uuv/fish_school/debris/marine_mammal/vessel；conf 0–1；cue narrowband/broadband/call/none；detection_id string/null |
| Track 误差与路径 | err:{a_m,b_m,angle_deg} 为 1σ 椭圆；state.history 最多 60 点，GET 单航迹保留完整历史；predicted 未来 5 分钟每 30 秒一点 |
| Track 风险 | level 0/1/2/3；risk 0–1；0 不进警报列表；前端使用服务 level，不自行按 risk 重算 |
| Alert | id,track_id,level,risk,breakdown,zone_id,asset_id,distance_m,eta_s,raised_t,updated_t,options_ready；zone_id/eta_s 可空，时间为仿真秒 |
| Detection | id,track_id,buoy_id,t,cls,conf,bbox,image_url,model；bbox 是像素角点 [x1,y1,x2,y2]；model yolo26n/stub |
| Buoy | id,lat,lon,status,range_m,pinging；status ok/down；range_m 米 |
| ZoneStatus | id,state,coverage；state open/restricted/clear/unsurveyed/blocked，coverage 0–1 |
| Asset | id,name,kind,lat,lon,sensitivity,rings_m；rings_m 为三级圈半径数组，米 |
| Option | id,label,is_baseline,zones_closed,speed_limit_zones,berths_open_pct,vessels_affected,delay_vessel_hours,residual_risk；比例均为 0–1 |

breakdown.C/P/B/Z/D 是未加权的分类/资产接近/行为/分区敏感度/持续时间分量。`R=0.30*C+0.25*P+0.25*B+0.15*Z+0.05*D`；一级阈值 0.20；二级 R>=0.40 或 B>0.8；三级还需 R>=0.70、confirmed，且距离<=400 米或 ETA<600 秒。升级立即，普通降级迟滞 30 仿真秒；AIS vessel 不告警。前端直接展示后端 level。

原始被动声学观测只在 B 内部流转，冻结契约没有对应 REST/WS：

```json
{"buoy_id":"B1","bearing_deg":12.5,"elevation_deg":4.2,"snr_db":18.0,"noise_level_db":60.0,"bearing_sigma_deg":3.3,"cue":"narrowband"}
```

方位从北顺时针，俯角向下为正；观测不带真值目标 ID、类别或位置。定位内部返回 `{x,y,depth,covariance,cue}`，位置为本地东/北/向下米制，covariance 为 3×3 米平方矩阵，再输出 Track。仿真 Target 的 x/y/depth/vx/vy/vz 不供前端消费。若要原始观测可视化，需先共同批准契约变更，本次不新增接口。

完整 Track/Alert/Detection/Option JSON 在 backend.json 对应 REST 条目。灾害 Detection.track_id 可为 `""`，A 按检测 ID 展示，不请求空航迹。实时 image_url 相对 **8000 后端根地址**，回放图片相对前端站点。PNG 已画框，A 不需重复画框。

## 人工审批与 AI 对接

1. 三级收到 options_ready 后，A 从事件或 GET `/api/options/{alert_id}` 展示方案，C 获取 Track/Alert/Detection/Option 证据。
2. C POST 完整 Recommendation 到 `/api/recommendations`，B 校验并广播。以下是完整静态样例：

```json
{
  "id":"rec-sample-1","kind":"security","alert_id":"A1","model":"template",
  "summary":"建议审核最小封闭方案",
  "explanation":"此为联调样例。请结合航迹和风险指标由操作员确认方案。",
  "recommended_option_id":"opt-1","evidence_ids":["T1","A1","det-1"],
  "uncertainties":["演示数据"],"confidence":"medium","created_t":120,"latency_ms":0
}
```

3. A 展示建议，只有操作员点击批准才 POST `/api/decision`；确认响应及 zone_changed/state 后更新限制。options_ready/recommendation 不会封区；模型不代操作员 approve。
4. reject 返回 ok 并写日志，不发 decision、不增加限制。过期或非三级审批返回 409：刷新快照、提示重新选择，不自动重试审批。

Recommendation.kind 为 security/disaster/buoy，model cloud/local/template，confidence low/medium/high；summary<=60、explanation<=300 字符。alert_id/recommended_option_id 可 null；非空必须是当前有效警报及其所属方案。evidence_ids 只能引用存在的航迹、警报、识别、浮标、分区、资产、方案。

C 实现 `POST http://localhost:8001/ask`，请求 `{question,track_id?}`，响应 `{answer,model}`；A 只调用 B `/api/agent/ask`。B 超时 20 秒，C0 本地模型预算 30 秒：C 应在 20 秒内响应或提前降级，本次不修改契约。没有获取最新建议的 REST，state 也不含 recommendation/options/reopen_plan，须处理事件和近期缓存。

C 声呐接口为 `ml/sonar/render.py:render_ping`、`ml/yolo/infer.py:SonarDetector`，签名见共享契约。B 显式传 max_range_m=300、fov_deg=120、noise=0.3、seed、size=640；返回灰度 uint8、像素角点框。权重默认 ml/yolo/weights/best.pt，缺模块/权重或失败回退 stub，A 保留模型来源标签。

## 前端直接使用 Mock 与回放

新增 public/mock/backend.json。A 的 Vite 可以直接请求，不需要 B 在线：

```js
const bundle = await fetch('/mock/backend.json').then(r => r.json());
const state = bundle.state;
const options = bundle.rest.find(x => x.method === 'GET' && x.path === '/api/options/A1').response;
const detection = bundle.rest.find(x => x.method === 'GET' && x.path === '/api/detections/det-1').response;
const imageUrl = bundle.mock_images[detection.image_url];
console.log(state, options, imageUrl, bundle.events);
```

Mock 为既有 v1 合成样例，经真实路由返回；mock_images 复用已有声呐 PNG 作布局示意，不新增图片/模型。固定 ID 只用于静态展示，Mock 按钮应在前端模拟，不可用于实时审批。真实时序与图片对应关系请用 `/replay_a.jsonl`、`/replay_b.jsonl`，每行 `{wall_ms,msg}`，按 wall_ms 调度，msg 与实时信封一致；A 的回放器仍需实现验收。

已有静态文件 `/data/zones.geojson`、`/data/assets.json`、`/data/buoys.json`、`/data/vessels.json`。原始 buoys 无 status/pinging，动态字段从 REST 或 Mock state 获取。本次不修改前端源码。

```powershell
# 重新生成 OpenAPI 与 Mock；不修改契约或生产 API
./.venv/Scripts/python.exe -m backend.tools.integration_bundle
./dev.ps1 test
./dev.ps1 check
```

联调顺序：Mock 布局 → B health/WS 首帧与 5Hz → 场景 A 三级/方案/approve/reject → 故障、reset、断线重连去重 → 场景 B 碎片与复航 → 两份离线回放 → C 真实识别/Agent/离线降级 → 三人演示彩排。

边界：港区为人工示意几何，未核验水陆；A UI/回放器、C 真实声呐/Agent 尚待联调；此前 20 分钟耐久检查通过，但单 tick <20ms 仍有峰值超限。本次仅准备联调，不新增功能，详见 [验证记录](validation.md)、[验收清单](acceptance.md)。
