# HarborGuard

**See underwater risk. Keep people in control.**

A port-security and disaster-recovery digital-twin prototype built for the InnovateLA Dual-Use Hackathon, Ports & Logistics lens. HarborGuard connects acoustic simulation, tracking, explainable alerts, sonar-image detection, response comparison, Agent recommendations and human approval.

The current demonstration uses **synthetic acoustic observations and simulated AIS**. It is not certified for real-world navigation, underwater surveillance or port reopening.

[Demo runbook](docs/demo-runbook.md) · [Acceptance evidence](docs/final-delivery-20261017.md) · [Project story](docs/devpost-story-en.md) · [Three twists](docs/twist-responses-en.md) · [Chinese documentation archive](docs/README.zh-CN.md)

## What it does

**Security:** localize and track simulated contacts, explain a three-level risk score, generate a sonar PNG and compare response options. The Agent recommends and explains; only an operator's approval applies security restrictions. Rejecting a suggestion does not automatically restrict a zone.

**Recovery:** survey zones while keeping coverage separate from unresolved observations. Misses, wrong classes, low confidence and unreliable near-field imagery remain unresolved rather than becoming clear when coverage increases. Candidate routes use confirmed-clear channels only. Time-saved displays are scenario assumptions, not measured operational savings or clearance decisions.

The frontend displays live state, detection images, recommendations, decisions and explicitly labeled, read-only JSONL replay. The 3D renderer is Three.js / React Three Fiber.

## Version and acceptance scope

| Evidence | Exact scope |
| --- | --- |
| Latest official main checked out for this README | `e9ae07fbf1e233d83c983803b3992b165eae163c`: includes B fix #16, report #17, A's 3D update #18, and C's subsequent #19 language/configuration fixes. These upstream changes were fetched into an isolated worktree; this documentation task did not merge them into main or rerun complete system acceptance on that SHA. |
| Last complete Windows acceptance run | Main `a841bf9a70d8bf8237b9e03763852a34bed10368`: **232 Python tests passed, 2 skipped**; frontend build, lint and A1-A6 passed; approximately **4.98 Hz** state delivery. |
| Actual browser demonstration | One real A/B/C **2D** flow in **4 minutes 46 seconds** on a841bf9. 3D was unavailable in that test browser. Screenshots were saved; this is not a recorded video. |
| B options-publication fix | Tested source `e1b3305`, report commit `390687a`: **237 passed, 2 skipped**, with actual browser/Agent metric consistency and Reject checks. Subsequently merged in #16; this does not automatically validate every later frontend change. |
| Recovery example | Three repeated real-weight runs on synthetic scenario B produced **6 clear / 3 blocked / 3 unsurveyed**. The fuel berth stayed unsurveyed at full coverage. Results are observed outputs, not hardcoded acceptance targets. |

The two skipped tests lacked a separate COCO smoke-test weight; the delivered sonar weight was actually exercised. The original 500-simulation-second security deadline was missed at 505 seconds. Four frontend history/recovery boundaries remain open in the last audited recovery code. The 20 ms target is best effort; correctness and 5 Hz delivery take priority.

See the [full report](docs/final-delivery-20261017.md), [A recovery handoff](backend/docs/A-final-recovery-handoff.md), [B publication fix](backend/docs/options-publication-fix.md), [A's subsequent 3D evidence](docs/3d-shoreline-realism/README.md) and [C's isolated retest](docs/C-acceptance-20261017-1743-retest-20261017-1911.md). Earlier reports retain their original timestamps and scope.

## Architecture and contracts

| Component | Location | Default service |
| --- | --- | --- |
| A: React/TypeScript dashboard, 2D/3D and replay | `frontend/` | `http://127.0.0.1:5173` |
| B: simulation, localization/Kalman tracking, risk, planning and SQLite persistence | `backend/`, `data/` | `http://127.0.0.1:8000` |
| C: sonar renderer, YOLO adapter and Agent | `ml/`, `agent/` | `http://127.0.0.1:8001` |

Public fields and event names are frozen by [shared/contract.md](shared/contract.md), with [TypeScript types](shared/types.ts), [sample state](shared/sample_state.json) and [sample events](shared/sample_events.json). C's interface reference is [docs/shared-contract-v1.md](docs/shared-contract-v1.md). Do not rename shared fields to work around integration issues.

Backend REST is under `/api`; WebSocket is `/ws`, not `/api/ws`. Interactive API documentation is at `http://127.0.0.1:8000/docs`. C exposes its own `/health` and `/ask`; the frontend uses B's contracted Agent proxy.

## Quick start

Use Python **3.11+** and Node **^20.19 or >=22.12**. Prepare dependencies and model files before the demonstration. Do not train or download models on stage. Inspect occupied ports before starting; never terminate an existing teammate's service just to reuse a port.

### Install once

From the repository root on macOS/Linux:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-runtime.txt
python -m pip install -e '.[dev]'
python -m pip check
cd frontend
npm ci --no-audit --no-fund
VITE_API_BASE=http://127.0.0.1:8000/api VITE_WS_URL=ws://127.0.0.1:8000/ws npm run build
cd ..
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
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

An existing prepared environment need not be rebuilt. First-from-zero installation time was not accepted as a five-minute setup. B-only lock files are not a replacement for C's full CPU/runtime dependencies.

### Start B: one worker and a separate database

In terminal 1, repository root, macOS/Linux:

```bash
source .venv/bin/activate
mkdir -p backend/runtime
export HARBORGUARD_DB="$PWD/backend/runtime/demo-submission-new.sqlite3"
export DEBUG_TRUTH_TRACKS=0
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

PowerShell equivalent:

```powershell
New-Item -ItemType Directory -Force backend/runtime | Out-Null
$env:HARBORGUARD_DB = Join-Path (Get-Location) 'backend/runtime/demo-submission-new.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Keep old databases. A checkpoint/configuration fingerprint mismatch must not be bypassed. Choose a genuinely new filename for an incompatible configuration rather than deleting history. Restarting the same version with the same compatible database restores the scenario in a paused state. Only one writer/worker is supported.

### Start C: deterministic offline fallback profile

In terminal 2, repository root, macOS/Linux:

```bash
source .venv/bin/activate
export BACKEND_BASE_URL=http://127.0.0.1:8000
export BACKEND_WS_URL=ws://127.0.0.1:8000/ws
export AGENT_HOST=127.0.0.1
export AGENT_PORT=8001
export AGENT_LANG=en
export CLOUD_PROVIDER=disabled
export OLLAMA_BASE_URL=http://127.0.0.1:9/v1
export OLLAMA_MODEL=qwen3:1.7b
export OLLAMA_FORMAT_OVERRIDES=''
export OLLAMA_TIMEOUT_S=0.2
python -m agent.main
```

For PowerShell, set the same variables with `$env:NAME = 'value'`, then run `.venv/Scripts/python.exe -m agent.main`. This profile deliberately uses an unavailable local-model endpoint to reach the deterministic template promptly; a local warmup failure is expected. No cloud credential, GPU or running Ollama instance is required for this profile. Verify an actual recommendation has `model=template`; startup health may initially report `idle`.

The Agent explicitly loads the root `.env` without overriding existing process variables. `.env.example` documents optional cloud/local settings, but it is not a credential and its defaults are not this offline profile. Never print or commit `.env`, tokens or keys. Use the [Mac runbook](docs/mac-demo-runbook.md) only when deliberately selecting the separately documented OpenRouter/Ollama deployment.

The latest C code honors the configured local model and defaults `AGENT_LANG` to `en`. Chinese output in English mode is rejected and may fall back to the English template within the existing budget. C's isolated retest reported 10 English recommendations, all template and none local; it did not establish English LoRA quality. Frozen Chinese test50/confirm60 scores do not measure English performance.

### Start A

In terminal 3:

```bash
cd frontend
npm run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

Use `npm.cmd` on PowerShell. Open `http://127.0.0.1:5173/`. Standard CORS permits localhost/127.0.0.1 on port 5173. `VITE_API_BASE` and `VITE_WS_URL` are build-time variables; rebuild intentionally when changing them. Do not silently reuse a QA build pointed at a different backend.

Health checks: B `http://127.0.0.1:8000/api/health`; C `http://127.0.0.1:8001/health`. Wait for B's model warmup and application startup before beginning.

## Five-minute demo

1. Explain that observations/AIS are synthetic or simulated. Start **Scenario A, 10x** in LIVE mode.
2. Wait for level-three alert and current response options; inspect the sonar PNG and its `yolo26n` or `stub` source label. A stub is a fallback, not real-model acceptance.
3. Inspect the actual Agent route. Show that a recommendation alone imposes no restriction. Select a current option and operator, then approve; only then should the affected zones become restricted. Reject does not automatically restrict them.
4. Use 3D only after testing the actual presentation computer; otherwise stay in 2D.
5. Start **Scenario B, 10x**, and inspect blocked/unsurveyed states, coverage and confirmed-clear route candidates. A green simulation zone is not permission to reopen.
6. Show an explicitly labeled **REPLAY**, with read-only controls and the correct version/model provenance.

Use the [detailed runbook](docs/demo-runbook.md). A real 2D rehearsal is evidence of a working flow, not proof of every business rule, historical recovery boundary or hardware behavior. This README does not claim a video has been recorded or submitted.

## Persistence, recovery and replay

Both approve and reject are persisted before a successful response and publish the existing structured `decision` event; write failure must not report success. Old history is not authority to approve an inactive alert. Scenario reset removes active restrictions and state while preserving stored history.

`GET /api/events` retains its frozen **500-event window**. It has no new pagination, total-count or truncation fields. Persisted detail queries do not make all early events discoverable through that window. Do not parse free-text logs into fabricated approval state. See [history handoff](backend/docs/history-handoff.md) and [frontend integration](docs/frontend-integration.md).

Historical `frontend/public/replay_a.jsonl` and `replay_b.jsonl` require their `replay_assets/` files and can be opened with `?replay=replay_a.jsonl` or `?replay=replay_b.jsonl`. They include historical stub results and must not be presented as current real-model LIVE evidence. The acceptance run also captured a separate, versioned real A/B/C transport replay. Existing `demo_a/demo_b/demo_full` summaries exceed the frozen length limit in the audited version; do not use them as evidence that every replay validates.

## Tests

From an activated development environment:

```bash
python -m pytest backend/tests tests agent/tests -q
python -m ruff check backend
python -m compileall -q backend agent ml
python -m pip check
python -m backend.tools.model_acceptance --scenario b --repeat 3 --out artifacts/real-b.json
cd frontend
npm run build
npm run lint
npm run check:a1
npm run check:a2
npm run check:a3
npm run check:a4
npm run check:a5
npm run check:a6
npm run check:recovery
npm run check:sonar
npm run check:english
```

PowerShell can call `.venv/Scripts/python.exe` and `npm.cmd` directly. Missing optional weights, API access, real Wi-Fi tests or target-machine checks must be reported as SKIP/PENDING rather than PASS. Existing test totals belong to their recorded SHA and environment.

## C model and Agent provenance

These are C-team records preserved from the previous README, not new measurements made during this documentation edit:

| Module | Recorded evidence and limits |
| --- | --- |
| C1 sonar renderer | 4,000 **synthetic** examples, seed 0; 3,400 training / 600 validation; deterministic fan PNG generation and B adapter integration. They are not physical sonar samples. |
| C2 YOLO | Lenovo-delivered weights were independently checked on the Mac: synthetic validation mAP50 **0.9771**, CPU **49.7 ms/image**, 600 samples. Weights/classes/manifests were verified. See [Mac acceptance](ml/yolo/ACCEPTANCE-MAC.md). |
| C3 Agent | C reports an isolated 20/20 OpenRouter cloud run. The Windows system acceptance above deliberately used **template**. A prior qwen3 run's 20/20 structure/ID result is not a 20/20 natural-language factual-accuracy result. |
| C4 LoRA | C reports completed Lenovo training/GGUF export and Mac serving using `harborguard-lora` with `format=json`: test50 factual validity **44/50**, confirm60 **39/60**. **Both sets are synthetic contexts.** See [source audit](acceptance_c4/data_provenance_20261017/README.md). |

C4's 501 input records split into 493 training records (450 synthetic + 43 captured from the simulated backend) and 8 internal validation records. "Captured backend contexts" do not mean real-sea measurements. Paired base/LoRA evaluations require the same base, quantization, template and parameters; compare datasets separately and retain denominators. The independently recorded qwen3 system baseline must not be mislabeled as a matched-base improvement.

Historical C0 automatic checks and GPU checks do not replace physical Wi-Fi loss, projector or cross-device video playback. The earlier macOS 26/Homebrew Python issue motivated `scripts/setup_env_runtime.sh` preferring uv; this is a machine-specific workaround, not a reason to rebuild a working environment. Keep runtime, YOLO training and LoRA training environments separate. No new training is needed for the demo.

For full module details use [Agent documentation](agent/README.md), [LoRA documentation](ml/lora/README.md), [historical README archive, now in English](docs/README.zh-CN.md) and the source audit. The Agent validates structure, IDs and selected deterministic facts, but cannot certify every free-text assertion; invalid output may retry or fall back. It never changes alert levels or calls the decision endpoint itself.

## Three twists and future work

- **Federal funding:** proposed **NSF SBIR Phase I** for real-echo validation and calibrated uncertainty, subject to suitability, applicant eligibility, Project Pitch and invitation. No grant, invitation or eligibility determination is claimed. See [NSF](https://www.nsf.gov/funding/opportunities/small-business-innovation-research-small-business-technology) and [eligibility](https://seedfund.nsf.gov/solicitation-eligibility/).
- **Global application:** a proposed Los Angeles -> Shanghai/Yangshan adaptation. Authorized local maps, depth/tidal references, acoustic calibration, language, data controls and approval procedures must be validated. No overseas partner, deployment or field result is claimed.
- **Poster:** the [A3 portrait PDF](docs/poster-live/HarborGuard-Poster-A3-3D.pdf) now uses an actual **3D target-following frame from an isolated A/B/C simulation**, showing level-three and level-two alerts, tracks, options and logs. [Capture provenance](docs/poster-live-capture.md) distinguishes synthetic inputs, the paused live connection and the older system acceptance. File preparation is separate from uploading the PDF to Drive, checking viewer access and pasting its real Drive link into Devpost.

Detailed [Twist responses](docs/twist-responses-en.md) and the [English project story](docs/devpost-story-en.md) are available for team review. A pitch deck, playable video, actual teammate confirmations and final submission receipt remain separate deliverables; this repository does not prove their completion.

Documentation, comments and ordinary runtime display text have been translated to
English. Frozen contracts, original evidence, Chinese-language model tests and
legacy translation keys remain intact for compatibility and reproducibility.
See the [translation scope and verification](docs/english-translation-scope.md)
and the [non-authoritative English contract guide](docs/contract-reading-guide-en.md).

## Responsible use and data attribution

HarborGuard could be misused for unauthorized surveillance or unsafe operational decisions based on incomplete data.
Human approval and explicit uncertainty limit these risks; the synthetic prototype is not certified for navigation or port reopening.

Public map/bathymetric layers retain their upstream attribution, including OpenStreetMap, NOAA and USGS where used by the frontend. Historical bathymetry, water-level references and visual alignment are not live acoustic sensing or field safety acceptance. Use the source/validation notes in `frontend/` before making claims about a layer. AI development assistance includes Codex and ChatGPT; disclose any other tools actually used by the team. No IBM Bob use is claimed by this README.

Do not commit `.env`, credentials, virtual environments, datasets, runtime failure logs, caches or large model outputs. The explicit delivered-weight exception is `ml/yolo/weights/best.pt`. Preserve third-party source, model and asset licensing requirements; a public repository does not by itself grant a new license to every component.
