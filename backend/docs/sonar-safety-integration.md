# B Conservative Sonar/Disaster Fix Acceptance

Historical #10 validation. Later truth-dependency/original-bad-frame audit: [survey-p0-audit.md](survey-p0-audit.md). Green zones/time savings are demonstration metrics, not reliable real reopening conclusions or proof of an entirely truth-independent system.

Date2026-10-17. Scope follows owner-approved isolated local implementation and subsequent explicit Push instruction. Only B implementation/tests/tools/docs; no A/C source, frozen contract, main, or running-demo replacement. **B fixes can be reviewed independently; newer C/full taskbook acceptance is not implied.** Real-model Security L3 remains505 simulation seconds, beyond original500. New-combination browser recovery,20-minute endurance, and venue rehearsals remained pending.

## Exact baseline and changes

- Publication branch: main8613834e7430eee40d2f020e6277dbdec72ca1f5, B implementation6353421.
- Isolated candidate combined that main with C6389b705bec35b8fc44018d1c14d770f2a82b364, local merge3f237b87866592d43064c76a93083c0f67ac3bd0, B implementation8843422. Publication cherry-picked B only, not that C merge.
- Candidate frontend/shared matched main; agent/ml/tests matched specified C. Existing demo remained on old checkout/template/database without restart/replacement.
- No new REST/event types/fields/enums/pagination:21 operations,14 events; /api/events latest500.

Fixes:
1. Empty, wrong-class, and low-confidence disaster candidates stay unsurveyed; coverage threshold cannot clear them. Only valid debris recognition confirms blocked; manual restrictions take precedence. Areas without suspected obstacles may clear/BFS normally.
2. At most one retry per20 simulation seconds and3 total per candidate, preferring untried available safe buoys. Mammal protection remains. Existing security limit of5 actual pings per track is unchanged; empty images do not refund shots.
3. For C fan imaging below30m, choose a physically appropriate alternative buoy. Without one, remain uncertain.0m is not fabricated as30m. B's rectangular-stub zero-distance positive control remains valid.
4. Match boxes with the actual renderer projection: C fan and B linear stub differ. At164m, expected C y=437.636; old B approximation289.68. Internal _projection is not a public Detection/event field.
5. Warm up the model with a separate seed before FastAPI lifespan readiness. Start/reset reuse it, without advancing world clock/RNG or creating business detections/PNG records/events. Missing C/weights still stub.
6. Retry count/time/buoy history joins internal checkpoints and transactional rollback. No table/shared structure changes.

Main files: backend/app/decision/{disaster,pinger,__init__}.py, perception/classifier.py, {config,checkpoint,main}.py; test_model_safety.py/test_real_model.py and two reproducible tools.

## Actual tests/evidence

[Machine record](evidence/sonar-safety-20261017.json). Raw logs/JUnit/model calls/new databases stay in ignored artifacts/model-fixes/, not Git.

| Check | Result/scope |
| --- | --- |
| Before fix main+C |170 PASS,5 FAIL,2 SKIP,101.82s. Two old stub assumptions failed under real weights; three C-generator Windows cross-C/D relpath failures |
| After fix main+C |191 PASS,2 SKIP,93.07s; C-drive basetemp, C generator unchanged. Two missing separate COCO smoke weights; delivered sonar weights tested separately |
| B-only publication main+B |110 PASS,1 SKIP,66.87s; main lacked newer C weights, so real-model test explicitly skipped. Two pytest cache-permission warnings, no assertion effect |
| Original stub positive controls |Full explicit B stub preserves4 debris,6clear/4blocked/2unsurveyed, security timing, complete replay assertions; not weakened to all-unsurveyed |
| New B safety regression |16 PASS: empty/wrong/low-confidence, cooldown/limit, near field, forbidden ping, manual restrictions, projection, reuse/warmup, same-DB restart, rollback, actual-weight conservative reopening |
| Seeded real model |Full A/B offline three times each, DEBUG_TRUTH_TRACKS off; event/state/PNG semantic hashes identical per scenario |
| Cold real HTTP/WS+C |PASS, free8004/8006,new DB: actual template advice,reject/approve,real WS disconnect/API compensation,PNG,same-DB restart; not browser acceptance |
| Static |Ruff,diff check,pip check PASS; no extra A/C/frozen differences |

“Real model” means delivered YOLO weights infer on **synthetic sonar**, not sea/hardware acceptance. Cloud disabled; Ollama pointed at closed local port; actual advice model=template. No claim that this run trained LoRA.

| Measurement | Before | After |
| --- | --- | --- |
| Final B zones |8clear/2blocked/2unsurveyed; fuel/north incorrectly green |6clear/3blocked/3unsurveyed; none of4 hazard zones incorrectly green |
| Estimated saved hours |12, erroneously included unresolved areas |9 |
| Fuel berth |clear |unsurveyed; only in-range buoy is~0m from target, no physically valid alternative |
| Valid reopening |entrance/south main/container berth1 |Still available; no all-yellow shortcut |
| A first UUV/L3 |363.9s/505s |363.9s/505s unchanged;500s requirement FAIL |

Cold health5.959s; same-DB restart5.824s. Connected sample294 states,5.00168Hz,max interval393.04ms,P99315.10ms,max24264B. Process-tree peak RSS431.59MiB,mean single-core CPU46.13% (~2.88% across16 logical cores). This is~one minute, not20-minute endurance.

Offline tools bypass lifespan warmup: first B outer-tick peak2382.94ms,first classify2216.57ms; later B peaks~380–385ms. Moving warmup out of the live path does not remove computation cost.20ms remains best effort; average5Hz does not guarantee exact200ms frames.

## Merge/startup precautions

New parameters change checkpoint fingerprint. Old databases are neither automatically migrated nor cleared; incompatible startup explicitly fails rather than silently dropping history. Preserve old version/database and select a new independent path. Never delete/overwrite demo data or edit fingerprint to load old state.

```powershell
$env:HARBORGUARD_DB = Join-Path (Get-Location) 'backend/runtime/sonar-safety.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

B-only branch does not bring newer C weights; missing models remain explicit stub. To reproduce specified C, combine its exact commit in a separate test branch and install CPU runtime dependencies from requirements-runtime.txt. Do not enable unaccepted cloud routes automatically. Candidate used its own venv, not the old demo environment.

```powershell
.venv/Scripts/python.exe -m pytest backend/tests tests -q --basetemp=artifacts/pytest-model
.venv/Scripts/python.exe -m backend.tools.model_acceptance --out artifacts/model-results.json --repeat 3
.venv/Scripts/python.exe -m backend.tools.live_model_smoke --out artifacts/live-model-new
```

Last command requires free8004/8006 and a nonexistent output directory. It uses a new DB and cleans only its processes. Its temporary internal Agent destination8006 does not change production config;8000/8001/5173 remain intact.

## Failures, pending items, owner actions

- FAIL: new-C L3 at505s versus400–500s. No risk-threshold/ping-budget manipulation. B/C can later examine line of sight, first actual detections, and finite shot window.
- Fuel remains unconfirmed: cannot claim all4 actual debris recognized. Any new observation location/scenario data needs review; no shared coordinate/C renderer changes here.
- PENDING: newer browser refresh/reconnect race, projector, real bathymetry/tides/sonar, actual Wi-Fi disconnect,20-minute soak,three venue rehearsals,recording/Devpost. Old template passes do not accept this whole candidate.
- A: honor backend unsurveyed/blocked/clear;100% coverage must not override state. Fix identical-time log multiplicity,multi-operator seq,old REST/new live races; never parse approvals from logs. No pagination; degrade beyond500.
- C: original commit remains intact; accept new routes/models separately, provide near/far failure examples, label model truthfully. English summary<=60/explanation<=300 **characters**, not words.
- B: submit/review isolated fixes/evidence; do not mix C merge or old#6 wholesale into main. Re-record new replays in isolation for A review; do not overwrite old frontend files.

This supplements historical B0–B7 and does not transfer all37 old checkbox results to newer C.
