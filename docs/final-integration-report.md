# HarborGuard Mainline Handoff Integration Check

Historical snapshot, 2026-10-17, America/Los_Angeles. Later business P0: [unresolved observations/projection/truth audit](../backend/docs/survey-p0-audit.md). Build/API/browser workflow results do not establish real reopening safety. The old 12-hour conclusion must not be presented as reliable.

Baseline official main **782d04d61858cca4849f7ff39942394e5b56d1f3**. This responded to the owner's request to inspect old#3/#6, organize missing materials, and Push again. No automatic Merge main, Force Push, old-PR closure, or A/C edits.

**Both earlier pushes existed on GitHub; nothing was lost. They had not entered main and both now had README conflicts.** Other PRs had already merged backend implementation, so it did not need rewriting. Missing B handoff tools, OpenAPI, mocks, and runbooks were migrated onto current main, avoiding obsolete candidate code/conclusions.

## GitHub state at this audit

| PR | Verified state | Treatment |
| --- | --- | --- |
| [#3](https://github.com/ChrisJiang123/harborguard/pull/3), head368df2ede67f2c8e353a628afb1559a95d70cb68 |Fork Draft, open, unmerged, mergeable=false; actual conflict backend/README.md |Migrate B tools/tests/OpenAPI; mocks in B, not frontend |
| [#6](https://github.com/ChrisJiang123/harborguard/pull/6), head5af2ae08d9baf6aa53fe58cacd6552986eed76a2 |Fork open, nondraft, unmerged, mergeable=false; same README conflict |Update integration/runbook; archive original template report/JSON; do not reintroduce old C |
| [#10](https://github.com/ChrisJiang123/harborguard/pull/10) |Merged by maintainer, merge700eb93, Bhead4fb8941 |Conservative sonar/projection/warmup/evidence already main |
| [#4](https://github.com/ChrisJiang123/harborguard/pull/4) |Merged by maintainer, top main merge782d04d, Chead6389b705bec35b8fc44018d1c14d770f2a82b364 |Preserve C source/weights; merge is not route acceptance |
| A#7/#11 |#7 already in main history; #11merge8ca2eb3 includes NOAA/proposed buoys |No frontend edits; existing build/self-checks, retain venue/browser limits |

Branch codex/harborguard-handoff-refresh. Old#3/#6 unchanged/unclosed. Owner may treat the new PR as replacement for missing handoff deliverables, rather than merging the entire old#6. Final links/mergeability/CI are reported at handoff.

## Migrated deliverables

| Source | Current location/reason |
| --- | --- |
| #3:21REST, 14events, structures, recovery |[frontend-integration.md](frontend-integration.md), corrected rejection, durable seq, old details, 500-window/new-DB limits |
| #3 OpenAPI |[integration/openapi.json](integration/openapi.json), exported from current FastAPI; API unchanged |
| #3 Mock |[backend fixture](../backend/fixtures/integration/backend.json), all requests/responses, both decisions, relativePNG mapping; no frontend/public write |
| #3 exporter/tests |[tool](../backend/tools/integration_bundle.py), [tests](../backend/tests/test_integration_bundle.py), memory DB / explicit model fixture; proves configured demo DB/frontend untouched |
| #6 integration/runbook |This report/[demo-runbook](demo-runbook.md), rewritten for main; no stale C-unmerged/reject-only-log/four-real-debris claims |
| #6 original report/JSON |[archive](archive/README.md), original5af2ae0 historical evidence; English prose translation does not rerun those tests |
| Old README/acceptance/files/validation |Historical numbers retained; current links/limits added; README resolution does not erase persistence/sonar safety |

Mock business state, Agent text, and PNG are explicit fixtures. Actual HTTP routes/Pydantic execute. This is not timing, YOLO quality, three-person rehearsal, or browser acceptance. A1/T1/opt-1 fixtures cannot approve a new LIVE scene.

## Actual execution

[Machine record](final-integration-results.json); raw JUnit/build outputs in ignored artifacts/handoff-refresh/.

- Four new handoff tests PASS:21REST, state/events, generated-output equality, PNG decoding, structured reject/approve, distinct ordered seq, no demo DB/frontend mutations.
- Initial B+C full run194PASS, 1FAIL, 2SKIP, 92.55 s. Failure was an old B assertion demanding byte-identical proposed frontend buoy placement versus LIVE; not an algorithm crash.
- After targeted data/handoff fixes, 10targeted tests PASS; final **196PASS, 2SKIP, 89.03 s**. Skips lack a separate COCO smoke weight; delivered sonar weights actually ran. SKIP is not PASS.
- A npm ci/build/lint/check: recovery/check: sonar/check: a1…a6 PASS.3D chunk 1003.10 kB warning retained. Automatic checks do not establish browser/GPU/projector acceptance.
- Ruff, compileall, pip check, diff check PASS. B production algorithms/migrations/shared/frontend/agent/ml/Ctests/data unchanged versus baseline. Re-export assertions verify generated artifacts.

### Compatibility issues handled

1. Old exporter used default persistent DB, possibly touching demo data or failing fingerprint. Now forced :memory:, without simulation loop/real YOLO. Tests point HARBORGUARD_DB at an old file and prove contents/lock unchanged.
2. Old tool wrote into frontend, violating A/B ownership. Now backend/fixtures/integration with explicit layout PNG. A chooses import; no API/new static port.
3. A#11 marks offline buoys as proposed deployment; old B test required root data/buoys.json byte equality. Keep original zones/assets/vessels equality and add LIVE API checks proving B coordinates before/after startup. Proposed data gets contract-compatible validation; A check: sonar still validates layout/no moved observations. B geometry assertions/coordinates were not weakened.

## A/B/C state and remaining acceptance

| Module | Implementation/evidence | Failed/unverified |
| --- | --- | --- |
| A |Main2D/3D, NOAAH 12617, proposedbuoys, recovery/decisions/replay; build/self-checks pass |New browser edges, recording/projectorFPS, actual land/water/vertical-datum alignment. NAVD 88↔MLLW tie is not proved by appearance |
| B |REST/WS, persistence, structured approve/reject, tracking/risk/options, conservative recovery, warmup; missing handoff now migrated |New C L3 t505>500, fuel near-field unresolved, 500window/no full pagination, new-combination endurance pending |
| C |Delivered YOLO/Agent in main; same B/C production tested separately via real HTTP/WS/template/restart |Synthetic sonar only; cloud/Ollama/LoRA not enabled/accepted here; English 60/300-character/fact validation belongs to C |

Previous isolated candidate with identical B/C production but different A: three full offline A/B repeats with matching hashes; 191PASS/2SKIP; cold 5.959 s; 5.00168 Hz, max 393.04 ms; actual template advice, approve/reject, disconnect compensation, restart passed. [Source](../backend/docs/sonar-safety-integration.md). These API results are not latest-A browser passes.

### Retained limitations

- Actual YOLO first UUV 363.9 s, L3t505; original500s upper limit FAIL.20 ms best effort; no statistical manipulation.
- Real-model B6clear/3blocked/3unsurveyed, 9h estimate; fuel~0m remains unresolved. Old template 6/4/2 does not replace this.
- /events latest 500 only, no pagination, total, gap marker. Internal durability is not public all-history access. /log current cachemax 1000. Same DB seq continues; new DB requires honest uncertainty.
- New parameter fingerprints reject old DB. Preserve old files; new independent HARBORGUARD_DB. No deletion/fingerprint edits/double writer.
- A had fixed most recovery entry paths, but legitimate duplicate logs, multi-operator decisions, and old REST/new-state boundaries had prior issues. Self-checks do not substitute for browser reproduction. A owns fixes; no log-derived approval.
- Physical Wi-Fi, ESP 32/LoRa, sea sonar, three venue rehearsals, new-model 20-minute soak unverified here. A's NOAA visual/B's schematic business data are different sources.

## Review/integration

No B production algorithm, DB schema, REST/WS contract, frontend/agent/ml/shared/data changes. Branch adds B tools/tests/mocks/OpenAPI/docs only. Models, databases, caches, logs, original taskbook excluded from new commits. Unapproved pagination remains a proposal.

Owner decides merge after Draft review. Old#3/#6 may later be closed as superseded by the owner; this agent did not close them. No CI records does not equal CI PASS. Complete controlled five-minute workflow on actual equipment before recording/submission; newer browser/target-device checks remain required.
