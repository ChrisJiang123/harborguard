# Scenario B Unresolved Observations and Projection Association — P0 Audit

2026-10-17, America/Los_Angeles. Business correctness was fixed before LoRA/retraining/new scenario data. Browser workflow success is not reopening safety acceptance.

## Version check

- Preserved failing run: local combination3f237b87866592d43064c76a93083c0f67ac3bd0, B main8613834e7430eee40d2f020e6277dbdec72ca1f5, C6389b705bec35b8fc44018d1c14d770f2a82b364. B ended8clear/2blocked/2unsurveyed and incorrectly estimated12h.
- Lenovo did not provide its exact audit checkout SHA, so identical audit versions cannot be assumed. Local original frames reproduced250m, UUV/conf0.595196 and0m/no detection. [Original evidence](evidence/survey-p0-original-failure.json) remains unchanged.
- Starting official mainc7840813c6a98c32ada5b91da6e6221dc74b121d included B#10 (6353421 implementation) and handoff#12; C remained6389b70. #10 had unresolved protection, bounded retries, C fan projection, but selected disaster candidates by truth class debris and identified them by truth ID. Truth-independence audit therefore failed.
- Branch codex/harborguard-survey-observation-audit started there. B code/tests/docs only; A/C/shared/data/training unchanged; no automatic Merge/Force Push.
- Implementation97a8c751c8ba9a18a6e89ace79f27df99751f28f. Later evidence commits do not change that algorithm.

## B changes

1. New synthetic active-observation boundary backend/app/sim/sonar.py generates anonymous meter-level positions for every geometric reflector, without truth class/target ID. Changing class/ID does not change observation identity. The old debris filter was removed, not hidden in a helper.
2. Disaster policy uses only observation positions, buoy geometry, and model output. Empty/non-debris/low-confidence/near-field/protection failures remain unresolved even at coverage1. A disappearing observation does not clear previously unresolved hazards.
3.20-simulation-second cooldown, maximum3 actual detections, preferring different physically available buoys. Class-free positions associate by40m nearest-neighbor continuity; crossing a grid boundary does not reset budget. Exhausted contacts stay unsurveyed. Near-field/protection blocks without emission consume no actual shot and create no fake image. Crowded/crossing identity accuracy was not accepted in this synthetic B test; conservative merges are possible. No truth-object identification claim.
4. Persist internal reason and explain near-field/forbidden-ping/miss/low-confidence/non-debris/retry count in existing log events. No new public fields/enums. Deduplicate logs by reason/actual-shot count, avoiding per-tick spam.
5. When position quantization's half-diagonal uncertainty intersects adjacent zones, both remain conservatively unresolved/blocked. Rounding cannot put a hazard next to a green zone. This is a synthetic-observation assumption, not a real-sea error model.
6. Scenario-to-sonar generation sits at the sim boundary. True class generates physical image shape only; detector output determines classification. Other reflectors are rendered too, without assuming a single debris object.
7. Pinger association takes explicit observed/predicted range/bearing through B's existing internal sonar_pixel projection. Removed guessing association range from rendered truth targets when prediction is missing. Two boxes from actual C render_ping prove old linear projection selects the wrong box and the new one selects the proper range/bearing.
8. BFS still uses only clear channels and adjacent clear berths. Savings derive from current clear count×SURVEY_H; restricted is no longer wrongly included. Neither9h nor12h is a target. Real-model assertions derive expectations from actual states.

0m stays0m: no30m clamp or moved target. At zero range bearing is undefined; image input explicitly represents it as0°, keeping range0. C survey retains the30m near-field guard. Original full-stub positives still require4 detections and6/4/2; tests are not passed by making every zone yellow.

## Executed verification

[Machine evidence and hashes](evidence/survey-p0-20261017.json). Raw JUnit/full new-model calls remain in ignored artifacts/survey-audit/.

Final full suite **211 PASS, 2 SKIP, 93.88s**; targeted35PASS. Skips lack a separate COCO smoke weight; delivered sonar weights ran. Ruff, compileall, pip check, diff check passed.

Independent real HTTP/WS on the same final algorithm: cold5.898s, restart5.785s, 294frames, 4.99733Hz, max interval363.56ms, P99267.65ms, max25381B. Actual template recommendations, approve/reject, disconnect compensation, and same-DB persistence passed. Peak RSS430.85MiB, mean single-core CPU39.25%. Short sample, not20-minute endurance; not browser business acceptance or real-sea safety proof.

| Case | Measured outcome/verdict |
| --- | --- |
| Original250m frame, seed2029167940 |Same weights still predict UUV/conf~0.595196; no claim model fixed. Replaying failure stays unsurveyed across0.9 coverage and3 exhausted attempts, excluded from routes: PASS |
| Original0m frame, seed1926751965 |Same weights still miss; near_field, 0 actual detections, coverage1 remains unsurveyed: PASS |
| Controlled miss/wrong class/low confidence |Checked at.1/20.1/30.7/40.1/40.2/1000simulation seconds; max3; threshold cannot clear unresolved: PASS |
| Truth-class/ID access guard |Objects throw on reading world cls/id. With captured sensor frames substituted, policy runs; 6classes at same location keep same contact identity: PASS, disaster-policy scope only |
| Multiple-target C projection |Actual boxes:164m/30°UUV and280m/0°debris. Old formula selects debris; new association selects UUV; predicted point within3px of actual box center: PASS |
| Near-field/protection/retry/rollback/restart |Executed with safety/history tests; checks count, reason, RNG, transactions; see machine totals |
| Real-weight B |Full600s×3, DEBUG truth tracks off; all6clear/3blocked/3unsurveyed; none of4 hazardous locations clear; identical semantic hashes |

Final B: anchorage_north/channel_main_n/channel_turning blocked; berth_fuel unsurveyed. Route only channel_entrance/channel_main_s; berth only berth_container_1. Derived9h is a simulation-assumption metric, **not reliable real reopening authorization**.

During regression, anonymous aiming/undefined zero-range bearing changed the old full-stub positive from4 to6 detections. Original assertions were retained; zero-range representation was fixed and full suite rerun. No relaxed test hid the regression; raw/final JUnit hashes remain.

Full new scenes use synthetic observed aiming/full-scene physical orientation; image/seed allocation can differ from old failures. A newer positive detection does not prove the original misclassification disappeared. P0 protection is established by original-frame replay and controlled failures; original confidence/raw evidence are preserved.

## Truth-dependency audit — whole system is NOT accepted as truth-independent

| Location | Current dependency/boundary |
| --- | --- |
| sim/sonar.py: survey_contacts |Still ideal synthetic observations from world geometry: anonymous meter-level candidates for all reflectors. Not extracted from real echoes/PNG; receiver-level misses are unmodeled. No class/ID reads, but geometry remains simulation-derived; real end-to-end sensing PENDING |
| sim/sonar.py: sonar_scene, sim/acoustics.py |True classes generate synthetic shapes, source levels, cues only—permitted scene generation. These labels are not real YOLO/reopening evidence |
| perception/classifier.py fallback |Explicit stub uses generated labels, an existing demo fallback rather than independent perception. Real-weight scenes assert every Detection.model=yolo26n; no silent fallback accepted |
| perception/tracker.py:87, engine.py:274 |Simulated AIS still matches directly against world vessel list. B4 was not refactored. This unresolved truth coupling prevents claiming the whole tracking/classification chain is independent |
| engine.py:_truth_tracks |Explicit DEBUG_TRUTH_TRACKS=1 fallback only; disabled here; not normal localization evidence |
| tools/model_acceptance.py |Truth positions used only for offline scoring of hazardous clear zones; permitted evaluation, not runtime feedback |
| decision/disaster.py, pinger association, BFS |No class-based candidate filtering/truth-ID association; anonymous observations, predicted geometry, detector outputs, and zone states. Still depends on synthetic sensor assumptions above |

Coverage remains a400m demonstration area integral versus300m actual imaging range. A0.9 threshold is not underwater safety evidence. Hazards never entering the observation stream cannot be guaranteed detected by this patch. Unresolved protection fixed does not mean green areas passed real reopening acceptance.

## A/C/Lenovo handoff

- A displays backend blocked/unsurveyed, never infers green from coverage/non-debris. Reasons can appear in existing logs; ZoneStatus has no structured reason. Do not add fields or derive approvals/state from prose. A dedicated reason field needs contract review.
- C should provide a public pixel-projection helper exactly matching render_ping. This round compares B's internal formula to actual C boxes, without changing C/frozen signatures. Do not claim the helper integrated before it is merged. LoRA is not a blocker.
- Lenovo replays250m/0m seeds and controlled misses/wrong/low-confidence, then real B. Both blocked and unsurveyed are acceptable; hazardous positions must never clear. No fixed9h assertion or prior training required.
- C4 in-flight files, A source, weights, shared, scenario data unchanged; explicit staged file list before commit.

## Reproduce/deploy

```powershell
.venv/Scripts/python.exe -m pytest backend/tests/test_survey_audit.py backend/tests/test_model_safety.py backend/tests/test_disaster.py backend/tests/test_real_model.py -q
.venv/Scripts/python.exe -m pytest backend/tests tests -q --basetemp=artifacts/p0-pytest
.venv/Scripts/python.exe -m backend.tools.model_acceptance --scenario b --repeat 3 --out artifacts/p0-real-b.json
```

Use CPU runtime dependencies matching specified C weights. Missing weights/runtime explicitly SKIP, not real-YOLO PASS. New observation-grid parameters change fingerprint; preserve running demo/database and use independent HARBORGUARD_DB, e.g.backend/runtime/survey-p0.sqlite3. No forced old checkpoint, DB schema, or shared-contract change.

At this snapshot5173 still ran old checkout1269f3e, not this fix. Isolated HTTP/WS used8004/8006/new DB and closed only its own processes. Lenovo must pull the exact new SHA/new DB; old browser/checkpoints are not new-version evidence.
