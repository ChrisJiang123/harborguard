# Stable Demo Baseline and Retest Agreement After A Fixes

Updated2026-10-17 under the project owner's latest thread instructions. Historical version-specific record.

## Acceptance policy

20 ms is a best-effort optimization target, no longer a mandatory acceptance gate. Preserve original timings, exceedance counts, and20-minute data; never change statistics to turn failures into passes. Priorities: simulation correctness, durable approval consistency, 5Hz delivery, stable venue demo. This change added B documentation/diagnostics only, without production code, shared contract, DB schema, RNG, detection-frequency, or C-template changes.

Stable B production04de0fe7abb9eb52ba7ae806beb30131d4b04a8e; verified C template78d39574266b01a582b0626c17021181749271c8; prior browser-report commit6b5e3eb. Original test checkout/services/independent database were retained, not replaced by an untested combination.

## A update checks

PR#7 dc69ad28ac37e8d0592d9271f9d61e28c79ff27c fixed the old race. Actual browser verification preserved live logs, real-template advice, and ordinary decisions during delayed history, without false seq rollback. Two A identity edges still failed: same-time legitimate identical logs shrink after refresh; a second operator's same-time decision is ignored live until refresh. See pr7-recovery-dc69ad2.md/evidence. **That SHA is tested; do not repeat the same run. Wait for R1/R2 fixes.** Keep stable B/C; no automatic Push/PR update/Merge.

Final read-only check found b549515337e0a50889d331ae397e4f381e4694ca, UI English translation only, unchanged deduplication. No full retest. Stay quiet on unrelated updates.

Earlier GitHub metadata plus git fetch had confirmed head17d440bf03f4db7dbf41d16c511fa8bd7325a7dd, open/unmerged. Relative to tested9850558 it added land DEM, aerial imagery, and3D files but did not modify store/useHarbor.ts, data/liveRecovery.ts, data/ws.ts. An old PR description/build pass was not evidence of a recovery fix. dc69ad2 scope is in the later report.

A's original requirements: when there is no previous snapshot on first connection, do not compare the initial snapshot against a live seq that advanced during REST and falsely report restart. Historical logs must not overwrite structured logs received during that wait. Original reproduction remains in ab-integration-9850558.md§3; later report describes fixes/remaining edges. B does not modify frontend or invent approvals from log prose.

Thread heartbeat harborguard-pr7 checks every15minutes. Unchanged recovery/unrelated updates stay quiet, without repeating tests. New fixes use an independent checkout. Automation performs no Push, PR mutation, or Merge.

## Peak diagnosis: actual scope

Isolated B04de0fe + fixed C78d3957 actual renderer, DEBUG_TRUTH_TRACKS=0, independent SQLite, FULL sync. Offline10× advances A to510s, B to120s. Temporary in-process timing wrappers changed neither on-disk production source nor running services. Not a new soak/network5Hz test.

Wrappers add overhead, and startup cache state differs; numbers locate costs rather than compare optimization benefit. Items nest—do not add renderer, PNG, classifier, decision as independent costs. A:510 outer ticks, 5100 Kalman/track/decision calls, 5 classifications. B:120 ticks, 1200 calls, 4 classifications.0.1s is a simulation substep; at10× each10Hz outer tick advances1s through10substeps. Outer time was not divided by10 to claim substep compliance; full end-to-end timing of every substep was not measured.

| Component | A mean/max ms | B mean/max ms |
| --- | ---: | ---: |
| Outer tick including persistence |18.5822/66.2455|3.3026/119.6544|
| Kalman predict |0.1158/0.4153|0.0014/0.0077|
| Association/update |0.3930/0.8098|0.0054/0.0086|
| Track materialization |0.3999/13.3393|0.0011/0.0100|
| Localization |1.9432/4.4686|0.0062/0.0105|
| C renderer per image |21.9500/30.4034|21.0187/21.2880|
| PNG save per image |7.5115/15.7172|5.1835/5.3318|
| Classifier including renderer/PNG |30.4884/46.8680|27.5733/27.9948|
| Checkpoint capture, copy/borrow combined |0.8595/16.8410|0.2358/0.7767|
| Checkpoint JSON+SQLite commit |2.8080/6.4229|0.9574/4.4540|
| State publication including seq transaction |1.5871/4.5780|0.7346/0.9721|

A's max tick ended t151 and included first classification t150.7:classifier46.8680ms, renderer30.4034, PNG15.7172, pure computation60.3903, full tick66.2455. Other peaks also clustered near active pings.

B's max tick ended t1; t0.1 generated4debris images in one substep. Four classifications totaled~110.29ms, decision113.5851ms, full outer119.6544. Ordinary subsequent B ticks were much smaller.

Control/wrapped runs had identical public-message SHA256, final seq, and A5/B4PNG byte hashes. This shows unchanged output in those windows, not full-scenario acceptance of a new algorithm. First diagnostic attached timers to tracker instances and failed checkpoint allowlist; that isolated failed sample was retained but excluded. Class-level wrapping completed; production stayed healthy.

Summary: evidence/peak-analysis-20261017.json. Full artifacts/peak-analysis-20261017-v2/; failed attempt artifacts/peak-analysis-20261017/. No demo DB overwrite.

## Optimization benefit/risk assessment

| Candidate | Evidence/potential benefit | Risk/decision |
| --- | --- | --- |
| Startup image-encoder/resource warmup |First A PNG15.7ms, later~5.4–5.6; possible first-image initialization benefit |No isolated cold/warm causality or proven saved milliseconds. Must check startup delay/pixel equality. Do not change stable B yet |
| Cache fixed sonar geometry grids |Renderer~21ms/image; inspect target/RNG-independent grid work |C-owned renderer; complete size/FOV/range keys, pixel equality, memory validation required. B does not edit it |
| Reduce repeated checkpoint serialization/copies |JSON/commit~2.8ms mean plus occasional capture peak |Current optimization preserves rollback/FULL atomicity. Borrowed mutable state, async durability, or stale caches threaten restart/failure consistency; insufficient benefit before contest |
| Move PNG encoding out of real-time path |Theoretically~5ms/image, more first time; no end-to-end proof |PNG must exist when detection publishes; atomic decision/restart evidence must remain. Early broadcast risks404/incomplete evidence; not a ready low-risk patch |
| Async whole detection/stagger B's4classifications |May reduce~110ms burst |Changes timing, risk, event order, RNG/replay, and pending-task durability. Proposal only; design and owner approval before implementation |
| Lower detection frequency/skip substeps/disable real detection/weaken durability |Rejected |Trades correctness/consistency/features for timing, against instructions |

No evidence Kalman/Mahalanobis association causes the principal peaks; do not change those algorithms. Keep stable backend; 20ms does not block Demo. Prior20-minute B evidence remains5.000Hz, max26618B, no HTTP/WS errors. Short offline diagnosis is not a rerun of endurance or live-rate acceptance.

Post-diagnostic real WS health sample:8.18s, 41states excluding initial snapshot, 5.001Hz, max interval218.16ms, max1810B, strictly increasing seq; B/C/frontend health200. Paused Recovery only, not10×load/long-term guarantee. Same summaryJSON.

## Retest after A fixes

Create independent candidate with exact new A and fixed B/C. Inspect changes, run necessary build/regression/actual browser tests. Preserve stable checkout; do not mix new C routes.

1. First connect, ordinary refresh, 3s delayed options: live state/events continue; no false rollback or old snapshot overwrite.
2. Add a unique log after history GET completes but before details return. Preserve it after recovery, merge byseq without duplicates; also preserve legitimate repeated text. No log-derived approval.
3. Real C-template recommendation during recovery retains recommendation/alert/option IDs, without loss/cross-scene contamination.
4. Approve/reject: HTTP, structured decision, disk, UI, and zone restrictions agree. Injected write failure503 must not show success; after repair retry is available.
5. Actually disconnect browser WS while B/C run; network_down is not this test. Reconnect compensation/dedup/order/decisions agree.
6. Same-DB restart continues seq, pauses state, restores advice/decisions. Only genuine replaced-database rollback is a new session.
7. >500events honestly shows limit; never fabricates complete history or marks unknown old decisions pending. Earlier pagination requires owner contract approval.
8. Empty-track Recovery PNG, 2D/3D, read-only Replay as regressions. Distinguish actual browser/API/automatic evidence; untested=PENDING.

Report a final integration candidate only after new fixes/key checks. No automatic Merge main. This update changed B reports/evidence only and performed no remote mutation.
