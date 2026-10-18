# HarborGuard Five-Minute Demo Runbook

Historical update: 2026-10-17, America/Los_Angeles; deadline 22:00 PDT. Tested main **a841bf9a70d8bf8237b9e03763852a34bed10368** included #4/#7/#13/#14/#15, not old #6. See [delivery check](final-delivery-20261017.md). These measurements belong to that SHA; freeze and check the actual recording version separately.

The actual A/B/C 2D browser workflow took **286.008 s (4m46s)**. 3D was unavailable in that browser; recovery R1–R4 still failed. At this historical snapshot B's options-metric broadcast patch was local e1 only (237 PASS/2 SKIP), not pushed/merged. Later merges do not retroactively change this evidence. Have the owner review and lock the final SHA. Do not risk correctness for 20 ms.

Show LIVE synthetic simulation → L3/options → template Agent → human approval → 2D (3D only if verified on the target computer) → explicitly labeled Replay. Delivered YOLO weights process synthetic images. Separate C synthetic LoRA evaluations do not prove a cloud/local/LoRA runtime accepted in this Windows run. B parameters/schedules are demo assumptions; A NOAA provenance does not validate B LIVE coordinates for deployment.

P0: old Recovery green zones/12-hour conclusions were unreliable. See [unresolved-observation/projection audit](../backend/docs/survey-p0-audit.md). The newer state-derived 9-hour estimate is also simulated, not real reopening permission. Browser workflow success does not establish business safety.

## Prepare dependencies and build in advance

The five-minute demonstration starts with services ready, excluding first-time network installation. Do not recreate a working venv. Python >=3.11; Node ^20.19 or >=22.12.

```powershell
# Repository root; choose one available interpreter setup on first install.
py -3.11 -m venv .venv
# Alternative: uv venv --seed --python 3.11 .venv
.venv/Scripts/python.exe -m pip install -r requirements-runtime.txt
.venv/Scripts/python.exe -m pip install -e '.[dev]'
.venv/Scripts/python.exe -m pip check
Push-Location frontend
npm.cmd ci --no-audit --no-fund
$env:VITE_API_BASE = 'http://127.0.0.1:8000/api'
$env:VITE_WS_URL = 'ws://127.0.0.1:8000/ws'
npm.cmd run build
Pop-Location
```

C runtime includes CPU inference and Agent SDKs; B lockfile alone cannot guarantee C startup. Do not download models or retrain at the venue. If weights/dependencies are unavailable, B explicitly labels stub; fallback is not real-model acceptance.

**Preserve old demo directories/databases. Use a separate checkout and new database.** Fingerprint mismatch rejects incompatible checkpoints. Do not delete databases, edit fingerprints, or migrate on stage. Same-version/same-database restart restores paused; explicitly Resume/Reset. Historical preview 5184 used a QA same-origin build, not standard 5173 deployment. Build the formal checkout for its intended URLs without overwriting an active dist.

## Three terminals

Check whether 8000/8001/5173 are occupied by an existing demo. Do not kill unknown processes or start conflicting services. B uses one process, one worker.

Terminal 1, repository root:

```powershell
New-Item -ItemType Directory -Force backend/runtime | Out-Null
$env:PYTHONPATH = (Get-Location).Path
$env:HARBORGUARD_DB = Join-Path (Get-Location) 'backend/runtime/demo-a841-final-new.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Wait for application startup complete; YOLO warmup precedes readiness. In this prepared environment all three services became ready in 10.295 s. First installation from zero remained PENDING; this is not a five-minute from-zero promise.

Terminal 2, repository root, verified template fallback:

```powershell
$env:BACKEND_BASE_URL = 'http://127.0.0.1:8000'
$env:BACKEND_WS_URL = 'ws://127.0.0.1:8000/ws'
$env:AGENT_HOST = '127.0.0.1'
$env:AGENT_PORT = '8001'
$env:AGENT_LANG = 'en'
$env:CLOUD_PROVIDER = 'disabled'
$env:OLLAMA_BASE_URL = 'http://127.0.0.1:9/v1'
$env:OLLAMA_MODEL = 'qwen3:1.7b'
$env:OLLAMA_FORMAT_OVERRIDES = ''
$env:OLLAMA_TIMEOUT_S = '0.2'
.venv/Scripts/python.exe -m agent.main
```

The closed local port causes unaccepted local routes to fall back quickly, without external keys. Do not automatically enable cloud/Ollama just before competition. Check actual recommendation model=template. AGENT_LANG=en selects the English runtime on newer main; historical a841 timing predates that later language configuration.

Terminal 3, frontend/:

```powershell
npm.cmd run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

Default REST is http://localhost:8000/api, WS ws://localhost:8000/ws. CORS allows localhost/127.0.0.1:5173. VITE_API_BASE/VITE_WS_URL are build-time settings; A must rebuild after changes.

## Pre-stage checks

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8001/health
```

B should return ok=true. C phase was c3-openrouter; model may be idle before processing a request. Do not demand template at startup: inspect the first actual recommendation. Open http://localhost:5173/, check LIVE/2D/logs/buoys, verify 3D readability on the recording computer, then return to 2D. If an old database restores paused, reset explicitly for a new demonstration.

## Five-minute sequence

| Wall time | Action | Expected behavior |
| --- | --- | --- |
| 0:00–0:20 | Explain LIVE synthetic business data; start Security A at 10× | Tracks, L1, actual state delivery |
| 0:20–1:15 | Wait for L2/active ping, L3/options_ready; pause after ~50–60 wall s | Source-labeled sonar PNG, risk, options, C template. Earlier L2 advice is not an approvable L3 plan |
| 1:15–1:45 | Select a current valid local option, enter operator, reject first or approve directly | Structured decision; reject does not restrict; approve produces restricted. Advice alone never executes |
| 1:45–2:00 | Show 3D only after target-computer verification; otherwise continue 2D | Do not debug GPU/install on stage |
| 2:00–3:10 | Start Recovery B at 10×; observe about one minute | 3 confirmed blocked areas; near-field fuel berth stays unsurveyed. Reference 6 clear/3 blocked/3 unsurveyed and simulated 9 h; B4/B7 fail at t=60 |
| 3:10–4:20 | Explain unresolved states/routes and open the actual-stream Replay below | Explicit REPLAY/read-only/source SHA. If End stops before final frame, press Play. Old stub is not this run's YOLO |
| 3:45–5:00 | Explain approval/acceptance limits; answer questions | Reserve retry time; no compilation/install/Merge on stage |

Measured real-weight L3 was t=505 s; the original 500 s requirement remains FAIL. At 10× this is ~50.5 wall s. The Recovery 6/3/3 and 9 h reference is calculated from state/assumptions; show actual returned values rather than forcing the reference. The 4m46s evidence is one-computer 2D with 3D fallback, not three-person rehearsal or complete recovery acceptance. Screenshots exist; no finished recording existed at that snapshot.

## Fallbacks

- B will not start: inspect fingerprint, single-writer lock, dependencies, ports. Preserve old databases; select a separate new path. Never delete history or stop someone else's service.
- Agent has no advice: check C health, B options_ready/current L3, C queue/logs. Do not infer approval from free text. Ask 502 usually means C unavailable; 504 means the 20 s proxy timeout.
- LIVE refresh/reconnect: at a841, two identical simultaneous live logs became one after refresh; GET log 503 lacked failure feedback. Multi-operator decision and old-REST race function reproductions remained FAIL. See [A handoff](../backend/docs/A-final-recovery-handoff.md). Reducing refreshes for a demo is not a fix. Only a 500-event window is queryable; do not promise complete early history.
- Slow/unavailable 3D: use 2D for the core workflow. Historical 3D build had ~1003 KB chunk warning; target projector FPS was not accepted by this run.
- Empty Detection.track_id: open PNG by Detection ID. No track does not imply no image. A near-field fuel observation without valid imaging remains unconfirmed; do not create a fabricated successful detection.
- Replay: explicitly label REPLAY; static playback cannot submit live approvals. Package image resources with it; this B check did not overwrite A's files.
- network_down is a simulated event, not a real Wi-Fi disconnection and not ESP32/LoRa offline validation.

Close only processes you started. Preserve old checkout/databases. See [interfaces](frontend-integration.md) and [version/evidence](final-integration-report.md).

## Historical isolated preview and emergency Replay

- Tested main preview: http://127.0.0.1:5184/ with B8020/C8021/new SQLite. Old 5173 was not switched.
- Recovery: http://127.0.0.1:5184/?replay=/final_replays/replay_maina841bf9_b.jsonl
- Security: http://127.0.0.1:5184/?replay=/final_replays/replay_maina841bf9_a.jsonl
- Portable bundle: artifacts/final-delivery/HarborGuard-maina841bf9-replays.zip, manifest and 8 PNGs. A must provide the same final_replays/ static directory for formal deployment; B did not alter frontend.
- Old replay_a/replay_b may serve as explicitly historical stub fallback. demo_a/demo_b/demo_full summaries exceeded 60 characters and were not contract-pass evidence before correction.

5184 was a local QA same-origin proxy. Do not deploy its fault-testing controls as production. Switch formal deployment only after owner permission and the old demo ends, with old databases backed up. Verify frontend build URLs match actual service ports.

## Recording and submission

At this snapshot no Push/Merge/formal cutover/Devpost submission was performed. The owner must record and play back the finished video, supply a public viewer URL, verify event rules/team/required fields, submit before 22:00 PDT, and retain the receipt. The accepted 2D scope is usable; do not miss the deadline seeking theoretical 100%, and do not hide limitations. See [historical draft](devpost-submission-draft.md) and [current story](devpost-story-en.md).
