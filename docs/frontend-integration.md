# Frontend/Backend/AI Integration Handoff — Frozen v1

2026-10-17 historical update, based on main 782d04d, including A #7/#11, B #10, and C #4. Migrated from old #3/#6 and checked against actual routes. The frozen v1 is unchanged; old template results do not establish acceptance of a newer combination. See [integration check](final-integration-report.md) and [demo runbook](demo-runbook.md).

This documents existing fields/routes/events only. Authority: [shared/contract.md](../shared/contract.md), [shared/types.ts](../shared/types.ts), [C's frozen copy](shared-contract-v1.md). Constraints/schemas: [OpenAPI](integration/openapi.json); [routes](../backend/app/api/rest.py). Chinese original fixtures remain unchanged; English prose/examples below explain the same contract.

## Startup/environment

Python >=3.11; tested version 3.11.17. Commands start at repository root.

```powershell
py -3.11 -m venv .venv
./dev.ps1 setup
$env:HARBORGUARD_DB = Join-Path (Get-Location) 'backend/runtime/handoff-current.sqlite3'
./dev.ps1 backend
# If script execution policy blocks:
# .venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
HARBORGUARD_DB=backend/runtime/handoff-current.sqlite3 python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

One worker. B dependencies: FastAPI, Uvicorn, Pydantic2, NumPy, Shapely, PyYAML, Pillow, OpenCV headless, httpx; see requirements-lock.txt. Main has C code/weights; full integration also needs requirements-runtime.txt and editable B. Missing CPU inference dependencies or weights yield an explicit stub. If Agent is absent, ask returns502. New fingerprint rejects old configured databases: preserve old files and choose an independent path; see [B deployment limits](../backend/docs/sonar-safety-integration.md).

| Purpose | Address |
| --- | --- |
| REST |http://localhost:8000/api|
| Explorer/schema |http://localhost:8000/docs / http://localhost:8000/openapi.json|
| WS |ws://localhost:8000/ws, no /api prefix|
| A |http://localhost:5173;127.0.0.1:5173 also allowed by CORS|
| C/Ollama |http://localhost:8001 / http://localhost:11434|

```powershell
Invoke-RestMethod http://localhost:8000/api/health
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/scenario/a/start -ContentType application/json -Body '{"speed":10}'
Invoke-RestMethod http://localhost:8000/api/state
```

Health/start return ok=true. A new database before scenario start has scenario=null and no tracks. Restarting the same database restores paused. Prior real-YOLO L3 occurred at t=505, approximately50.5 wall seconds at10×, exceeding the original500-second target:FAIL. Old stub timing t=483.1 does not establish real-model timing.

## All REST requests/responses

13 GET and8 POST operations; success status200. POST JSON Content-Type: application/json. Start body is optional; other bodies required; extra fields rejected.

Complete actual payloads are in [backend.json](../backend/fixtures/integration/backend.json) rest array: method, frozen route, sample path, request, status, and response; PNG entry has content_type/asset_url. Business state, Agent response, and sonar image are explicit fixtures. Routes/Pydantic actually execute, not evidence of simulated timing/browser acceptance. Fixed T1/A1 IDs are sample-only. Two decision examples show reject/approve, covering21 distinct operations.

| GET path | Parameters | 200 response |
| --- | --- | --- |
| /api/health |none|{"ok":true}|
| /api/state |none|StateMsg; bundle.state and corresponding REST entry|
| /api/events?since_seq=0 |integer>=0, default0|EventMsg[] with seq strictly>N, within latest500; bundle.events|
| /api/zones |none|FeatureCollection, complete12 polygons in the REST entry|
| /api/assets |none|Asset[], sample5 assets|
| /api/buoys |none|Buoy[], sample10 buoys, status/pinging|
| /api/tracks/{track_id} |e.g.T1|Track, full history|
| /api/alerts/{alert_id} |e.g.A1|Alert|
| /api/detections/{det_id} |e.g.det-1|Detection|
| /api/options/{alert_id} |e.g.A1|{alert_id, options: Option[], ranked: string[]}; sample3 options|
| /api/sonar/{det_id}.png |e.g.det-1|image/png binary, 640×640, annotated boxes/labels; not JSON|
| /api/log?limit=100 |integer1–1000, default100|LogEntry[], newest-first; empty[]|
| /api/metrics |none|{"yolo":null,"lora":null} if unavailable; otherwise C metrics.json|

| POST path | Example/constraints | 200 |
| --- | --- | --- |
| /api/scenario/{scenario_id}/start |a/b; omitted body,{}, or{"speed":10}; speed nullable, number>0<=100|{"ok":true}|
| /api/control |{"action":"pause"}, resume, reset, or{"action":"speed","value":4}; speed requires value>0<=100|{"ok":true}|
| /api/mode |{"mode":"security"} or disaster|{"ok":true}|
| /api/inject |{"type":"buoy_down","target":"B4"}; down/up requires a valid target|{"ok":true}|
| /api/decision |{"alert_id":"A1","option_id":"opt-1","action":"approve","operator":"demo"}; approve/reject; operator length1–100 characters|{"ok":true}|
| /api/recommendations |Complete Recommendation, valid references|{"ok":true}, broadcast recommendation|
| /api/log |{"level":"info","source":"agent","text":"Integration note"}; text length1–2000 characters|{"ok":true}, broadcast log|
| /api/agent/ask |{"question":"Current risk?","track_id":"T1"}; question1–4000, track optional/null|{answer, model}, e.g.template fixture|

inject.type: buoy_down/up, network_down/up, noise_up/down. Network injection changes simulated state, not HTTP/WS connectivity; C uses network for routing. Noise switch is idempotent. Log.level: info/warn/critical; source: sim/perception/decision/agent/operator.

Check response.ok. Errors have {detail:...}:404 means unknown ID/scenario/buoy;409 means stale/noncurrent L3 decision, wrong option, or resume without a scene;422 means invalid type/range/extra fields/Recommendation references;502 means Agent unavailable or invalid response;504 means Agent exceeded20s;503 means runtime or durability unavailable. Write failure must not show success. Validation422 detail is an array; business detail is a string. Sample404/409/422 responses are in bundle.errors. The Detection/PNG memory cache holds64; stored older details restore through existing paths. Only unknown IDs return404; historical objects cannot approve a current scene.

## WebSocket/events

Use native browser WebSocket, with no authentication, subprotocol, or subscription message. Initial full state is followed by5Hz full snapshots; events publish immediately. Controls use REST, not WS commands.

```js
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = ({ data }) => {
  const msg = JSON.parse(data);
  if (msg.type === 'state') console.log('Replace current snapshot', msg);
  if (msg.type === 'event') console.log('Apply event', msg.event, msg.data);
};
ws.onclose = ({ code }) => console.log('Closed; reconnect and recover', code);
ws.onerror = () => console.log('Backend connection failed');
```

State contains {type:"state",seq,t,mode,network,scenario,paused,speed,buoys,tracks,alerts,zones}. t is simulation seconds. States/events share seq, so gaps between events are normal. Same-database restart continues seq.

```json
{"type":"event","seq":10,"t":120,"event":"decision","data":{"alert_id":"A1","option_id":"opt-1","action":"approve","operator":"demo"}}
```

| event | data | A/C handling |
| --- | --- | --- |
| alert_raised |{alert: Alert}|Add alert; C fetches evidence|
| alert_changed |{alert: Alert, from_level, to_level}|Update level; L3 waits for options_ready|
| alert_cleared |{alert_id}|Remove alert; disable old decision|
| detection |{detection: Detection}|Card/image|
| options_ready |{alert_id, options: Option[], ranked: string[]}|Display by ranked IDs|
| recommendation |{recommendation: Recommendation}|Advice, evidence, uncertainty, model|
| decision |{alert_id, option_id, action, operator}|Authoritative approve/reject, emitted after durable storage|
| zone_changed |{zone_id, state}|Zone update; coverage from state/zones|
| reopen_plan |{route_zone_ids, reopen_berth_zone_ids, unsurveyed_zone_ids, blocked_zone_ids, est_hours_saved}|Recovery plan|
| buoy_changed |{buoy_id, status}|Buoy|
| network_changed |{network}|Connectivity/C route|
| mode_changed |{mode}|security/disaster|
| scenario_changed |{scenario, status}, started/ended/reset|Clear old derived caches/buttons|
| log |{log:{t, level, source, text}}|Event log|

Fourteen standalone examples are in bundle.event_catalogue and [frozen samples](../shared/sample_events.json). They form a format catalogue, not one sequential demo. bundle.events/state represent a single static instant; decision_examples separately show later reject/approve and must not be replayed backward over that snapshot.

On reconnect, open WS and buffer messages, restore initial state, then fetch /api/events?since_seq=N using the last processed event cursor. Merge in seq order, including live advice/logs/decisions received during REST. Old REST must not overwrite fresh WS. Same-time identical logs and different operators require seq identity, not only t/text/action. Option details need request-generation/sequence protection.

A lower initial seq can indicate a replacement database/service or rollback, rather than normal same-database restart. On first connection, do not compare against state that advanced while REST waited. Durable internal history does not extend /events beyond500; there is no pagination,total,or truncation marker. /log exposes a current cache of at most1000. State seq gaps do not prove event loss. Degrade honestly and never derive approval from prose. Slow clients close with1013. Reset/start preserve seq; alert/detection IDs continue in the same database.

## Position/acoustic/track/risk structures

| Type | Fields/units |
| --- | --- |
| Position |WGS84 lat/lon; depth_m positive down; history/predicted=[lat, lon, depth_m, t]; GeoJSON=[lon, lat]|
| Motion |vel_e/n/d east/north/down m/s; heading clockwise from north; speed_mps horizontal|
| Track |id, status tentative/confirmed, cls unknown/uuv/fish_school/debris/marine_mammal/vessel, conf0–1, cue narrowband/broadband/call/none, detection_id string/null|
| Uncertainty/path |err:{a_m, b_m, angle_deg}, 1σ ellipse; state history last60 points, detail full history; prediction5min, every30s|
| Risk |level0/1/2/3, risk0–1; 0 absent from alert list; A uses backend level without recalculation|
| Alert |id, track_id, level, risk, breakdown, zone_id, asset_id, distance_m, eta_s, raised_t, updated_t, options_ready; zone_id/eta_s nullable; time in simulation seconds|
| Detection |id, track_id, buoy_id, t, cls, conf, bbox, image_url, model; bbox pixel corners[x1, y1, x2, y2]; model yolo26n/stub|
| Buoy |id, lat, lon, status ok/down, range_m, pinging|
| ZoneStatus |id, state open/restricted/clear/unsurveyed/blocked, coverage0–1|
| Asset |id, name, kind, lat, lon, sensitivity, rings_m three-ring radii in meters|
| Option |id, label, is_baseline, zones_closed, speed_limit_zones, berths_open_pct, vessels_affected, delay_vessel_hours, residual_risk; fractions0–1|

breakdown C/P/B/Z/D are unweighted classification/proximity/behavior/zone/duration components. R=0.30*C+0.25*P+0.25*B+0.15*Z+0.05*D. L1 threshold is0.20; L2 requires R>=0.40 or B>0.8; L3 additionally requires R>=0.70, confirmed tracking, and distance<=400m or ETA<600s. Escalation is immediate; ordinary de-escalation has30 simulation seconds of hysteresis. AIS vessels do not raise alerts. A displays B's level.

Passive observations stay internal; the frozen contract has no corresponding REST/WS:

```json
{"buoy_id":"B1","bearing_deg":12.5,"elevation_deg":4.2,"snr_db":18.0,"noise_level_db":60.0,"bearing_sigma_deg":3.3,"cue":"narrowband"}
```

Bearing is clockwise from north; elevation is positive down. Measurements contain no truth ID,class,or position. Localization returns internal {x,y,depth,covariance,cue}, in local east/north/down meters with3×3m² covariance, then outputs Track. Target x/y/depth/vx/vy/vz are not frontend data. A raw-observation UI requires an approved contract change.

Complete Track/Alert/Detection/Option examples are in bundle.rest. Disaster track_id may be an empty string; use Detection ID and do not request an empty track. Live image_url resolves against B's root on8000; replay images resolve against the frontend. PNGs are already annotated; A need not draw boxes again.

## Human approval/AI

1. L3options_ready: A shows current options from event/detail; CgathersTrack/Alert/Detection/Optionevidence.
2. C POSTs a complete Recommendation; B validates and broadcasts it. English illustrative variant of the static fixture:

```json
{
  "id":"rec-sample-1","kind":"security","alert_id":"A1","model":"template",
  "summary":"Review the smallest closure",
  "explanation":"Integration example. An operator must review tracks and risk before approving.",
  "recommended_option_id":"opt-1","evidence_ids":["T1","A1","det-1"],
  "uncertainties":["Demonstration data"],"confidence":"medium","created_t":120,"latency_ms":0
}
```

3. Only an operator's Approve action POSTs a decision. Confirm the response and zone_changed/state before claiming a restriction. options_ready and recommendation never close zones; the model cannot approve.
4. Approve and reject persist first, then emit decision, operator log, and ok. Reject neither adds nor revokes existing restrictions. Approve uses the current option. Failure returns503 and must not show success. Stale/non-L3 decisions return409 and must not be retried automatically. The structured event is authoritative, not prose.

Recommendation.kind security/disaster/buoy; model cloud/local/template; confidence low/medium/high; summary<=60 and explanation<=300 characters. alert_id/recommended_option_id may be null; otherwise they reference a currently valid alert and its own option. evidence_ids may reference only existing tracks, alerts, detections, buoys, zones, assets, and options.

C implements POST http://localhost:8001/ask with {question,track_id?} and response {answer,model}. A calls B /api/agent/ask. B timeout is20s and C's budget18s. No latest-advice REST endpoint was added; state lacks recommendation/options/reopen_plan. Recover using state, details, and recent events; access to complete older history remains limited.

C sonar interfaces ml/sonar/render.py:render_ping and ml/yolo/infer.py:SonarDetector follow the frozen signatures. B passes max_range_m=300, fov_deg=120, noise=0.3, seed, and size=640. Results are grayscale uint8 and pixel-corner boxes. Default weights: ml/yolo/weights/best.pt. Missing or failing modules/weights fall back to stub; retain the actual model label.

## Direct-use mocks/replay

Mocks live in B-owned backend/fixtures/integration/. A chooses import or static packaging. This handoff does not write frontend files. Image mapping is relative to backend.json:

```js
const bundle = JSON.parse(require('node:fs').readFileSync('backend/fixtures/integration/backend.json', 'utf8'));
const state = bundle.state;
const options = bundle.rest.find(x => x.method === 'GET' && x.path === '/api/options/A1').response;
const detection = bundle.rest.find(x => x.method === 'GET' && x.path === '/api/detections/det-1').response;
const imageUrl = bundle.mock_images[detection.image_url];
console.log(state, options, imageUrl, bundle.events);
```

Mock data pass through real routes, but the PNG is an explicit B layout illustration matching bbox, not measured recognition. Fixed IDs are not valid LIVE approvals. Replay lines are {wall_ms,msg}, scheduled by wall_ms. A also includes synthetic demonstration replays: check provenance/model and never describe an old stub as current YOLO. This handoff did not overwrite A replays.

Existing static files are /data/zones.geojson, assets.json, buoys.json, and vessels.json. Original buoy data lack status/pinging; obtain dynamic fields from REST or mock state.

```powershell
# Regenerate OpenAPI/mock; no contract or production API change.
.venv/Scripts/python.exe -m backend.tools.integration_bundle
./dev.ps1 test
./dev.ps1 check
```

Integration order: mock layout → B health/initial WS/5Hz → A L3/options/approve/reject → faults/reset/reconnect → B debris/reopening → offline A/B Replay → C recognition/Agent/offline fallback → team rehearsal.

Limits: B uses schematic geometry/schedules. A's NOAA/proposed sonar deployment and B's LIVE observations are separate sources. Never move LIVE buoys for appearance. Delivered YOLO was tested on synthetic sonar, not at sea. This handoff does not enable cloud/Ollama/LoRA runtime.20ms is best effort; correctness, history consistency, and5Hz come first. See [integration](final-integration-report.md) and the [original checkbox report](../backend/docs/B-final-acceptance.md).
