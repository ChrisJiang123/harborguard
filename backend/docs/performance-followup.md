# B Performance Improvement and Updated Endurance Verification

> Owner-confirmed policy update, 2026-10-17:20ms is now best effort, **not a hard Demo gate**. FAIL/exceedance counts below preserve the original strict-threshold measurements; they no longer block delivery and are not rewritten as passes. Correctness, durability, and5Hz take priority. This policy update did not change algorithms, timing, configuration, or production. See demo-stability-followup.md.

Date2026-10-17. Baseline pushed d223b15 (history branch); independent local branch codex/harborguard-backend-tick-performance. Only B implementation/tests/diagnostics/docs changed. Frozen contract, coordinates, parameters, frontend, agent, ml unchanged. No unapproved pagination, template replacement, remote Push, or Merge.

## Scope of conclusions

Snapshot/transaction overhead decreased. **Every tick<20ms still FAILS**; mean<20 is not an every-sample pass. Final92PASS(58.77s), RuffPASS. Complete A/B public messages, finalseq, and everyPNG byte matchd223b15. OldDB compatibility passed; production commitd9a2e89. New B20-minute real-service soak passed below. None accepts newer A/C browser integration, three-person rehearsal, real models/sea, or hardware offline.

## Diagnose before changing

Baseline used real SQLite, FULL sync, normal acoustic/Kalman, 10× offline full A1200s/B600s. The~37s benchmark is not20-minute endurance/network5Hz. Timed game.step, algorithm, state publication, checkpoint capture, SQLite commit, classifier including PNG. cProfile A t490–510 located repeated deepcopy/capture, generic encoding, and immediately discarded track snapshots. Profile overhead is not an unprofiled benchmark.

Changes:
1. Pre-transaction checkpoint still deep-copies for rollback. Post-transaction synchronous encoding borrows fields, avoiding a second complete copy. Encoder dispatches common numbers/list/dict first; storage format unchanged.
2. Every world change still atomically writes full checkpoint. State-only publication persists newseq in a separate transaction without rewriting unchanged checkpoint. SQL compares oldseq; broadcast only after success, no preallocation.
3. State truncates history to60 before copying; REST remains full. Mutating a snapshot cannot affect engine.
4. Tracker.update default return remains; engine's internal optional argument skips a snapshot immediately regenerated later. Cue counts calculated once pertrack.
5. First-seen history scan only for newtracks, avoiding eager setdefault evaluation eachsubstep. Risk, association, RNG, detections unchanged.

Files: app/checkpoint.py, storage.py, engine.py, perception/tracker.py, decision/risk.py.

## Final benchmark versus baseline

Local Windows, Python3.11.17, prepared dependencies; sequential runs, no concurrent verification service. Outer tick includes synchronous checkpoint/SQLite; state publication separate. P95=sorted item floor(0.95*n). No cross-machine guarantee.

| 10× metric | d223b15 | Improved | Interpretation |
| --- | ---: | ---: | --- |
| A outer mean |23.1807ms|19.6448ms|15.25% lower|
| A outer P95 |31.5246ms|27.0585ms|Improved, still over|
| A outer max |76.3968ms|61.0667ms|Strict20ms FAIL|
| A >20ms /1200 |865|446|Reduced, notzero|
| A algorithm mean/max |13.2952/52.6367ms|13.0000/47.4786ms|Includes detection, not one0.1s substep|
| A state mean |10.5526ms|1.6111ms|84.73% lower|
| A state P95 |17.1986ms|2.0130ms|Improved|
| A classifier+PNG max |32.1670ms|34.1279ms|Not disabled/optimized; peaks remain|
| B outer mean/max |2.6358/115.3724ms|2.2322/113.8246ms|First detection burst still over|
| B >20ms /600 |1|1|Strict FAIL|
| B state mean |1.9430ms|0.6778ms|Improved|

A10Hz outer real-time tick at10× advances1 simulation second through ten0.1s substeps. No dividing outer time by10 to claim compliance. PNG/algorithm timings nest; do not double-count. No individual-substep max/P95 output this round, so no strict substep pass.

Initial copy/state-only optimization: Amean21.0677ms, state1.5618ms; encoder dispatch then yielded final table. All88 original tests passed after each round; four additions yielded92. FULL sync, acoustic localization, active detection, and frequency retained. Async image generation changes scheduling/availability; not implemented without verified semantics.

Raw reviewable metrics/PNG hashes: evidence/ticks-before.json, ticks-after.json. Initial database size sampled before WAL checkpoint was unsuitable for disk comparison; removed from delivery metrics, raw artifacts retained.

```powershell
.venv/Scripts/python.exe -m backend.tools.benchmark_ticks --directory artifacts/ticks-new --speed 10
.venv/Scripts/python.exe -m pytest backend/tests -q
.venv/Scripts/python.exe -m ruff check backend/app backend/tools backend/tests
```

Same benchmark script works on old version, omitting commit_sequence subsection if absent. Always a new directory; never overwrites demo DB.

## Reproducibility and transactions

Complete public state/event/seq hashes at fixed publication cadence:

| Scenario | Common before/after SHA256 |
| --- | --- |
| A |fadb098fa451ae9cbf497d0660a5fa109a2267849d164db43e7587a7bc50d3a0|
| B |7192f62a4c60073e77373af0dd10d09504c5e1815e851f9d2ac077e2e6f2085b|

Every A14/B4PNG hash identical; finalseq712/334. No fewer events/pushes used to save time. Models were stub; no real-recognition accuracy evidence.

Four tests in tests/test_tick_optimizations.py:
- Trigger forbids checkpoint rewrite; 20state publications still succeed; restart restores state/seq.
- Failedseq write neither broadcasts nor advances cursor; after repair continues original sequence.
- Mismatched expectedseq refuses overwrite; does not hide a secondwriter/internal inconsistency.
-5000-point track produces60-point state but5000-point REST; mutating returned snapshot leaves the engine intact.

Original88approval/recommendation rollback, restart,>500window, RNG/Kalman continuation tests remained green. All public world changes use transactions. Debug tools directly modifying internals must callgame.save(); state publication is not world-change persistence.

OldDB compatibility used a copy of actuald223b15 artifacts:604archivedevents, 2decisions, 4currentPNGs preserved; seq904 → 906 and another restart readable. No fingerprint/schema-version change, deletion, or migration; original DB untouched.

## New20-minute real-service endurance

PASS for this B service, synthetic scenarios, and tested environment. Strict20ms remainsFAIL.

| Item | Measured |
| --- | --- |
| Wall duration |1200.08s|
| WS states/events |6001/1139|
| Mean state rate |5.000Hz|
| Max received state |26618B,<50000|
| DB scene starts/ends |13/13, 7A+6B|
| HTTP/WS check errors, serviceERROR/Traceback |0/0|
| Single-core CPU, 39~30s windows |mean15.751%, max24.0%|
| Total service/Python RSS |94.89–104.14MB; scene fluctuations, repeated return~96MB, no sustained accumulation|
| Stored events |1142, including3beforeconnection; publicwindow500|
| quick_check |ok|
| Restart after run |same checkpoint t, paused=true, seq7146continues, old det-1PNGhash unchanged|
| >20ms logs/max loggedtick |3424/120.8ms, FAIL|

CPU is30s-window utilization, not instantaneous peak. Memory evidence covers20min, not infinite leak-freedom. Fault injection differs from offline no-injection benchmark; counts are not directly comparable. Reviewable evidence: evidence/soak-history.json. DB~111.5MiB; events/PNGs archive continuously without automatic cleanup. Long-term retention needs separate approval; do not delete history to meet resource goals. DB not committed.

```powershell
$env:HARBORGUARD_DB = Join-Path (Get-Location) 'artifacts/B-soak-history-new/history.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.venv/Scripts/python.exe -m backend.tools.soak --seconds 1200 --port 8005 --report artifacts/B-soak-history-new/report.json
```

Use new directory/freeport. soak readsHARBORGUARD_DB; explicit isolation avoids writing operator data. Recorded run: artifacts/B-soak-history-20261017/, actualWS/REST/PNG, A/Bcycles, sixfaults/recoveries, 30sCPU/RSSsamples. B only, no Ctemplate/browser/realWi-Fi/onsiteoperators.

## Real-process restart and decisions after optimization

history_smoke --directory artifacts/history-live-tick-performance-20261017 --port8004 completed60.157s, PASS. Three prepared starts1.576/1.551/1.541s; real L1/L2/L3 wall3.720/15.069/48.339s, state~5.009Hz. Recommendation was explicit tool template fixture, not C.

After actualreject/approve, terminated/restarted process: recommendation, both decisions, details, restrictions equal, seqno rollback. Added520logs, restarted again: APIlatest500, internal587retained oldadvice/decisions. Fourempty-track RecoveryPNGsHTTP200/signaturevalid, stillstub. Smallreport: evidence/history-smoke-performance.json; fullDB/logs/requestJSONignored.

## Integration preparation and remaining work

Read-only merge-tree against fixed template fork/codex/harborguard-live-integration@5af2ae0 andlocald9a2e89 found no backend production text conflict but **backend/README.md conflict**. No actual merge/A/Coverwrite. B should retain bothlateststartup/templateinstructions manually in team integration; never replace the whole file with ours/theirs. Text preflight isnotnewestA/Cbrowseracceptance.

Remaining at this historical snapshot: strict20ms, history pagination approval, newA/Crefresh/reconnect/restartbrowserchecks, threepersonrehearsals, teammatefrom-zerostartup.20-minuteBpass doesnotmake B0–B7 or the project fully accepted.
