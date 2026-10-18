# HarborGuard Final Integration and Delivery Check

Historical acceptance date: 2026-10-17, Los Angeles; deadline 22:00 PDT. This run locked **main a841bf9a70d8bf8237b9e03763852a34bed10368**; final Fetch still matched.

**Conclusion at that SHA: the 2D core could be recorded, full acceptance had not passed, and Devpost had not been submitted.** Actual A/B/C browser flow took **286.008 seconds (4m46s)**. 3D was unavailable in this browser; four A recovery defects remained. A separate B options-broadcast defect was fixed locally but was not then in main. Later merges do not retroactively alter these measured results.

## Versions/environment

| Module | Official merged version | This run's finding |
| --- | --- | --- |
| A | #7 merge f93af2c; later #11/#15 merge a841bf9 | Build/lint/A1–A6 pass, 2D usable; R1–R4 FAIL, current browser 3D unavailable |
| B | #13 merge **5a68f1204ec064db474e8b6ac9c35f7f041180e5** | Confirmed merged; fresh full suite/real Recovery pass; metric-change broadcast defect below |
| C | #4 merge 782d04d; C4#14 merge 99d7091 | Actual WS subscription/REST submission tested, actual model **template**; cloud/local/LoRA runtime SKIP |

GitHub reconfirmed #4/#7/#13/#14/#15 merged. Obsolete/conflicting #6 was not used. Actions query for the exact main returned no runs; that is not CI PASS. Separate C synthetic LoRA evidence exists; no training, download, switch, or runtime acceptance of it in this run.

Independent checkout: C:/Users/Administrator/.codex/worktrees/harborguard-final-main-latest/marine; branch codex/harborguard-final-main-latest. New SQLite artifacts/final-delivery/final-main.sqlite 3. B8020/C8021/QA preview 5184. DEBUG_TRUTH_TRACKS=0, one worker, fingerprint checks intact. Original 5173/8000/8001/8003 and old databases were not switched, deleted, or stopped.

Python 3.11.17, torch 2.14.1+cpu, ultralytics 8.4.181, Pydantic 2.14.1; Node 24.19/npm 11.17. Reused prepared CPU dependencies; new-worktree npm ci~7 s; three services ready 10.295 s after preparation. First-from-zero install PENDING. Sonar weight SHA 256:2cad3146fa4b98516efa0057367c3c5d53220dc2a3246058f5608094a6568839.

## Tests actually run on this main

| Check | Result |
| --- | --- |
| pytest backend/tests tests agent/tests -q | **232 PASS, 0 FAIL, 2 SKIP, 130.92 s**. Not old 211 results. Skips lack separate COCO smoke weights; delivered sonar weights actually ran |
| Ruff/compileall/pip check | PASS; Ruff backend, compileall backend/agent/ml, consistent dependencies |
| Frontend | Build 10.035 s; lint, A1–A6, recovery, sonar, English PASS.1003.10 kB lazy3D chunk warning, nonblocking |
| Offline real model | Full A1200s×3, B600s×3; per-scenario event/state/PNG semantic hashes matched; no silent stub |
| REST/WS+C/persistence | PASS at API layer: actual approve/reject, disconnect compensation, same DB restart; model=template |
| Real-time metrics | **4.97718 Hz**, 295states, max interval 490.945 ms, P99346.417 ms, max24264B, RSS peak 431.77 MiB, CPU single-core equivalent 48.77% (~3.05% of16logicalcores) |
| Browser faults | Buoy down/up 314/316 ms; simulated network down/up 298/322 ms; noise up/down actual REST → WS → visible log. Simulation only, not Wi-Fi/ESP 32/LoRa; noise 3 s bound PENDING |
|20-minute endurance | **PENDING at a841**. Earlier5a68 ran 1200.61 s, 5961 frames, 4.965 Hz, no errors; cannot transfer to newer SHA |
|20 ms | Best effort, not Demo blocker; no risky refactor/disabled detection/manipulated stats |
|Replay | Old replay_a/b contract, 14+4PNG/HTTP pass, butstub. demo_a/b/full summary>60characters FAIL. New a841 actual A/B streams+8PNG passed contract/resource checks |

## Security/Recovery

Actual latest browser showed real tracks/risk, active ping, L3, yolo26n PNG, C template, andApprove → restricted. API Reject did not restrict; local candidate also tested actual browser Reject. Reset generated new IDs/restored defaults; API regression passed. **Original 500 simulation-second L3 gate FAIL:505 s measured.** Risk parameters were not tuned merely to meet timing. Later options-metric broadcast inconsistency prevents claiming Security fully passed.

Actual Recovery: **6clear/3blocked/3unsurveyed**. North anchorage blocked; fuel 100%coverage still unsurveyed; 0m never clamped to 30m. BFS only channel_entrance/channel_main_s; available berth berth_container_1.9h derives from actual states and 1.5h/zone assumption, not hardcoded reference. Maximum 3 actual attempts/20 s cooldown, wrong/missed/low confidence, near field, exhaustion, coverage crossing, multiple-box regression passed; real B repeated 3 times.

**This accepts a conservative policy/demo under synthetic simulation.** Anonymous contacts still derive from simulation geometry; AIS simulated; real model errors remain. Not real marine sensing, whole-system truth independence, or reopening authorization. Physical bathymetry/tide/receiver observations/crowded targets need separate acceptance.

## Unresolved defects and exact evidence scope

| Item | Finding | Owner |
| --- | --- | --- |
|R1 simultaneous identical logs |Latest-main browser 2 live → 1refresh; B stored both. Preserve distinct seq, not a content Set |A|
|R2 multi-operator decision |Latest source function FAIL; e1sameA at t632 rejectseq 1158/1201; Bdurable, UI retained Operator A |A|
|R3 failed logGET |Latest browser GET log 503 with WS healthy gave no partial/failure; function FAIL |A|
|R4 oldREST/newWS |Exact main function FAIL; prior5a68 actual 6 s delay produced table 15%/Agent 20%; same relevant A hash through a841. Full latest-main delayed browser not rerun |A|
|B options metrics not broadcast |Main offline/browser REST 55%, WS/Agent 50%; geometry-only signature missed metrics/ranking.5new tests RED on main, GREEN locally |B|
|500-event range |Frozen window, no pagination/total/truncation. Prior5a68actual 510-event test honestly showed incomplete history: PASS; latest API restore passed. Not all history |A/Bcontractlimit|
|3D |Actual a841 browser unavailable; 2Dcontinued. A4 automatic pass is not recording GPU/FPS acceptance |A/recorder|

See [A handoff](../backend/docs/A-final-recovery-handoff.md). This validation did not edit frontend/agent/ml/frozencontract.

Nonblocking snapshot issue: after B10 recovers online, latest buoy advice may still describe itsfault-time three offline buoys. Current state: B10 online, 8 of 10 online. C/Ashould label history/age or regenerate after recovery; Bmust not invent retraction events. Screenshots/original events retained.

## B fix completed locally, not published at this historical snapshot

Branch codex/harborguard-options-publication, tested source **e1b33055883b6bef8e003fc61a2c9f43178cfac1**, based on a841. Original fixfe0681e7be706ba33a39dfc8dd1e8b2589749de1. Production only backend/app/decision/__init__.py plus 5 parameterized B tests. Complete payload/ranking changes broadcast; identical payload deduplicated. No risk/30 s optimization/approval/shared-field changes.

Candidate **237PASS, 2SKIP, 152.24 s**; Ruff/compileall/A build pass. Actual B+C+browser t632 REST=options_ready=Agent=UI, risk 10%; 4.98839 Hz, 251 frames, max 349.02 ms, max25585B. GUI Reject/second-operator Reject persisted without restricted zones; A R2 still FAIL, not masked. Earlier fe had full real A/B repeat/browser Recovery; old full results not transferred to e1. e1 had not repeated the entire five-minute flow.

At this date: no Push/PR creation-update/Merge. Owner should review this small fix, decide merge, then lock the precise SHA; main must not be described as already fixed. Isolated preview 5182, not formal deployment.

## Demo/delivery decision

Actual 4m46s was **one-computer A/B/C 2D workflow**:A10× → L3 → YOLO PNG → template → Approve → restricted → 3D unavailable/fallback 2D → B10×600 s → actual-streamReplay. QA real REST paused at t512 for recording preparation. One PNG click needed fresh AX selection; 3D fallback; Replay End stopped before the last frame and needed Play. Not three-person onsite, nor zero-retry/full 3D acceptance. Screenshots retained; **no finished recording**.

Begin 2D candidate recording; first review the small B fix for formal freeze. If video claims complete history consistency, A fixes R1–R4/a new SHA first. Verify 3D on the recording computer, or use 2D with honest scope. Label Replay; never call old stub/captured streams LIVE or claim real reopening permission.

| Owner | Before deadline |
| --- | --- |
|B/projectowner |Review Push/merge of the tested B fix, freeze SHA, new DB; after A update, retest only affected paths, no new features |
|A |R1–R4/regression; old Demo summary length; verify target 3D or use 2D; no inferred green/decisions |
|C |Prefer verified template; cloud/local/LoRA needs separate acceptance, merged code is not a service pass; disclose synthetic metrics |
|Owner/recorder |Record/playback, accessible video URL, event rules/team/required fields, personal submission before 22:00 PDT, receipt |

[Runbook](demo-runbook.md), [historical draft](devpost-submission-draft.md). Editable draft is not rule compliance or submission.

Historical isolated preview 5184; old 5173 unchanged. Emergency Recovery:
http://127.0.0.1:5184/?replay=/final_replays/replay_maina841bf9_b.jsonl
Portable artifacts/final-delivery/HarborGuard-maina841bf9-replays.zip. Do not deploy QA fault controls.

Evidence:[JSON](../backend/docs/evidence/final-delivery-20261017.json), [Recovery](../backend/docs/evidence/final-maina841bf9-recovery.png), [YOLO](../backend/docs/evidence/final-maina841bf9-sonar.png). Local logs/JUnit/original SQLite in artifacts/final-delivery/, with hashes in the JSON. Report commit excludes DB/weights/cache/logs/credentials.
