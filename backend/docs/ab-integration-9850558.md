# A/B/C Actual Browser Integration Record (2026-10-17)

Historical record. Owner later made20ms best effort, not a Demo gate; original measurements/conclusions remain. PR#7 head17d440b added terrain/aerial imagery only, with the same three recovery files as tested. It was not counted as a fix/new pass. See demo-stability-followup.md.

Security → template advice → human approve/reject and Recovery → reopening plan → debris PNG/JSONL ran. **Full integration was not accepted:**actual A recovery race remained, and frozen v1 cannot query advice/decisions beyond500. No frontend/agent/ml/shared edits, Push, PR update, or Merge main. This local integration record does not replace B0–B7, real recognition, or three-person venue rehearsal.

## Fixed versions and isolation

| Module | Tested SHA |
| --- | --- |
| B |04de0fe7abb9eb52ba7ae806beb30131d4b04a8e|
| A PR#7 |98505588c643d55174acf399bb597ca8c9260ec0|
| C verified template |78d39574266b01a582b0626c17021181749271c8|
| Local combination |1269f3eea1c47a19a6c94ab56699322a62282f98|

Primary checkout remained pure B codex/harborguard-backend-tick-performance. Separate C:/Users/Administrator/.codex/worktrees/harborguard-ab-integration/marine, branch codex/harborguard-ab-integration-9850558, merged fixed C/A without conflicts. Directory diffs proved frontend=A, backend/shared=B, agent/ml/tests=C. New report written only in B primary checkout.

Actual B8003, C8001, production-built A5173; transparent QA HTTP/WS relay8000. Browser used8000, C connected directly8003. Relay only controlled faults/delay, never generated business data or altered messages. Separate SQLite preserved existing demo databases.

## Executed checks

| Check | Result | Evidence/scope |
| --- | --- | --- |
| A dependencies/build/lint/A1–A6 |PASS|npm ci/build/lint/six check: a*; 3D chunk988.95KB warning|
| B+C suite |PASS with skips|120 passed, 2 skipped, 66.77s; skips require YOLO weights|
| Windows default cross-drive temp |FAIL environment|Initial117 pass / 3 fail / 2 skip; C ml/sonar/gen_dataset.py:59 relpath from D: temporary files to the C: repository failed. New same-drive --basetemp passed, without C edits|
| Real Security escalation |PASS|DEBUG_TRUTH_TRACKS=0, 10×, L3t483.1 (~49wall s); two actual C recommendations, processed2/submitted2/errors0|
| Actual browser WS disconnect/compensation |PASS within window|Only browser WS closed, B/C continued. Reconnect showedL3, 4options, one matching template card, QA_WS_OFFLINE_MARKER_01; not network_down|
| Approve/refresh |PASS within window|A1/opt-1 approve seq1035, 5restricted zones; refresh restored advice/operator/approved|
| Same-DB restart after approve |PASS within window|seq1174 → 1255, same t, paused=true, state equal exceptseq, event list equal, UI retained confirmation|
| Decision write failure |PASS|Disposable DB trigger; A11 reject503, no new decision/no restricted, UI failure and retry, no false success; trigger removed|
| Reject/refresh/restart |PASS within window|Retry200; A11/opt-1 rejectseq1887, no restricted; refresh/second restart retained rejected|
| >500 boundary |Public recovery limited|520logs → GETevents500, seq2018..2542, sorted/unique, olddecision0. DB647events and bothapprove/reject. Refresh did not fabricate old approval from logs|
| REST/live concurrency |FAIL, A|OptionsGET3s delay; new log after logGET visible before recovery, then vanished; false rollback. DB retained it|
| Actual Recovery |PASS, demo|Pausedt107, B4/B7down, 8/10online; routechannel_entrance/channel_main_s, berth_container_1; 4blocked/2unsurveyed; 9h assumes demo survey duration|
| Empty-track debris entry |PASS, stub|det-11..14 emptytrack; all4UIentries opened200, decoded640×640, labeled synthetic, no empty-track request|
| 2D/3D, target/camera |SmokePASS|SecurityReplay/Recovery toggled, T60selected in3D, follow/underwater controls, 2D retained target, actual render screenshots. Hidden canvas fallbackAX text had isVisible=false; not WebGL failure|
| Two B JSONL replays |SmokePASS|Aseek20:00, Bseek10:00, business POST disabled; 46.16srelay sample0backendPOST; image/replay_assets/b/det-1.png|
| Agent ask proxy |PASS, templatefacts|/api/agent/ask model=template. Fixed C did not handle Recoveryreopen_plan; disaster advice card stayedidle, not a claimed capability|
| WS short sample |PASS, limited|PausedRecovery10.11s, 52states includinginitial, 5.07Hz, mean197.12/max223.73ms, max1845B, seqincreasing; notrunning10×/soak|

Actual browser work was one local computer, without A/C operators; not three-person onsite acceptance. UI FPS readout was not a formal benchmark. Viewport~893×759; do not reuse A's prior1920×1080 FPS.

### Six simulated-fault feedback checks

| Operation | Actual visible feedback | Observed upper bound from operation start |
| --- | --- | --- |
| buoy_down B1 |Offline, 7/10, recovery button|383ms|
| buoy_up B1 |8/10, online|382ms|
| network_down |External network offline, stillLIVE, local shoreline fallback|383ms|
| network_up |External network toggle reset|378ms|
| noise_down |Fault log corresponding to structured log event|214ms|
| noise_up |Fault log corresponding to structured log event|192ms|

First4 timed real UI actions. Noise had no UI injection button; existing REST then actual browser logs were used, without adding controls. Timing includes command/observation overhead, all<3s. Noise results prove log feedback only, not numerical noiseUI or reevaluated localization. No actual Wi-Fi disconnect/LoRa/ESP32 validation.

## A fix recommendations

P1:fix async history overwriting live messages and false restart, within current contract. Locations: store/useHarbor.ts:108 recoverLiveState, data/ws.ts:39, data/liveRecovery.ts:6.

Reproduction: pause real A atL3, delay /api/options/{alert_id}3s, refresh, then POST unique log afterlogGET but before options GET returns. Log appears then disappears with false backend-sequence-rollback warning. logGET completedwall1792233734.488, marker1792233734.639, firstoptionsGET1792233737.483. QA_RESTORE_RACE_MARKER_02 remained archived, proving B did not lose it.

Cause: first connection previousSnapshotSeq=undefined; ??state.latest?.seq substitutes a seq that advanced during REST and compares it with initial snapshot. False rollback discards state.events. Final logs assignment independently replaces fresh logs with olderREST. Fixing onlyseq does not fixlog overwrite.

Explicitly distinguish no-old-snapshot from captured old seq. Only preconnection seq determines rollback. Merge newerstate/events received during wait byseq/stableIDs; logsnapshot cannot overwrite fresh structured logs. No log-derived approve/reject or new shared fields.

A regressions:(1)first connect+delay details+newstate, no false restart;(2)RESTlogdone/detailswaiting/newlog, preserve exactlyonce after recovery. Keep genuine rollback/reset/duplicate-compensation tests. Ordinary green tests miss this window.

P2:narrow-screen3D overlays crowded893×759. Collapse detailed DEM metadata, constrain overlayheight/scroll; retest1920×1080 projector, retaining provenance/demo-waterlevel labels. Chunk size/THREE.Clock deprecation can follow later.

No new pagination/log parsing for A yet. Consume existingapprove/rejectdecision; windowrecoveryworks. Beyond500 show incomplete/unconfirmed. Proposed pagination stillneeds owner approval and B implementation.

## B/C/owner actions

- B: persistence, structured reject, restart, rollback needed no new production fix on these browser paths. Historical strict20ms failure remains in performance report; short WS sample cannot overturn it.
- Owner: approve history-contract proposal only if arbitrary oldadvice/decisionrecovery is required. DBarchives exist, but events is explicitlylatest500, no pagination/total/truncation ordecision/recommendation detail API. None added here.
- C: fixed template handlesSecurityoptions_readyonly. Recovery advice needs separate C implementation/acceptance using existing recommendation kind, not silently replacing the baseline. Fix/document cross-drive generatorrestriction; realweights/output remained unverified.
- A: supply a new SHA after the race fix, retest the actual browser. Projector, real network loss, onsite rehearsal pending.

## Standard three-service startup/demo

Run in an integrated checkout containing the exact A/B/C versions; pure B does not include A/C. Python>=3.11, Node/npm; fixed template needs no key/Ollama/GPU.

```powershell
# Terminal1,root;oneworker,fixedDB,preserve onrestart.
$env:DEBUG_TRUTH_TRACKS = '0'
$env:HARBORGUARD_DB = Join-Path $PWD 'backend/runtime/demo.sqlite3'
.venv/Scripts/python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

```powershell
# Terminal2,root,fixed C template.
$env:BACKEND_BASE_URL = 'http://127.0.0.1:8000'
$env:BACKEND_WS_URL = 'ws://127.0.0.1:8000/ws'
$env:AGENT_HOST = '127.0.0.1'
$env:AGENT_PORT = '8001'
.venv/Scripts/python.exe -m agent.main
```

```powershell
# Terminal3;rebuild afterfrontendchanges.
Set-Location frontend
npm.cmd run preview -- --host 127.0.0.1 --port 5173 --strictPort
```

First install/build separately: root ./dev.ps1 setup, then frontend npm.cmd ci/build. This run reused preparedPython, withoutfrom-zero/five-minutestartuptiming. Ports8000/8001/5173mustbefree; CORSallowslocalhost/127.0.0.1:5173. QArelay is not a standard demo dependency.

Suggested<=5min:
1.0:00–1:15 open127.0.0.1:5173, LIVE, A10×, L1 → L2 → L3, template~49s.
2.1:15–2:00 pause, explain evidence/options, approve/checkrestrictions, refreshauthority. Ifoldfalse-restart appears before the A fix, disclosebug; notDBloss.
3.2:00–2:40 3D/target/above-underwater/follow; regional DEM is not a precise port survey, waternotlivetide.
4.2:40–3:50 B10×, 4debrisentry/PNGs/syntheticlabels/survey-reopening/faults.Fixed C does not generate Recovery advice.
5.3:50–4:40 ?replay=replay_b.jsonl orreplay_a.jsonl, seek/read-only/localimages. Localshoreline/replayfallback is not actual Wi-Fi offline acceptance.
6.4:40–5:00 human approval, synthetic recognition, 500window, and pending items.

## Evidence/integration decision

Summary backend/docs/evidence/ab-integration-9850558.json. RawHTTP/serviceslogs, independentDB, screenshots, faultcontrols remain ignored artifacts/ab-integration-9850558/, not deployment dependencies/GitDBs. Failuretriggerremoved, quick_check=ok, health200, finalsimulationpaused, network/noisenormal.

B isreviewable/integrable; conflict-free combination isnotwhole-project acceptance. Retest after the A fix before final merge. No automatic Merge, C-template replacement, or A remote modification. OnlyBreport/evidenceadded.
