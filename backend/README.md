# HarborGuard Backend and Algorithms

Hackathon backend for underwater security and post-disaster reopening at the Port of Los Angeles. One Python process provides deterministic simulation, passive acoustic observations, localization/tracking, risk alerts, sonar classification adapters, and response-option calculations. Restrictions change only after operator approval.

Taskbook B is the development basis. Public fields follow the [frozen v1 contract](../shared/contract.md), [TypeScript types](../shared/types.ts), [state sample](../shared/sample_state.json), and [event samples](../shared/sample_events.json).

The 2026-10-17 persistence update is documented in the [A recovery handoff](docs/history-handoff.md) and [B verification record](docs/history-verification.md); these take precedence over the initial MVP background for restart, rejection, and history limits. See [sonar safety integration](docs/sonar-safety-integration.md) for conservative survey handling and the newer C candidate. New algorithm parameters change the internal checkpoint fingerprint: preserve old demo databases and choose a separate `HARBORGUARD_DB`, for example `backend/runtime/sonar-safety.sqlite3`. Never delete an old database or force incompatible checkpoints to load. Branches without C use an explicit stub and must not claim real-model detection.

Later local optimization/endurance results are in [performance follow-up](docs/performance-followup.md). Strictly keeping every tick below 20 ms did not pass; a lower mean is not full acceptance. The owner subsequently made 20 ms a best-effort target, with correctness and 5 Hz delivery taking priority.

Mainline [REST/WS/decision handoff](../docs/frontend-integration.md), [five-minute runbook](../docs/demo-runbook.md), and [PR #3/#6 migration report](../docs/final-integration-report.md) were updated for B #10, C #4, and A #11. `python -m backend.tools.integration_bundle` exports OpenAPI and explicit static mocks into docs/integration and backend/fixtures/integration without touching runtime databases or frontend/. See the [file list](../docs/files.md) and [acceptance scope](../docs/acceptance.md). Reports apply to their stated SHA, not every later commit.

## Install and start

Python >=3.11. Run from the repository root.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
make backend
```

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
./dev.ps1 setup
./dev.ps1 backend
```

If script policy blocks startup, run `.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`. With uv installed, `uv venv --seed --python 3.11 .venv` is another environment setup option.

Health: `http://localhost:8000/api/health`; API explorer: `http://localhost:8000/docs`; WS: `ws://localhost:8000/ws`. A new database starts idle. Restarting the same database restores the scenario paused. Default database: backend/runtime/harborguard.sqlite3; override with HARBORGUARD_DB. Migrations are automatic, with no external database server. Use one worker; a second writer to the same file is rejected.

## Demo operations

```bash
curl -X POST http://localhost:8000/api/scenario/a/start -H "Content-Type: application/json" -d '{"speed":10}'
curl http://localhost:8000/api/state
curl -X POST http://localhost:8000/api/control -H "Content-Type: application/json" -d '{"action":"pause"}'
curl -X POST http://localhost:8000/api/control -H "Content-Type: application/json" -d '{"action":"resume"}'
curl -X POST http://localhost:8000/api/control -H "Content-Type: application/json" -d '{"action":"speed","value":4}'
```

PowerShell: `Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/scenario/a/start -ContentType application/json -Body '{"speed":10}'`.

1. Start A. Observe unknown tracks, level-3 alerts, automatic active pings, and annotated sonar images. Level 3 emits options_ready; GET /api/options/{alert_id} returns current options.
2. POST actual alert_id/option_id with action approve and operator demo to /api/decision. Only then do affected zones become restricted. Approve and reject persist first, then publish the existing decision event and operator log; write failures return 503. Reject does not alter zones. Approved restrictions remain until reset.
3. POST /api/inject with `{"type":"buoy_down","target":"B4"}`, `{"type":"network_down"}`, or `{"type":"noise_up"}`; restore with buoy_up/network_up/noise_down. Noise injection is an idempotent switch.
4. Start B via POST /api/scenario/b/start. Observe coverage, blocked/clear/unsurveyed, and reopen_plan. B4/B7 fail at simulation second 60.
5. POST /api/control with action reset. Current tracks, alerts, detections, recommendations, restrictions, and faults clear; persisted history remains. Same-database seq and alert/detection IDs increase across restart. Historical details are not active objects and cannot authorize old alerts.

DEBUG_TRUTH_TRACKS=1 is an explicitly labeled truth-track demonstration fallback. Normal runs/recordings use acoustic localization and tracking. Missing C modules/weights use a sonar stub, labeled Detection.model=stub; YOLO is not required merely to start B.

## Validation and replay

```bash
make test
make check
make samples
make record
# PowerShell: ./dev.ps1 test, check, samples, record
```

make record generates frontend/public/replay_a.jsonl and replay_b.jsonl without waiting in real time. Lines contain wall_ms and contract msg; wall_ms = simulation seconds / speed * 1000. Images are stored under frontend/public/replay_assets/{a,b}/ and referenced by static image_url, allowing offline playback. Only offline recording generates template recommendations, explicitly model=template; C submits online recommendations.

A dispatches full state/events by wall_ms without B. Deploy replay_assets with JSONL. Replay and live envelopes match. At this historical handoff, joint browser acceptance of newer #7 with B persistence remained pending; later reports provide newer evidence.

```bash
python -m backend.tools.soak --seconds 1200 --port 8000 --report artifacts/soak.json
```

This starts its own Uvicorn, cycles A/B, injects simulated faults, validates WS/PNGs, measures RSS, single-core-equivalent CPU, frequency, and packet size, then closes its own process. The port must be free. See [validation](../docs/validation.md).

## A/C integration

| Process | Owner | Startup/address |
| --- | --- | --- |
| Backend | B | make backend; 8000 |
| Frontend | A | frontend/README.md; development port 5173; A supplies production build |
| Agent | C | ASGI on 8001 implementing POST /ask |
| Ollama | C | Not required by this B persistence handoff; no new route enabled here |

Start B, Agent, then A. Historical main 782d04d already included A #7/#11 and C #4; C was no longer an unmerged skeleton. Use the runbook's explicit template fallback. New cloud routes, newer A browser behavior, and venue hardware need separate acceptance; old #6 conclusions do not automatically apply.

- A subscribes to /ws: complete state at 5 Hz and immediate events. CORS allows localhost/127.0.0.1:5173. Buffer live messages before /api/events?since_seq=N compensation, then deduplicate by seq. Only the latest 500 events are queryable, with no all-history pagination. Same-database restart keeps seq increasing and pauses simulation; replacement/rollback requires cursor reset and an uncertainty notice. Slow clients are disconnected to protect simulation.
- C sonar exposes ml/sonar/render.py:render_ping and ml/yolo/infer.py:SonarDetector, using grayscale images and pixel-corner boxes; weights are ml/yolo/weights/best.pt. Start at repository root for imports.
- Silent disaster debris may have empty Detection.track_id. Open images by Detection ID rather than requesting an empty track.
- Live image_url resolves against the backend root; replay images resolve against the frontend origin.
- C subscribes to alerts/options, obtains REST evidence, and POSTs complete Recommendation to /api/recommendations. Invalid structure/references return 422. B validates, persists, and broadcasts; it never approves for the operator.
- BACKEND_BASE_URL is the root; clients append /api; WS uses /ws. B proxy timeout is 20 s; C total budget is 18 s. This handoff changes neither.
- B/C dependency ranges are compatible. B lockfile alone omits C dependencies including ultralytics, matplotlib, anthropic, and openai. Full integration also installs requirements-runtime.txt and rechecks dependency/model loading. B includes Shapely/Pillow. If combining setups, create C's .venv first and then install B dependencies there.
- /api/agent/ask proxies to http://localhost:8001/ask; unreachable C returns 502 and a 20 s timeout returns 504. B continues running.
- Metrics read ml/yolo/metrics.json and ml/lora/metrics.json; missing/invalid metrics return null.

## Implementation scope and assumptions

backend/app/config.py holds simulation, acoustic, risk, hysteresis, ping, and optimization parameters. The 10 Hz wall-clock loop advances fixed 0.1 s substeps according to speed. Randomness derives from the scenario Generator and derived seeds. Measurements contain no truth ID. Tracking uses forward bearing intersections, clustering, a 3D constant-velocity Kalman filter, and Mahalanobis nearest-neighbor association. AIS is only for cooperative identification. Options rank predicted-path buffers, berth availability, vessel-hour delay, and residual risk. Disaster coverage accumulates scan-circle/zone intersections; BFS uses clear channels.

Business geometry/schedules are demonstration assumptions; see [data notes](../data/README.md). A's NOAA multibeam and proposed buoy locations do not automatically move B LIVE coordinates. YOLO evidence concerns synthetic sonar; real sea conditions, newer browsers, and venue demonstrations need separate verification.

## Git handoff history

The historical codex/harborguard-handoff-refresh branch was based on origin/main@782d04d and retained B #10, C #4, A #7/#11. Old #3/#6 were pushed but had README conflicts with newer main. Missing B tools/materials were migrated and stale descriptions corrected, without reintegrating old C or overwriting A/C.

Review fixtures/regression, then the new Draft, then browser recovery/replay and venue rehearsal on the chosen main SHA. Pagination requires contract approval. Historical Push permission did not authorize merging main, force-pushing, or closing teammates' PRs.
