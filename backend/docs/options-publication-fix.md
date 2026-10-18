# B Options-Metric Broadcast Fix — Historical Review Snapshot

Tested source e1b33055883b6bef8e003fc61a2c9f43178cfac1 on codex/harborguard-options-publication, based on official main a841bf9a70d8bf8237b9e03763852a34bed10368. Original implementation fe0681e7be706ba33a39dfc8dd1e8b2589749de1. e1 merged newer main into its own isolated branch, not into main or teammates' remotes. “Not pushed” below describes this report's historical snapshot, not necessarily today's GitHub state.

## Defect and change

At Security t=914, actual browser acceptance found REST residual risk 55%, while the latest options_ready/Agent/UI stayed at 50%. Optimizer recalculated correctly, but DecisionEngine deduplicated only closure/speed-limit geometry. Risk, vessel-hours, berth availability, affected-vessel counts, and ranking changes were not broadcast when geometry stayed unchanged. B owns this; A polling is not a fix.

Changed files:

- backend/app/decision/__init__.py: signature includes all frozen Option fields and ranked. Changed complete payloads publish; identical ones remain deduplicated.
- backend/tests/test_option_publication.py: five parameterized regressions independently change risk, delay, berth fraction, vessel count, and ranking. Verify immutable old events, valid payloads, checkpoint round-trip deduplication, and no automatic restriction from advice.

No optimizer/risk parameter/30-s optimization period/approval/frozen API/event-type changes. Production diff against a841:6 additions/2 deletions; 48 test lines. No frontend/agent/ml/shared/data changes.

## Actual tests

| Check | Result and scope |
| --- | --- |
| Five new regressions on official main | 5 FAIL/RED, proving the defect; not a claim the existing 232 tests failed |
| e1 full pytest backend/tests tests agent/tests -q | 237 PASS, 0 FAIL, 2 SKIP, 152.24 s; missing separate COCO smoke weights, delivered YOLO actually ran |
| Ruff/compileall/latest A build | PASS; A/C source unchanged |
| Real B+C+WS | e1 new DB, DEBUG_TRUTH_TRACKS=0, one worker; t632 REST=latest options_ready, risk 0.10, actual C template summary 0.10 |
| Actual browser | Same A a841 table 10%, Agent 0.10; screenshot/JSON retained. GUI Reject and second-operator API Reject persisted, neither restricted zones |
| Runtime | 251 states, 4.988394 Hz, max interval 349.020 ms, max25585B, peak RSS 430.74 MiB, CPU single-core-equivalent 48.76% |
| Checkpoint/writes | Five new tests cover signature checkpoint round-trip; existing persistence/failure/restart tests included in 237. No additional full real-process restart browser test on e1 |

Earlier fe on5a68 separately passed 216/2SKIP, real A1200/B600 three times each, and full browser Security→Approve→Recovery→Replay. B semantic hash stayed equal; A added legitimate option events, changing its hash as expected. **Do not count old fe's complete browser run as latest e1 acceptance.** e1 browser scope was option consistency and Reject above; 237 includes real B tests.

## Risks and remaining limits

- Optimization stays every 30 simulation seconds; more legitimate metric updates increase event count. Detection/correctness were not reduced for20ms.
- Older checkpoint signatures may publish one extra complete option set at next optimization. Generic tuple serialization remains readable, then normal deduplication resumes; fingerprint checks stay enabled.
- A R2 still fails: e1 at t=632 reject seq 1158/1201, Operator A then QA_CURRENT_2, both stored/no restricted, but UI retains old operator. This B patch does not fix other A recovery boundaries.
- 500-event window, simulation truth dependencies, browser3D unavailability, and synthetic-model errors remain. No real reopening or full-system acceptance claim.
- C cloud/local/LoRA runtime SKIP; actual model=template.

Isolated historical preview http://127.0.0.1:5182/ (B8018/C8019), DB artifacts/latest-candidate/final-main.sqlite 3. Existing demo/database untouched. Raw logs/JUnit/JSON/screenshots: artifacts/latest-candidate/; compact [evidence](evidence/options-publication-20261017.json).

At this report's date: no Push, PR creation/update, Force Push, or Merge main. Owner approval was required before publishing the isolated branch; local fixes were not main.
