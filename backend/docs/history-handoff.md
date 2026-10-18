# History Recovery Handoff for A — Frozen v1 Contract

Date: 2026-10-17. B branch: codex/harborguard-backend-history, based on official main@5817b9c. This historical change modified B implementation, migrations, tests, documentation, and fixtures only; no extra A/C commits were merged or rewritten.

A's frontend/B-HANDOFF.md was reviewed. A advanced from8f4a860 to456b808 during the final Fetch (3D contours/labels; handoff unchanged). A browser acceptance was not run on this B branch. **The owner must first integrate B into the team branch; this document does not mean a remote service is deployed.**

## Forward directly to A

1. B now emits action reject in the existing frozen decision event. Approve/reject/recommendations write SQLite before returning ok or broadcasting. Storage failure returns503. First verify whether #7's existing handler works without frontend changes.
2. Structured decision is authoritative. Order/deduplicate by seq; recommendation cards use recommendation.id and alert_id/option_id. Never infer decisions from log prose or show success merely because POST was sent. On503/network error, requery; do not automatically repeat approvals.
3. Same-database restart preserves increasing seq, recent500 events, current state, details, PNGs, and recent logs. Restored simulation is paused and needs Resume. Ordinary reconnect need not discard history. Keep sequence-rollback protection for replaced databases/old versions.
4. **Pagination beyond500 is neither approved nor implemented.** Retain incomplete-history/state-unconfirmed UI and do not call the proposed endpoint below. Exactly500 does not prove truncation; seq gaps can come from states.
5. Alert still has no decision-state field. options_ready, detail HTTP200, or zone state cannot establish approve/reject. Details may be last-known historical objects; current activity comes from latest state. Reject does not revoke earlier approved restrictions, which persist until reset/new scenario.
6. Real B A10× at this historical stub baseline: L1~3.8 wall s, L2~15.1, L3/options~48.4. t=90 is simulation time and precedes L2; allow50–60 wall s. Use actual IDs, not hardcoded A1/T1.
7. Empty-track debris in Recovery opens details/image_url by Detection ID, never an empty-track request. Four PNGs passed backend transport validation; model=stub, not real-model acceptance.
8. In the integrated branch, browser-test refresh after approve/reject, WS reconnect, B restart, and degradation beyond500. DEM/tides/new3D remain A's work. API tests are not actual frontend/backend browser acceptance.

## Startup from repository root

Python>=3.11 with the team's prepared .venv and requirements-lock.txt. SQLite is standard-library and needs no external service/package.

```powershell
# First install/update only; not part of prepared-dependency startup timing.
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-lock.txt
.venv/Scripts/python.exe -m pip install --no-deps -e .
$env:DEBUG_TRUTH_TRACKS = '0'
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Optional fixed path before startup: HARBORGUARD_DB=C:/HarborGuardData/demo.sqlite3. Reuse the same absolute path; relative paths resolve against startup directory. Do not use :memory: for persistence demonstrations. Use one worker, no --reload for continuous-operation acceptance; a second writer to the file is refused.

Initial startup runs backend/migrations/001_history.sql automatically. Its version is internal storage, not API version. Incompatible configuration/data/checkpoint rejects restoration rather than silently losing history; B must review migration. Do not delete the database as a fix. For backups, stop services and copy database plus surviving -wal/-shm, or use SQLite backup. Checkout/editable startup was tested, not standalone wheel distribution.

REST http://127.0.0.1:8000/api; WS ws://127.0.0.1:8000/ws; explorer /docs. CORS remains localhost:5173 and127.0.0.1:5173. C Agent stays on8001; this branch neither replaces the verified template nor enables cloud routing.

```powershell
$api = 'http://127.0.0.1:8000/api'
Invoke-RestMethod "$api/health"
Invoke-RestMethod -Method Post "$api/scenario/a/start" -ContentType application/json -Body '{"speed":10}'
# Wait for actual L3/options. A1/opt-1 below are fixture-only IDs.
Invoke-RestMethod -Method Post "$api/decision" -ContentType application/json -Body '{"alert_id":"A1","option_id":"opt-1","action":"reject","operator":"demo"}'
Invoke-RestMethod "$api/events?since_seq=0"
Invoke-RestMethod -Method Post "$api/control" -ContentType application/json -Body '{"action":"pause"}'
Invoke-RestMethod -Method Post "$api/control" -ContentType application/json -Body '{"action":"resume"}'
```

## Existing 21 REST operations — no new endpoint

Authoritative fields: shared/contract.md, shared/types.ts, backend/app/models.py. Expand response schemas in /docs; complete actual JSON is in backend/fixtures/history/.

| Method/path, all under /api | Parameters/body | Success/limits |
| --- | --- | --- |
| GET /health | None | ok=true; runtime/storage error503 |
| GET /state | None | Complete StateMsg; no recommendation/decision fields |
| GET /events | since_seq=0, nonnegative | Ascending events with seq>N from latest500; not pagination |
| GET /zones | None | ZoneCollection GeoJSON with current state/coverage |
| GET /assets | None | Asset[] |
| GET /buoys | None | Buoy[] |
| GET /tracks/{track_id} | ID | Current Track, otherwise last-known archive; T IDs may repeat across scenarios |
| GET /alerts/{alert_id} | ID | Current Alert, otherwise archive; no decision-state field |
| GET /detections/{det_id} | ID | Detection, original model/image_url |
| GET /options/{alert_id} | ID | {alert_id,options,ranked}, including last-known archive |
| GET /sonar/{det_id}.png | ID | image/png; falls back from memory to stored PNG |
| GET /log | limit100, range1–1000 | Newest-first current-scene LogEntry[]; no decision semantics/pagination |
| GET /metrics | None | yolo/lora metrics or null |
| POST /scenario/{id}/start | a/b, optional {"speed":10} | ok; clears current objects, not history |
| POST /control | pause/resume/reset; speed requires value | ok; resume without restorable scene409 |
| POST /mode | {"mode":"security"} or disaster | ok |
| POST /inject | {"type":"buoy_down","target":"B4"} | ok; also buoy_up/network_down/up/noise_up/down |
| POST /decision | alert_id,option_id,approve/reject,operator | Atomic persistence before ok; inactive L3/no options409 |
| POST /recommendations | Complete Recommendation | ok; bad structure/current references422 |
| POST /log | {"level":"info","source":"operator","text":"Note"} | ok |
| POST /agent/ask | {"question":"Current risk?","track_id":null} | {answer,model}; unavailable502,20s timeout504 |

Unknown detail IDs return404. Historical details are not active objects: decisions on reset/cleared alerts still409. /log remains latest1000, clearing current log on new scene/reset. Archived log events remain internal, but v1 cannot page through them. Alert/detection counters increase across same-database restarts; Track IDs still restart atT1 per scenario and are not globally unique. Previously memory-only history cannot be recovered retroactively.

## WebSocket/recovery ordering

Use new WebSocket('ws://127.0.0.1:8000/ws'). Server immediately sends full state, then ~5Hz snapshots; committed events are immediate. State/events share increasing seq, so event seq values need not be consecutive. Simulation t resets per scene and cannot order history.

Actual HTTP-produced rejection:

```json
{"type":"event","seq":303,"t":485.0,"event":"decision","data":{"alert_id":"A1","option_id":"opt-1","action":"reject","operator":"history-smoke"}}
```

Approve has the same shape with action approve. Recommendation data is {recommendation:{...}}; see fixtures. No decision_id/status/session_id/rejection reason/new enums were added. EventMsg.seq is the stable event identity within one database.

Recommended sequence (verify #7 before duplicating implementation):

1. Open WS, preserve the initial full state, buffer subsequent live messages.
2. Fetch /api/events?since_seq=last-processed-event-seq (0 after first refresh) and /api/log?limit=1000 concurrently. Snapshot seq is not proof history was read.
3. Merge REST/buffered events, deduplicate and sort by seq. Historical alert/zone events must not overwrite newer full state. Current activity follows state; advice/decision cards follow structured events.
4. Separate scenes by scenario_changed seq, not t; oldt500 must not follow newt0 by time sorting. Logs follow endpoint order and have no stable ID. Never derive decisions from text.
5. Missing decision in the window means unconfirmed, not pending approval. Readable details do not restore approval. Exactly500 supports only “may be incomplete,” without total/truncation proof.
6. Slow clients may close1013; repeat recovery. Same-database restarts do not roll back seq. Replaced/restored-old databases use #7 rollback clearing/warnings.

v1 has no decision idempotency key or terminal-state transition rules. Multiple valid submissions produce multiple seq-distinct decisions. Reject does not undo approve. Avoid automatic business-operation retries.

## Reproducible samples and B validation

backend/fixtures/history/ contains real B HTTP responses:
- state-before-restart.json: acoustic/KalmanT3,L3, approved-zone state.
- events-before-overflow.json: recommendation/reject/approve/other events, all v1 Pydantic-valid.
- recommendation.json: template fixture explicitly constructed/POSTed by B's tool, **not C Agent output**.
- decision-reject.json/decision-approve.json: fixture-specific IDs.
- det-6.json: Recovery debris without passive track. Its URL works only where the associated data exist; JSON does not include PNG.

Use a new directory without an existing database and free port:

```powershell
.venv/Scripts/python.exe -m pytest backend/tests -q
.venv/Scripts/python.exe -m backend.tools.history_smoke --directory artifacts/history-new-run --port 8004
```

The tool operates only its own service/new SQLite. In~60–70s it runs Security→reject→approve→forced restart→520 appended events→restart→Recovery PNG. Outputs report.json, actual request/event/state JSON, DB, logs. It is neither frontend regression nor three-person rehearsal.

## Minimum contract proposal — NOT IMPLEMENTED; owner approval required

/events exposes latest500 without pagination/truncation; state/details lack recommendation/decision history lists. Existing APIs cannot retrieve every stored record.

Proposed v1.1 adds only GET /api/history/events, preserving all v1 paths/fields/cache semantics:

```text
Request: after_seq=0 (>=0), limit=200 (1..500), optional through_seq.
First request fixes through_seq to current global seq; later pages reuse it.
Select after_seq < event.seq <= through_seq, ascending, up to limit.
Response: {items: EventMsg[], next_seq: number, through_seq: number, has_more: boolean}
When has_more=true, next_seq=last event seq; otherwise next_seq=through_seq.
```

Reuse existing EventMsg/actions; no decision status/session fields or total count required. Fixed high-water mark prevents endless paging into the live tail. A pages until has_more=false, deduplicates by existing seq/IDs, then merges buffered seq>through_seq. Preserve initial state as current truth; history restores cards only.

Durable same-database seq already solves ordinary restart rollback. No boot identifier is added. Database replacement/old backup still requires explicit client reset; automatic arbitrary-dataset recognition would need a separate reviewed identifier. **This endpoint does not exist. shared/contract.md, shared/types.ts, and models.py were not changed. B implements only after owner/team confirmation, then A integrates.**
