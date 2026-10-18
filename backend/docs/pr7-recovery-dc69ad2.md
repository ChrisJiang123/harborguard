# PR #7 Recovery Fix — Actual Browser Retest

Date:2026-10-17; heartbeat harborguard-pr7. **Old log overwrite and false-restart warnings were fixed; the ordinary single-operator demo ran. Two A deduplication boundaries still failed, so PR#7 was not fully accepted.** No A/C production, B algorithms, frozen interfaces, or migrations changed. No Push/PR update/Merge.20ms remained best effort.

## Fixed versions/environment

| Item | Exact tested version |
| --- | --- |
| A PR#7 |dc69ad28ac37e8d0592d9271f9d61e28c79ff27c|
| B production |04de0fe7abb9eb52ba7ae806beb30131d4b04a8e|
| C template |78d39574266b01a582b0626c17021181749271c8|
| Local candidate merge |b48cac76e301a047afa330bced2eae6e388d534c|

New managed worktree combined A's fix with the previous fixed B/C without conflict. Directory checks: frontend=dc69ad2, backend/shared=B04de0fe, agent/ml/tests=C78d3957. No new C model route. Three later B tests were run separately in B's primary checkout, not described as original candidate tests.

Original5173 → QA8000 → B8003/C8001 checkout/processes/database were preserved. Candidate used QA5174 → B8004/C8006/new SQLite. A's supported build settings: VITE_API_BASE=/api, VITE_WS_URL=ws://127.0.0.1:5174/ws. QA served static files and transparent HTTP/WS with optional delay/disconnect. Only its launcher pointed internal B Agent calls at8006, without source/message changes. B CORS unchanged; same-origin QA is not proof of new5174 cross-origin permission.

## Executed checks

| Case | Result | Evidence/scope |
| --- | --- | --- |
| A build/lint/A1–A6/check: recovery |PASS|npm ci119packages, 0vulnerabilities; build/lint/7checks passed; 995.19KB3D chunk warning|
| Existing B+C suite |PASS with skips|Same-drive temp; 120 passed, 2 skipped, 68.57s; weight skips are not real-model acceptance|
| B history tests |PASS|3new boundaries; test_history.py18passed, 5.07s; RuffPASS; fixtures are not browser scenes|
| First-refresh false rollback |PASS|New-origin first connection/multiple ordinary refreshes had no false warning|
| Actual new C advice during recovery |PASS|Paused A t479 beforeL3; delayed already-read events response5s, resumed B; actual template rec-d89ea3415187 survived with A1 card, 4options, unique newlog, no false restart|
| Exact previous race |PASS|Old options response3s delay; after logGET added QA_PREVIOUS_RACE_EXACT_REPRO_02; retained once plus prior marker, rejected state correct, no loading/false restart|
| Failed reject persistence |PASS|Disposable QA DB trigger; actual GUI reject503, decision0/restricted0, UI failure/retry; removed trigger, retry succeeded|
| GUI reject/refresh |PASS|A1/opt-1, Operator A, t484, seq887; refresh restored rejection/template|
| Real WS compensation |PASS|Proxy closed browserWS; DISCONNECTED while B/C ran. Three ordered offline logs and independent REST approve A1; reconnectLIVE, QA_REMOTE approval/5restricted agree, eachlog once, UI3/2/1 newest-first|
| Same-DB B restart |PASS|seq1421 → 1519, state equal exceptseq, event list equal, paused=true, UI approved; not database replacement|
| GUI approve/refresh |PASS|Second full A; actual C rec-e3714ebee774; A11/opt-1, Operator A, t486, seq3064; 5restricted/confirmation survive refresh|
| Same-time legitimate identical logs |FAIL, A|B retains seq143/144; UI2live → 1afterrefresh|
| New same-time operator decision |FAIL, A|A1/opt-1approve QA_REMOTE_2, seq1520, t484 persisted; live card retained QA_REMOTE while logs showed second; refresh corrected|
| Honest500-window degradation |PASS, limited|520logs → events500, olddecision0, archive596events/3decisions; UI500-limit/history-unconfirmed, no false restart/fabricatedapprove; not full-historyquery|
| Recovery regression |PASS, synthetic|Pausedt208, B4/B7down, plan/4blocked/2unsurveyed/9h assumption visible, no oldA decisions|
| Empty-track PNGs |PASS, stub|det-6..9track_id empty; all4 opened/decoded640×640 via existing/api/sonar, synthetic labels|
| 2D/3D |SmokePASS|Actual rendered screenshots, return2D; no formalFPS/projector acceptance, overlay occlusion remained|
| Two B JSONL replays |SmokePASS|Aseek20:00, approve disabled; Bseek10:00, 4debris; read-only, no Bconnection, local det-1PNG640×640|
| Genuine low-seq new session |PASS, specific scope|A11approved; oldoptions delayed5s while intentionally switching B to brand-new QA DB/restart. seq30, t0, scenario null. Correct rollback notice, oldA11/approval cleared, delayedresponse did not resurrect it; oldDB4decisions retained. This deliberate replacement is not ordinary restart data loss|
| Final short WS health |PASS, limited|8.14s idle/newDB; 40frames excludinginitial, 4.991Hz, max216.63ms, max1809B, seqincreasing; candidate/original health200. Not10×load/newsoak|

Three new B regressions prove identical logs are distinct seq events, and two operators can legally issue same-action/same-time decisions. Both survive restart and latest_decision points to the latter. No new API/idempotency rule was added to accommodate A's content deduplication.

## Two recommendations for A

### R1: Log merge loses legitimate multiplicity

Locations: store/useHarbor.ts logIdentity:108, mergeRecoveredLogs:113. A Set of t: level: source: text confuses repeated delivery with two independent same-content events.

Pause/idle and POST twice:

```json
{"level":"info","source":"operator","text":"QA_DUPLICATE_SAME_TEXT_AND_TIME"}
```

GETevents has seq143/144; GETlog has2; UI2live → 1refresh. Same source/time/text cannot justify deleting a legitimate record.

Use existing event.seq for structured log identity. ID-less REST snapshot merging must retain multiplicity, not Set(texttuple). Add both tests: two legitimate identical logs remain2; the same replayed event remains1. Existing contract expresses the within-window distinction without new B fields.

### R2: Decision identity ignores seq/operator

Locations: eventIdentity decision branch:95, reduceMessage duplicate-return:176. Current alert/option/action/t key ignores different operators' new events.

At same paused A1/opt-1 time, approve QA_REMOTE then QA_REMOTE_2; B accepts/stores bothseq. Secondseq1520, t484 appears in logs but card remainsfirst untilrefresh.

No separate decision business ID exists; deduplicate by durable event.seq with existing session/generation for actual rollback. Differentseq cannot be ignored because action/t match. Test same-time twooperators → immediate latestcard, and same-seq retransmit → no duplication. Preserve new false-restart/generation/delayed-request protections.

These remain final history/audit consistency defects. Standard single-operator/one-decision five-minute flow passed. Do not call all Demo startup broken, or hide the edges as fully green.

## Handoff/limits/retest status

- Evidence: evidence/pr7-recovery-dc69ad2.json, including actualoperator/seq, timegating, browserresults. RawHTTP/DB/screenshots ignored artifacts/pr7-recovery-dc69ad2/; noDB/cache/sourcecopies committed.
- Three B regressions in backend/tests/test_history.py; production/shared unchanged. BothQA DBquick_check=ok; failuretriggerremoved.
- Fixed Ctemplate/stubrecognition only. No realweights/sea, hardwareoffline, three-personrehearsal, formalGPU/FPS, or arbitrary older-history pagination acceptance. Recovery advice not implemented in that template baseline.
- Read-only GitHub found main already included #8merge8a911ae; not an action by this run. No remote mutation/main switch/merge. Fixed candidate results do not accept allmain.
- dc69ad2 testing completed; laterheartbeats should not rebuild/retest sameSHA. WaitA R1/R2newSHA; unrelated3Dupdates stayquiet.
- Final read-only PR#7headb549515337e0a50889d331ae397e4f381e4694ca was UIEnglish. eventIdentity/logIdentity/mergeRecoveredLogs unchanged versusdc69ad2; no redundantfullrun/fullacceptanceclaim. Testedversionremainsdc69ad2.
- Temporary5174/8004/8006services/pageclosed, worktreearchived, recoverable from the candidate commit. Original5173/8003/8001rechecked200. OriginalQA DB/screenshotsretained.
