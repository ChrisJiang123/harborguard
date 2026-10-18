# HarborGuard final integration check report — historical PR #6 snapshot

> English translation of the report at PR #6 head `5af2ae08d9baf6aa53fe58cacd6552986eed76a2`. The original text remains in Git at that commit; the adjacent JSON evidence is unchanged. All findings below refer to that historical candidate, not the current main. Later fixes and real-model results do not retroactively change this report.

Conclusion: **this candidate was suitable for a Draft PR and a controlled demonstration; full team acceptance still had open work and did not imply unconditional readiness to merge into main.** At the user's direction, refresh recovery and the disaster detection-image entry point were assigned to A; frontend source was not modified in this round. No new YOLO, LoRA, LLM routing or other product feature was developed or enabled. Frozen v1 remained unchanged.

See the [five-minute demo runbook](../demo-runbook.md), [frontend handoff](../frontend-integration.md), and historical machine-readable [results](pr6-final-integration-results.json). The first two links lead to documents that may subsequently have been updated.

## Branches, repository and PRs at the time

The baseline was origin/main `5817b9c`, verified C template commit `78d3957`, and B handoff commit `368df2e`. Before publication, C's remote branch gained `9af08a7` (cloud/Ollama/template routing). That change was outside this round's scope and was neither included nor verified; the candidate retained the template version. Remotes were origin = ChrisJiang123/harborguard and fork = tankewudi/harborguard. Existing B/C commits were integrated on `codex/harborguard-live-integration` with final delivery documentation. Neither local nor remote main was changed.

| PR / branch | Role in this historical candidate | Check result |
| --- | --- | --- |
| PR #2 | B backend implementation | Already merged into main by the repository owner |
| PR #5 | A6 frontend | Already merged by the repository owner; main supplied the frontend baseline |
| [PR #3](https://github.com/ChrisJiang123/harborguard/pull/3), codex/harborguard-backend-mvp | B OpenAPI, mock, handoff exports and tests; head 368df2e | Left open / Draft; merge preflight against the then-latest main found no conflicts; status was not changed |
| [PR #4](https://github.com/ChrisJiang123/harborguard/pull/4), c/model-agent | C1/C2/C3; latest remote additionally included three-route model selection | Open; candidate included only original template baseline 78d3957. New remote 9af08a7 was left for C's review; C source and PR were not changed or merged |
| codex/harborguard-live-integration | A+B mainline plus the above B/C commits and this report/runbook | Intended as a separate Draft, explicitly documenting overlap/dependencies with #3/#4; no automatic merge |

C was advised to decide whether the new #4 routing belonged in the final demo; the team could merge #3 as appropriate and then review the integration Draft. Taking the latest #4 would require renewed routing/dependency/demo verification: template results did not validate 9af08a7. Shared commits would naturally disappear from the diff without reverting C's newer changes. This round did not close or approve teammates' PRs.

`git merge-tree --write-tree origin/main <branch>` found no conflicts for either the B branch or integration branch. The integration branch retained original #3 and verified-template #4 commits rather than copying files and rewriting history. A's frontend/src, B's backend/app and shared matched main; C's agent/ml/tests matched pinned commit 78d3957, not later 9af08a7. New commits contained only B documentation and verification results.

Potential future conflicts involved shared documentation such as backend/README.md, docs/files.md and docs/validation.md, plus any integration baseline changed by A/C later. No actual conflict was present then; that did not guarantee later commits would be conflict-free. Fetch and rerun preflight before publication after main changes. The original taskbook remained untracked; real .env files, logs, caches and model weights were excluded.

## Module completion status at that snapshot

| Module | Implemented and verified | Still open |
| --- | --- | --- |
| A frontend | LIVE connection, static business layers, 2D, real 3D rendering, alerts/options, template advice, operator approval confirmation, Security/Recovery file replay; build/lint/A1–A6 checks passed | Refresh/disconnect event compensation; no-track debris image entry; projection, target-device FPS, real Wi-Fi disconnect refresh and cross-device video playback |
| B backend | 21 REST operations, 5Hz WS, event cache, anonymous perception/tracking, risk levels, active ping, option comparison, operator decisions, disaster coverage/reopening, fault injection, Agent proxy, replay and contract samples | Real harbor land/water verification; not all individual ticks met <20ms, including image-generation peaks |
| Submitted C version | Real sonar renderer; template event→context→recommendation→submission loop; factual Q&A with an 18-second budget below B's 20-second proxy budget; Agent did not approve | Trained sonar YOLO weights and broader disaster/buoy recommendations were outside this candidate. C's new cloud/Ollama routing was outside the verified template baseline; no model was added/enabled in this round |

`Detection.model=stub` and `Recommendation.model=template` had to remain visible. Integrating C's renderer did not mean trained recognition weights had been delivered. Recovery used `scenario=b`, `mode=disaster`; frozen enums were not renamed.

## Blocking issues and conditions for a demonstration

| Severity | Issue, evidence and owner | Effect on submission / demo |
| --- | --- | --- |
| Full acceptance blocker; A | Real A → L3 → pause → approve → refresh: B retained restricted state and recommendation/decision events, but A's advice, approval confirmation and logs became empty. frontend/src/data/ws.ts did not call existing /api/events after connecting | Did not block a Draft. Avoid refresh during the controlled demo. Refresh recovery could not be claimed accepted. Fix with existing interfaces; historical events must not overwrite a newer snapshot |
| Disaster image-entry acceptance blocker; A | B's four debris detections had empty-string track_id and all PNGs were retrievable. Timeline.tsx enabled clicks only for events with an active track, leaving all four detection points disabled | Blocked-zone/reopening display remained demonstrable, but scenario B's image popup entry could not be shown. Opening the existing preview by detection.id required no contract change |
| Complete-main startup blocker; maintainer/C | C3 was still in #4; main lacked agent/main.py. Latest #4 additionally contained routing not verified in this candidate | Candidate had the template loop; maintainer had to select the final C revision for main. Taking 9af08a7 required new routing/dependency/demo tests; older template results could not substitute |

A controlled five-minute demonstration required preinstalled dependencies and a built frontend, three healthy services, LIVE connected, no refresh while A was active, and a scenario B focus on map/coverage/reopening rather than the unfixed image entry. Otherwise use explicitly labeled REPLAY; never present it as live approval.

## Non-blocking issues and acceptance boundaries

- C's dataset generator used os.path.relpath. With the default temporary directory on D: and repository on C:, three tests had failed. Pointing pytest basetemp to repository artifacts made them pass. C source was not modified and the original failures were not hidden. The demo did not generate training datasets.
- Two pretrained-weight inference smoke tests skipped because .cache/yolo26n.pt was missing. They did not count as passes; no model was downloaded in this round.
- The frontend 3D chunk was approximately 981KB, with a bundle-size warning. Three.Clock/TestClient emitted upstream deprecation warnings; no resulting runtime failure was observed.
- Existing 20-minute endurance evidence came from an earlier B acceptance run. It did not establish 20-minute endurance for this A/B/C combination. See JSON for this run's actual duration and tick warnings.
- The 20ms individual-tick target still had overruns. The then-observed 5Hz output supported the demo, but average frequency did not prove every performance requirement passed.
- Map and schedule data were illustrative/fictitious. The 9-hour estimate used demonstration assumptions such as 1.5 hours per zone; real-chart deployment verification was incomplete.
- Five minutes referred to presentation after setup, not first-time online installation plus projector validation.

## Tests passed in this historical round

| Check | Command / evidence | Result |
| --- | --- | --- |
| Full B + C regression | `.venv/Scripts/python.exe -m pytest -q backend/tests tests --basetemp artifacts/final-integration-pytest` | 103 passed, 2 skipped, 57.16 seconds; included B's two handoff-sample tests |
| Python static/dependency checks | Ruff backend; compileall backend/agent/ml; pip check | Passed; no dependency conflicts |
| Frontend | npm run build, lint, check:a1…check:a6 | All passed; bundle-size warning retained |
| Frozen fields | Compared all 12 interface field/type definitions between A and shared/types.ts; B/C original-contract tests | Matched; 21 REST operations, no field changes |
| Actual combined services | B 8000 + C 8001 + A 5173; existing-contract Security, advice, reject/approve, reset and Recovery checks | See historical JSON runtime; count as passed only where status=passed |
| Offline assets | Read both JSONLs through actual frontend static service, validated every Schema/seq/wall_ms, decoded all PNGs | JSON records counts/results; team replay files were not re-recorded or overwritten |
| Source ownership | Git compared A/main, B/main and C/78d3957 | Production source matched the corresponding submitted revisions |
| Merge preflight | main + B branch; main + integration branch | No conflicts at that time; reread GitHub mergeability/CI after publication |

The same production-source version had earlier completed actual browser LIVE/3D/approval confirmation and B replay final frames: A was 120 wall seconds / 1,200 simulation seconds; B was 60 / 600, ending at a 9-hour reopening estimate. This documentation commit did not relabel those checks as new projector, Wi-Fi or model verification.

## Interface and state consistency at that snapshot

- Full REST paths/constraints/examples were in frontend-integration.md and docs/integration/openapi.json. WS was ws://localhost:8000/ws, without an /api prefix. State was a full snapshot; event/state shared increasing seq.
- L3 generated options_ready; C obtained facts by existing GET operations and posted /api/recommendations; B validated references and broadcast. Advice did not automatically produce restricted state.
- At this historical revision, reject wrote only a log; approve emitted decision and restricted zones. Option zones_closed matched actual restricted zones. After reset, stale approvals returned 409. This behavior was later superseded; do not treat it as the current persistence contract.
- B's /api/events could recover recommendation/approval events; A consuming that recovery was a separate open task. No fields were added to state to conceal it.
- B /api/agent/ask → C /ask returned answer/model. The actual template service worked; cloud and Ollama were not enabled.
- Recovery's four detections without tracks conformed to v1. Coverage, buoy failures, 6/4/2 zone states and the 9-hour estimate matched REST/WS/existing replay in this historical candidate.
- Verified ports were 8000/8001/5173, with Node 24.19.0/npm 11.17.0 and Python 3.11.17. Exact dependency/environment commands were in the runbook. Real keys did not need to be committed.

## Publication and delivery checks

Only explicitly listed B documents/results were staged. The round scanned 237 indexed files and 238 distinct blobs in outgoing history. No checked common secret pattern or excluded environment/cache/log path was found. This was pattern scanning, not proof that all possible secrets were absent. Existing main assets replay_a (~10.9MB), demo_full (~9.6MB) and C's existing samples.png were intentional demo resources and were not regenerated. The largest new delivery file was a textual report/JSON; no new weights, logs or caches were added.

Retain original B/C commits and push to an independent feature branch; preserve #3/#4 status and make a new integration PR a Draft. If there are no CI workflows/check records, report "not configured/no records", never "CI passed". Final delivery should include the PR link and live mergeability/CI state.

This historical report supported safe submission, review and a controlled demonstration. It did not replace A's two fixes, teammate review or the maintainer's decision to merge main.
