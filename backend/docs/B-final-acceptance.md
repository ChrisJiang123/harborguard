# HarborGuard B backend and algorithms acceptance report

> English translation of a historical report, not a new acceptance run. The original report is preserved in Git at `d2d4c6fbdff72de5b2d2c02aab0c39723513f3a8`. Original requirement wording and raw evidence remain in the taskbook and linked JSON. References to “this round”, “current main” and open PRs below describe the original snapshot.

The later [unresolved-observation, projection and truth-dependency audit](survey-p0-audit.md) established that the old 12-hour estimate and incorrectly green areas were unreliable. Synthetic observations, stub and AIS retain limitations; full-system truth-independent acceptance has not passed. The historical checkbox totals below do not cover that additional audit scope.

Original report date: 2026-10-17, America/Los_Angeles. Basis: **HarborGuard Taskbook B — Backend and Algorithms**, for the lead and A/B/C teammates. The later [sonar-safety/C6389b70 supplement](sonar-safety-integration.md) recorded real-model Security L3 at 505s, beyond the original 500s bound; browser and new-version endurance were pending there. These 37 historical items cannot establish full acceptance of the newer C revision. The lead changed 20ms to a best-effort target.

**B's core MVP was implemented and conditionally demonstrable with synthetic data; the original taskbook was not fully accepted.** All 37 original checkboxes are covered: **31 PASS, 1 FAIL, 5 PENDING**. The original every-tick <20ms measurement failed; removal of the hard gate makes it non-blocking for Demo, not PASS. Historical passes apply only to their recorded versions, not the latest main.

This report's B regression run was **95 passed / 0 failed / 0 skipped, 63.17s**. Ruff, compileall, dependency consistency and strict sample TypeScript compilation passed. Only B reporting and isolated verification were performed: no production/A/C/coordinate/contract/migration changes, Push, PR or Merge.

## Basis and evidence rules

Original local input: the B taskbook DOCX, SHA256 `9291ad36b4c3d38563caa681f4634c107db5723975e28f73d0e2c25cef9fe9ac`. Its original filename is retained in the machine-readable evidence. All 37 checkboxes were extracted and, before this translation, the Chinese requirement wording was checked word for word against the original. Conclusions were not inferred from `docs/acceptance.md` marks. The attachment was not added to Git without permission.

“Implemented” means source exists; “tested” requires actual execution. PASS applies only to the recorded version/environment. PENDING means evidence for the required person, version or location is missing; it does not automatically mean a defect.

| Evidence | Exact scope | Use |
| --- | --- | --- |
| R, report round | B worktree `6f862d78bb8458f90237252f4fc6d1629e7b6738`, production matching `04de0fe7abb9eb52ba7ae806beb30131d4b04a8e` | New 95-test run and numerical/geometry/contract audits; isolated memory/temp DBs, no browser rerun |
| H1, original acceptance | Combination `9ed9a4d92c46c0ffa2419ed8145ce4c9de53a26d`; A=`faa7ac16265b4a976c71361d7ee378a6abc27784`; template C=`78d39574266b01a582b0626c17021181749271c8` | Full playback, DEBUG map, three single-machine rehearsals, installation timing; source report `9049a556bc35cc714b1dcd9091ea5db36aea629d` |
| H2, stable persistent B | B=`04de0fe7abb9eb52ba7ae806beb30131d4b04a8e`; production optimization `d9a2e89` | 20-minute endurance/performance/restart; browser fault latency also with A=`98505588c643d55174acf399bb597ca8c9260ec0` |
| H3, recovery recheck | A=`dc69ad28ac37e8d0592d9271f9d61e28c79ff27c`, same pinned B/C; candidate `b48cac76e301a047afa330bced2eae6e388d534c` | Actual browser recovery, template Agent, decisions, failure injection, disconnect, restart, 500-event window and PNG |

[Machine-readable item evidence](evidence/B-final-acceptance-20261017.json) retains H1 source commit, evidence hashes, three-run measurements and installation steps. H2/H3 links appear below.

## Git and delivery state at the original snapshot

- Branch `codex/harborguard-backend-tick-performance`; pre-report HEAD=`6f862d7`, one unpushed B-test/docs commit ahead. Original DOCX untracked.
- Official remote: https://github.com/ChrisJiang123/harborguard.git. After fetch, `origin/main=f93af2caa6763ca41c00f05a5a9329939f0dbbe3`, including maintainer-merged PR #7. A head=`b549515337e0a50889d331ae397e4f381e4694ca`. Its three recovery-critical files differed from H3 only in English copy; two identity/deduplication issues remained. “Merged” did not mean “accepted”.
- main's `backend/app`, `backend/migrations` and `shared` matched stable B, but main then had only C0, without `agent/main.py` or the template implementation. It was not the verified complete A/B/C package; old template startup timings could not establish full-main startup.
- No complete browser/three-rehearsal rerun of that main. `origin/demo/mac-integration` was outside scope; new C routing was not automatically substituted.
- Four probes of `127.0.0.1:5173`, `:8000/api/health`, `:8003/api/health` and `:8001/health` returned ConnectTimeout. Existing demo availability was unconfirmed, not a backend test failure. No process, checkout or demo DB was changed. Start the selected pinned combination and check health before demonstrating.

## Original checklist, item by item

Each item gives the translated original requirement, source/test, actual execution, measurements, status and remaining action. Paths are repository-relative. R always means the 95-test B@6f862d7 run, with production matching B@04de0fe. Historical checks are not presented as new runs.

### B0–B1

#### B0–B1-1 PENDING

Original requirement: a teammate clones, runs `make backend`, and GET /api/health returns `{"ok": true}`.

- Source/tests: Makefile:backend; dev.ps1; backend/app/main.py; backend/tests/test_contract.py.
- Execution: R isolated in-memory TestClient health; H1 new local clone and three-service startup, not rerun. No teammate GNU make execution.
- Measurement: R health=`{"ok":true}`; H1 preinstalled startup 3.063s, new-clone startup 3.719s.
- **PENDING**: interface evidence exists; the required teammate clone/make record is absent.

#### B0–B1-2 PASS

Original requirement: a small Python /ws client receives about five state messages per second, with continuously increasing seq.

- Source/tests: backend/app/api/ws.py; bus.py; main.py; test_api.py::test_websocket_rate_sequence_and_disconnect_cleanup.
- Execution: R WS test; H2 actual 20-minute stable-B network run.
- Measurement: 1200.08s, 6001 states, 5.000Hz; H3 idle sample 4.991Hz; strictly increasing seq.
- **PASS**: events/state share seq, so states may skip numbers. Strictly increasing is not gapless. 5Hz is an average, not a hard-real-time guarantee for every frame.

#### B0–B1-3 PASS

Original requirement: tests/test_contract.py visits every appendix GET and validates responses with corresponding Pydantic models.

- Source/tests: backend/app/models.py; api/rest.py; test_contract.py::test_all_contract_get_endpoints.
- Execution: R named test and frozen-path checks within all 95 tests.
- Measurement: 21 REST = 13 GET + 8 POST; 12 JSON GETs Pydantic v2-valid; PNG GET actually decoded; 14 event types.
- **PASS**: PNG uses binary validation, not a JSON Pydantic model.

#### B0–B1-4 PENDING

Original requirement: A can directly use sample JSON with A's TypeScript types, confirmed by A.

- Source/tests: shared/sample_state.json; sample_events.json; types.ts; frontend/src/types/contract.ts.
- Execution: R assigned samples directly to StateMsg/EventMsg[]; `tsc --noEmit --strict --skipLibCheck --target ES2022`.
- Measurement: exit 0; two tracks, one L3 alert, three sample options, 14 event types.
- **PENDING**: compilation proves compatibility, not A's required explicit confirmation.

#### B0–B1-5 PASS

Original requirement: connected A has no browser-console CORS error.

- Source/tests: backend/app/main.py; config.ALLOWED_ORIGINS; test_contract.py::test_cors_and_static_data.
- Execution: R preflight; H1/H3 actual pinned-A browser/error checks. H1 used localhost:5173 cross-origin, H3 a same-origin proxy.
- Measurement: 5173 OPTIONS 200/correct allow-origin; no historical browser CORS block.
- **PASS** only for tested configurations. H3 proxy does not establish 5174 cross-origin permission or latest-main full acceptance.

### B2

#### B2-1 PASS

Original requirement: Shapely loads all polygons; every is_valid; unique zone IDs; symmetric neighbors.

- Source/tests: data/zones.geojson; backend/tests/test_data.py::test_polygons_metadata_and_symmetric_navigation_graph.
- Execution: R five data tests plus independent geometry/adjacency audit.
- Measurement: 12 unique valid polygons = six berth, four channel, two anchorage; zero asymmetric links or geometrically noncontacting neighbor pairs.
- **PASS** for schematic validity, not real-chart accuracy.

#### B2-2 PASS

Original requirement: entrance BFS through channels reaches every berth zone.

- Source/tests: decision/disaster.py::reopen; test_data.py::test_entrance_reaches_every_berth_through_channels.
- Execution: R channel-only entrance BFS, test_data/test_disaster.
- Measurement: all six berths reachable; disaster BFS uses only clear channels.
- **PASS**: blocked/unsurveyed channels are never traversed.

#### B2-3 PENDING

Original requirement: all ten buoys are inside/immediately adjacent to water polygons; visually verify on geojson.io that none is on land.

- Source/tests: data/buoys.json; test_data.py::test_buoys_are_in_schematic_water_and_assets_in_berths.
- Execution: R schematic Shapely containment and nearest-neighbor distances, no authoritative land/water visual check.
- Measurement: 10/10 inside schematic water; spacing 280.000–492.443m versus suggested approximately 500–800m.
- **PENDING**: A/B must jointly check a reliable basemap; do not move shared coordinates without approval.

#### B2-4 PASS

Original requirement: A's map displays business zones, three asset rings and buoys.

- Source/tests: frontend/src/map2d/* (A unchanged); data/*; test_data.py.
- Execution: H1/H3 actual 2D browser/layers and frontend A2 checks.
- Measurement: 12 zones, five assets/three rings, ten buoys; 40 schedule-record static copies matched.
- **PASS** for backend-sourced business-layer display, not real harbor chart/bathymetry acceptance.

### B3

#### B3-1 PASS

Original requirement: tested geo round-trip error <0.1m.

- Source/tests: backend/app/geo.py; test_simulation.py::test_geo_round_trip_has_sub_decimeter_error.
- Execution: R four round trips plus parameterized tests.
- Measurement: maximum 4.64408957473e-10m, far below 0.1m.
- **PASS**.

#### B3-2 PASS

Original requirement: a UUV reaches a 300m waypoint at 1.5m/s at t=200±1s.

- Source/tests: sim/targets.py::UUV; test_simulation.py::test_uuv_reaches_300m_waypoint_at_200_seconds.
- Execution: R, 1999+1 steps of 0.1s.
- Measurement: t199.9 → 299.85m; t200 → 300m and velocity zero.
- **PASS**.

#### B3-3 PASS

Original requirement: same seed twice yields exactly identical target positions at t120s.

- Source/tests: sim/scenario.py; world.py; test_simulation.py::test_scene_seed_is_repeatable_and_large_steps_match_fixed_steps.
- Execution: R two fixed-substep runs plus one 120s large step.
- Measurement: positions/velocities matched at t120; A seed42/B seed7.
- **PASS**: scenario-derived numpy Generator only, no wall-clock randomization.

#### B3-4 PASS

Original requirement: DEBUG_TRUTH_TRACKS=1 scenario A shows scripted target motion on A's map.

- Source/tests: engine.py::_truth_tracks; sim/targets.py; test_simulation.py.
- Execution: H1 separate DEBUG=1 backend and actual A browser, not rerun here.
- Measurement: seven truth tracks; T1 coordinates changed t1→t301, visible on map/card; 10m error ring and explicit DEBUG label.
- **PASS** for historical fallback display. Algorithms/endurance/ordinary Demo use DEBUG=0. Existing services were not restarted for DEBUG here.

#### B3-5 PASS

Original requirement: REST pause/resume/1×/4×/10×/reset work.

- Source/tests: backend/app/api/rest.py; engine.py; backend/tests/test_api.py::test_controls_faults_and_reset.
- Execution: R isolated REST speed/state checks, full pause/resume/reset/clock tests.
- Measurement: all three speed requests 200, values 1/4/10; paused positions/time fixed; reset t0/scenario=null.
- **PASS**: 10Hz outer loop; a 10× tick advances one simulation second through ten 0.1s substeps.

### B4

#### B4-1 PASS

Original requirement: three buoys observe a straight target; after 30s position RMSE <30m and velocity error <0.3m/s.

- Source/tests: perception/localize.py; kalman.py; test_perception.py::test_noisy_three_buoy_track_accuracy_velocity_and_id.
- Execution: R independent 61 samples at t30–90 plus full perception tests.
- Measurement: position RMSE 5.88507m; velocity RMSE 0.171037m/s; single T1; final ellipse a=7.21399m/b=3.48527m.
- **PASS** for the straight window after 30s, not full turning-scenario velocity performance.

#### B4-2 PASS

Original requirement: scenario A UUV retains one track ID for ≥90% from first detection to berth arrival.

- Source/tests: perception/tracker.py; perception/benchmark.py.
- Execution: H1 full A/1200 simulation seconds, truth only for scoring; H2 optimized-output consistency.
- Measurement: first t1, arrival t1066; T3=965/1066=90.5253%; T60=99 samples.
- **PASS**, narrowly before arrival. Full 1200s main-ID share 80.4167%. ID changes remain disclosed; denominator was not adjusted.

#### B4-3 PASS

Original requirement: ≤1 confirmed false track per five simulation minutes in A.

- Source/tests: sim/acoustics.py; perception/localize.py; benchmark.py; test_perception.py.
- Execution: R 300s false-alarm-only test; H1 four 300s windows over A.
- Measurement: zero confirmed false tracks per window, using >100m from nearest truth as the false-track scoring definition.
- **PASS** with explicit 100m scoring gate; actual false observations were generated and the count stayed ≤1.

#### B4-4 PASS

Original requirement: surface-vessel tracks are vessel and raise no alerts.

- Source/tests: perception/tracker.py::update; decision/alerts.py; test_perception.py::test_ais_only_uses_nearby_vessels.
- Execution: R AIS/alert exclusion; H1 once-per-second confirmed-broadband nearest-vessel scoring.
- Measurement: all 3793 samples inside the 100m scoring gate were vessel/L0, zero violations.
- **PASS**: production AIS 50m gate unchanged; AIS must not override narrowband UUV.

#### B4-5 FAIL

Original requirement: at 10Hz, every tick processes in <20ms.

- Source/tests: backend/app/engine.py::step; perception/classifier.py; backend/tools/benchmark_ticks.py; backend/docs/performance-followup.md.
- Execution: H2 exclusive optimized full A/B 10× offline benchmarks/20-minute run with real synchronous persistence/numerical flow; separate pinned-B/C peak diagnosis. No new performance run or algorithm change here.
- Measurement: A outer mean 19.6448ms/P95 27.0585ms/max 61.0667ms, 446/1200 over 20ms; B max 113.8246ms; endurance log max 120.8ms.
- **FAIL** against the original strict threshold, now non-blocking best effort per lead. Preserve statistics; distinguish substeps, outer ticks, PNG and persistence.

### B5

#### B5-1 PASS

Original requirement: all five hand-computed risk cases pass.

- Source/tests: decision/risk.py; config.W; test_decision.py::test_risk_five_hand_computed_cases.
- Execution: R five cases plus behavior/ETA tests.
- Measurement: C=0.6/0.2/0.05/0.92/0.2; R=0.47/0.35/0.305/0.566/0.35.
- **PASS**; C/P/B/Z/D weights 0.30/0.25/0.25/0.15/0.05 unchanged.

#### B5-2 PASS

Original requirement: R oscillating around 0.4 does not repeatedly toggle level.

- Source/tests: decision/alerts.py; test_decision.py::test_alert_hysteresis_and_deleted_track.
- Execution: R 0.39/0.41 oscillation and continuous-low tests.
- Measurement: low t1, recovered t10, low t20; L2 at49, L1 at50; deleted track emits cleared.
- **PASS**: immediate upgrade, 30 continuous simulation seconds for downgrade.

#### B5-3 PASS

Original requirement: A10× reaches L1≤5 wall seconds, L2 in15–25s, L3 in40–50s by scene-start/velocity tuning.

- Source/tests: decision/alerts.py; data/scenarios/scenario_a.yaml; test_integration.py.
- Execution: R numerical regression; H2 actual Uvicorn HTTP/WS wall timing; H1 three template rehearsals.
- Measurement: stable B L1=3.720s/L2=15.069s/L3=48.339s; H1 L3=49.016/48.407/48.406s.
- **PASS** for those baselines; actual wall time, not t/10. Different-baseline earliest L1 times remain separate. Later real-model 505s limitation is disclosed above.

#### B5-4 PASS

Original requirement: after L2 ping, detection includes image_url; opening PNG shows boxes.

- Source/tests: decision/pinger.py; perception/classifier.py; test_decision.py::test_active_sonar_fallback_png_and_all_outbound_event_models.
- Execution: R classifier/PNG/events including C-import/malformed-output fallback; H3 actual browser images/boxes.
- Measurement: ping t150.7; PNG640×640 decoded; all four Recovery empty-track_id images opened.
- **PASS** for allowed fallback, Detection.model=stub; not YOLO/real-sonar accuracy acceptance.

#### B5-5 PASS

Original requirement: within one simulation second after L3, options_ready has ≥2 local options plus full-port closure; baseline berths_open_pct=0 and maximum vessel-hour delay.

- Source/tests: decision/optimizer.py; test_integration.py::test_security_scene_timing_options_and_manual_approval.
- Execution: R full A/optimizer; H2/H3 actual L3/options; first-L3/event comparison.
- Measurement: same substep t483.1; three local + one full; baseline open0/delay162 vessel-hours; smallest local6 vessel-hours.
- **PASS**; suggestions only, restricted requires human approve.

#### B5-6 PASS

Original requirement: approve makes corresponding state.zones restricted.

- Source/tests: decision/__init__.py::approve; api/rest.py::decision; test_api.py::test_decision_endpoint_requires_valid_human_approval.
- Execution: R API/decision/SQLite rollback/restart; H3 actual UI approve/reject/write failure, refresh/same-DB restart.
- Measurement: A11/opt-1 UI approve seq3064, five restricted; reject seq887; write failure503/no successful decision.
- **PASS**. Lead later required the existing decision event/persistence for reject, without adding shared fields. Reject does not undo approve; A's operator edge is I02.

#### B5-7 PASS

Original requirement: marine-mammal no-ping rule has unit tests.

- Source/tests: decision/pinger.py::safe; test_decision.py::test_mammal_ping_prohibition_limit_and_duration.
- Execution: R 500m protection, call cue, online buoys, 20s/five pings/1.5s tests.
- Measurement: no protected ping; allowed outside; timing/count assertions passed.
- **PASS** for simulation, not hardware emissions.

### B6

#### B6-1 PASS

Original requirement: B zones become clear/unsurveyed/blocked within60 wall seconds; after t60 buoy fault ≥1 zone remains unsurveyed.

- Source/tests: decision/disaster.py; scenario_b.yaml; test_integration.py::test_disaster_scene_faults_detection_and_connected_reopening.
- Execution: R complete numerical B; H1 three actual600-simulation-second B10× runs; H3 browser smoke.
- Measurement: first blocked0.141/0.156/0.172s; first clear1.844/1.828/1.860s; B4/B7 fail t60; historical final six clear/four blocked/two unsurveyed.
- **PASS** historically; three states within60s, full600s took59.938–60.031s. Debris does not use Security alerts. Later real-model counts must not be overwritten with these historical counts.

#### B6-2 PASS

Original requirement: reopen_plan gives ≥1 route and ≥1 eligible berth.

- Source/tests: decision/disaster.py::reopen; test_disaster.py::test_bfs_requires_continuous_clear_channels_and_adjacent_clear_berths.
- Execution: R BFS/full B/independent assertions; H3 actual browser.
- Measurement: channel_entrance + channel_main_s; berth_container_1; SURVEY_H=1.5h gives9h.
- **PASS** for taskbook formula, not real survey labor or economic savings.

#### B6-3 PASS

Original requirement: same seed twice yields identical event-name + t sequence.

- Source/tests: backend/tools/record.py; test_integration.py::test_full_replay_deterministic_and_self_contained.
- Execution: R recorded A/B twice each in separate pytest temp directories; checkpoint reproducibility tests.
- Measurement: event-name+t and JSONL byte SHA256 matched; PNG decoded; frontend/public untouched.
- **PASS**. Offline clock does not depend on random external-Agent latency.

#### B6-4 PASS

Original requirement: each injection is visible on A within3s.

- Source/tests: engine.py::inject; sim/world.py::inject; frontend/src/panels/BuoyGrid.tsx/TopBar.tsx.
- Execution: H2 actual A9850558+B04de0fe+C78d3957 browser, ab-integration-9850558.json. Not rerun here; R B unit tests only.
- Measurement: buoy_down383ms/up382ms; network_down383ms/up378ms; noise_up≤191.521ms/down≤214.135ms.
- **PASS**, including observation overhead; noise REST→frontend log. Simulated network does not prove Wi-Fi/LoRa/ESP32 offline. Latest main was not retimed.

#### B6-5 PASS

Original requirement: replay_a.jsonl/replay_b.jsonl play completely in A.

- Source/tests: backend/tools/record.py; frontend/src/data/replay*.ts (A unchanged); test_integration.py.
- Execution: H1 A@faa7ac1 actual0-to-end1×; H3 A@dc69ad2 seek/read-only/PNG only; R double recordings/full messages/images.
- Measurement: A120000ms/B60000ms; A20:00 L3/B10:00 reopening9h; H3 replay approval disabled/local debris PNG640×640.
- **PASS** only for versions with full-playback evidence. Latest-main full browser playback remained PENDING; seek is not complete playback.

#### B6-6 PASS

Original requirement: invalid POST /api/recommendations returns422; valid data broadcasts.

- Source/tests: models.py::Recommendation; engine.py::recommend; test_contract.py::test_recommendation_validates_references_and_broadcasts.
- Execution: R schema/reference/transaction tests: invalid structure/evidence/optionIDs422, valid broadcast/write rollback; H3 actual C template.
- Measurement: rec-d89ea3415187 and rec-e3714ebee774; alerts/options queryable; advice survived delayed recovery.
- **PASS**; C never approves. Template lacked disaster/buoy triggers; new routing unaccepted here.

#### B6-7 PASS

Original requirement: absent Agent gives clear /api/agent/ask error; B stays alive.

- Source/tests: api/rest.py::ask; test_api.py::test_agent_proxy_success_failure_timeout.
- Execution: R MockTransport success/502/504; H1 actually stopped its own C. No other service stopped here.
- Measurement: actual absence502 in2.375s/B healthy; 20s timeout branch MockTransport504.
- **PASS**, distinguishing actual absence from simulated timeout.

### B7

#### B7-1 PASS

Original requirement: A/B three runs each, key-event timing variation <3s.

- Source/tests: data/scenarios/*; H1 observer/machine-readable rehearsals.
- Execution: H1 three actual-browser single-machine rehearsals, not current-main reruns or three-person onsite.
- Measurement: totals260.235/135.594/201.187s; L3 range0.610s; B completion range0.093s; all key variation<3s.
- **PASS** historically; one observer-backpressure attempt/retry disclosed. Onsite/latest-candidate rehearsals awaited.

#### B7-2 PASS

Original requirement: continuous20-minute run without errors and with stable memory.

- Source/tests: backend/tools/soak.py; backend/app/main.py; backend/docs/evidence/soak-history.json.
- Execution: H2 actual1200s Uvicorn/HTTP/WS/CPU/RSS plus DB restart after persistence/optimization; not latest ABC endurance; not rerun here.
- Measurement:1200.08s/6001 states/1139 events/5.000Hz/max26618bytes; CPU mean15.751%/30s max24.0%; RSS94.89–104.14MB; zero errors.
- **PASS** for that machine/duration. Memory fell on switching; no sustained growth. Stable RSS does not mean DB disk history stops growing.

#### B7-3 PENDING

Original requirement: teammate follows README and starts the whole system from zero in <5minutes.

- Source/tests: README.md; backend/README.md; dev.ps1; H1 docs/demo-runbook.md.
- Execution: H1 new local clone/independent venv/node_modules/install/build/three services; not a teammate's fresh computer, not rerun here.
- Measurement: cached install/build32.922s + startup3.719s =36.641s; preinstalled3.063s.
- **PENDING**: not empty-cache/no-runtime/new-computer/teammate acceptance. Then-main lacked template C, so old timings cannot transfer.

#### B7-4 PENDING

Original requirement: `make test` all green.

- Source/tests: Makefile:test; dev.ps1:test; pyproject.toml.
- Execution: R equivalent `python -m pytest backend/tests -q`, Ruff/compileall/pip check/sample TS; H3 B+C. Literal GNU make unavailable. Original report described the then-default testpaths as backend/tests.
- Measurement:95 passed/0 failed/0 skipped,63.17s; one upstream TestClient deprecation warning. Historical B+C120 passed/2 skipped,68.57s.
- **PENDING** only for literal GNU make. Equivalent Windows workload passed. Missing-weight skips are not passes and cannot simply be added to95.

## Module summary

| Module | PASS | FAIL | PENDING | Boundary |
| --- | ---: | ---: | ---: | --- |
| B0–B1 |3|0|2| Service/interfaces/push passed; teammate clone/make and A sample confirmation pending |
| B2 |3|0|1| Schematic geometry/connectivity valid; real land/water/deployment unverified |
| B3 |5|0|0| Simulation/seeds/controls passed; DEBUG map was historical specialized evidence |
| B4 |4|1|0| Numerical quality passed; original20ms missed, hard gate removed |
| B5 |7|0|0| Risk-to-human-action flow passed; no real-recognition accuracy acceptance |
| B6 |7|0|0| Backend/historical combinations passed, version-limited playback/injection evidence |
| B7 |2|0|2| B endurance/old triple single-machine rehearsal passed; teammate/GNU make pending |
| Total |31|1|5| Not full original37-item acceptance; not latest-main all-green |

Five PENDING: B0–B1-1, B0–B1-4, B2-3, B7-3, B7-4. B7-4 preserves the literal GNU make boundary; equivalent95 Python tests passed. This does not mean five unimplemented backend features. Three-person onsite rehearsal and latest-package reacceptance remain separate integration requirements, not hidden by narrowing the checklist.

## Additional persistence and interface acceptance

These later lead requirements were not original checklist items.

| Capability | Result at the report snapshot | Evidence / limit |
| --- | --- | --- |
| SQLite recommendations/decisions/events/PNG/runtime | PASS,B | storage.py,checkpoint.py,migrations/001_history.sql;18 history cases included in95 |
| Structured approve/reject and atomic writes | PASS,B | Success/broadcast only after commit; real SQLite failure503/no successful decision; H3 UI retry passed |
| Same-DB service restart | PASS,tested combination | seq continued, safely paused; decisions/restrictions/details/advice survived; H3 seq1421→1519 |
| Internal archive beyond500 | PASS,B | R526+events/restart; H3 archive596events/3decisions while public window stayed500 |
| Public full recovery beyond500 | PENDING,contract | /api/events filters latest500; no paging/count/truncation flag; persistence does not enable enumeration |
| Older known-ID details/PNG | PASS,B,limited | Current object first, historical fallback; /alerts/{id} has no decision status and is not a decision-query endpoint |
| Real-time logs/template advice during REST recovery | PASS,H3 | New log survived old-options3s delay; actual template recommendation survived events5s delay; original race fixed |
| Actual WS disconnect/compensation/deduplication | PASS,H3 order tested | Only browser WS closed; B/C continued; three offline logs recovered once/in order, not network_down standing in for disconnect |
| Actual seq rollback/new-session protection | PASS,H3 | Switched to new QA DB, old UI approval cleared; old DB retained. DB replacement is not ordinary restart history loss |

REST retained21operations,14events and original fields; Pydantic v2/TypeScript samples verified. State/event share seq, so require strict increase, not consecutive states differing by1. State has no recommendation/approval fields; structured decision events are authoritative. /api/log returns latest1000/newest first; start/reset clears current logs. Never infer decisions from free text. v1 has no decision idempotency key/terminal-state definition; legitimate repeats can have different seq. Reject does not revoke approve.

The original taskbook said reject writes only logs. The lead later explicitly requested structured publication within the frozen contract's existing decision/action=reject definition. B implemented that definition without new fields/events/statuses. Full-history pagination remained a [proposal](history-handoff.md), not an unapproved implementation.

## Integration issues open at that snapshot

### I01: legitimate duplicate logs collapsed — FAIL, A

H3 posted the same log twice at one paused time. B produced valid seq143/144; LIVE showed two, refresh one. frontend/src/store/useHarbor.ts logIdentity/mergeRecoveredLogs used a t/level/source/text Set, collapsing distinct records. A should deduplicate structured events by seq and preserve multiplicity when REST logs lack IDs. Test same-event redelivery→one versus two legitimate identical posts→two. Added B persistence tests proved both survive restart; frontend was unchanged.

### I02: decision operator ignored newer event — FAIL, A

At t484, H3 approved A1/opt-1 as QA_REMOTE then QA_REMOTE_2. B persisted/broadcast second seq1520; log showed second operator, card still first until refresh. Frontend decision key omitted seq/operator. Retain generation/session protection but identify decisions by durable event.seq; distinct seq must not disappear for equal action/time. Add same-time two-operator and same-seq-redelivery tests; no B contract change needed.

### I03: main lacked pinned template Agent — final-package blocker, C/lead

Then-main contained C0 without verified template/renderer. The report did not substitute new cloud/Ollama routing. Lead should choose inclusion of78d3957 and test an independent delivery branch. B did not merge main or overwrite C.

### I04: history window and external acceptance

Full-history pagination awaited contract approval. Real land/water, bathymetry/tides, sonar/weights, onsite projector/video, physical Wi-Fi disconnect/hardware offline, teammate from-zero startup and three-person rehearsal were incomplete. Permitted stub/template fallback does not establish real recognition/hardware performance.

I01/I02 blocked complete recovery/decision-edge consistency claims. H3 passed a controlled single-operator, one-decision, within-window demo.20ms and approximately995KB3D chunk were non-blocking optimization. Neither dismiss the tested main flow nor hide boundaries to claim all-green.

## Performance and stability

| Metric | Measurement / scope | Judgment |
| --- | --- | --- |
|5Hz|H2 actual1200.08s/6001states/5.000Hz,maximum26618bytes|PASS there; below50000bytes|
|CPU|H2 single-core30s-window mean15.751%,max24.0%|Below50%; not instantaneous-peak guarantee|
|RSS|H2 backend/Python children94.89–104.14MB, fell after switching|No sustained20-minute growth, not unlimited leak-free proof|
|Outer tick|A mean19.6448/P95 27.0585/max61.0667ms;B max113.8246ms|Original20msFAIL; hard gate removed|
|Image peaks|A classifier max46.868ms;B initial four classifiers≈110.29ms total|Mostly image path; no Kalman/risk change|
|Substep|0.1simulation second;ten per10×outer tick|Updated full-substep P95/max not independently measured; outer/10 is not proof|
|Disk|H2≈111.5MiB,events/PNG retained|Future retention needed; no deleting history to lower metrics|

Lowest-risk next step was stable B plus A recovery/package startup. Sonar-grid caching belonged to C; async PNG changes availability, atomicity, RNG/replay and was not an unconfirmed competition patch. No new optimization/statistics change in this report round.

## Single-machine rehearsal and startup evidence

H1 used the old pinned combination. A/C were not onsite; this was not three-person acceptance.

| Run | Total seconds | L1/L2/L3 wall seconds | Template advice | Recovery completion | Result |
| --- | ---: | --- | ---: | ---: | --- |
|1|260.235|0.063/15.094/49.016|49.110|60.031|Actual UI approval,2D/3D,Recovery,replay passed|
|2|135.594|0.110/15.125/48.407|48.453|60.031|Same; replay seek, complete playback separate|
|3|201.187|0.109/15.140/48.406|48.468|59.938|Same|

Three successful flows needed no application-level retry. An additional incomplete run2 attempt hit observer backpressure/keepalive timeout because WS was not continuously consumed; observer fixed, run repeated. Three successes does not mean every attempt was error-free. H3 added two actual A loops/Recovery after persistence, without inventing three updated full rehearsals.

H1 cached-machine new-clone install/build32.922s plus startup3.719s=36.641s; preinstalled3.063s. Not empty-cache/new-computer/teammate acceptance. Then-main lacked C and four service probes timed out, so these timings did not prove that main's startup.

## Recheck commands and five-minute demo

These are instructions, not restarts/installations/recordings/merges executed by the report. Choose a separate worktree with pinned B/C and tested A; do not invoke Agent from a C-incomplete main.

```powershell
# Selected demo worktree, Python3.11+ and local virtualenv already available
$env:HARBORGUARD_DB = 'C:\HarborGuard\demo\history.sqlite3'
$env:DEBUG_TRUTH_TRACKS = '0'
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000

# Second terminal, pinned C source/dependencies ready; template needs no cloud keys
$env:BACKEND_BASE_URL = 'http://127.0.0.1:8000'
$env:BACKEND_WS_URL = 'ws://127.0.0.1:8000/ws'
.\.venv\Scripts\python.exe -m agent.main

# Third terminal, A dependencies and build ready
npm.cmd --prefix frontend run preview -- --host 127.0.0.1 --port 5173
```

Create a writable DB parent first; one worker per DB, retain DB for recovery. Check8000/8001/5173; do not kill unknown processes. Check frontend API/WS build addresses. Historical QA8003/8006/5174 are not frozen production addresses.

```powershell
# Workload actually passed here; use a new unused temporary directory
.\.venv\Scripts\python.exe -m pytest backend/tests -q --basetemp artifacts/B-acceptance-next
.\.venv\Scripts\python.exe -m ruff check backend/app backend/tools backend/tests
.\.venv\Scripts\python.exe -m compileall -q backend
.\.venv\Scripts\python.exe -m pip check
```

Before presenting: B health=ok, C health explicitly template, frontend LIVE, both local JSONLs/PNGs present. Sequence for that historical fallback baseline:

1. 0:00–0:20: disclose synthetic harbor/stub/template/human final approval; LIVE,2D assets/buoys.
2. 0:20–1:20: Security10×,L1→L2→PNG→L3/options, historically≈49s. If late inspect speed/pause/health; never fabricate events.
3. 1:20–2:10: local/full-port options, real template advice, one operator approves once; check restricted, pause/refresh within-window recovery.
4. 2:10–2:40: 3D→2D; water/DEM are demo references, not verified bathymetry.
5. 2:40–3:50: Recovery10×,debrisPNG,B4/B7faults,clear/blocked/unsurveyed,BFS/historical9h assumption.
6. 3:50–4:40: explicitly read-only Replay; disclose key-frame seek, not new full-playback acceptance. Preserve failures before fallback; never clear DB to conceal them.
7. 4:40–5:00: verified abilities/remaining boundaries; stop recording.

## Objective coverage

| Original objective | Verified capability | Limit |
| --- | --- | --- |
|LA underwater-security digital twin|Schematic zones/assets,acoustic observation,localization,Kalman,three risk levels,PNG|Not real survey/sonar-performance acceptance;post-arrival ID changes|
|Quantified local human response|Local/full-port options,berths/delay/residual risk,approved restrictions,rejection record|Demo formulas;two A deduplication edges open|
|Disaster reopening|Coverage,debris,buoy faults,clear-channel BFS/eligible berths|Not real disaster survey;9h is an assumption|
|Reproducible/offline fallback|Fixed seed,message/PNG consistency,twoJSONLs,read-only replay|Public>500history contract-limited;no hardware/physical-disconnect proof|
|Team competition delivery|Pinned-template flow,three historical single-machine rehearsals,95Btests|Then-main lackedC;onsite/newcomputer/finalvideo incomplete|

These fit B's MVP direction but do not replace official competition rules or whole-team acceptance. The taskbook allowed labeled stub fallback while C rendering/model work was unavailable. Allowed B fallback acceptance differs from real AI-recognition quality acceptance.

## Delivery judgment and ownership

**B taskbook not fully passed; stable B supplied a testable, integrable MVP.** Controlled recording could use the pinned combination. Then-main lacked C, two A consistency edges failed, service availability was unconfirmed; not unconditionally ready for onsite demo/final submission. Devpost materials could be prepared, but official criteria, final package, cross-device playback and team sign-off still needed checks. No submission/organizer acceptance claimed.

- A: frontend-only I01/I02 fixes, retaining generation/delay protection; new-SHA same-text logs/same-time operators/real refresh/reconnect; projector/video readability.
- B: preserve stable95-test implementation, independently combine A fixes/newDB, jointly verify geometry; history paging/coordinates only after lead approval. No repeat approval for authorized routine work.
- C: arrange pinned78d3957 inclusion/renderer/dependencies/health; accept new routing separately; show stub if weights unavailable; Agent never approves.
- Lead: decide minimal history proposal/finalSHA; arrange onsite/team startup acceptance. PR#7 was maintainer-merged; report performed no main/remote modification.

## Reviewable evidence

- [Item data](evidence/B-final-acceptance-20261017.json)
- [Stable B performance](performance-followup.md),[20-minute summary](evidence/soak-history.json)
- [Peak diagnosis/updated20ms](demo-stability-followup.md),[breakdown](evidence/peak-analysis-20261017.json)
- [Actual-process persistence](history-verification.md),[history/decision fixture/contract](history-handoff.md)
- [A9850558 browser integration](ab-integration-9850558.md),[six injections](evidence/ab-integration-9850558.json)
- [Adc69ad2 recheck/A suggestions](pr7-recovery-dc69ad2.md),[seq/timing/results](evidence/pr7-recovery-dc69ad2.json)

Older H1 report was local at `codex/harborguard-b-final-acceptance@9049a556bc35cc714b1dcd9091ea5db36aea629d`; inspect `git show <SHA>:docs/B-final-acceptance.md` and docs/B-acceptance-evidence.json. Its reject-only-log/no-persistence/20ms-hard-gate/old-A-race statements described that earlier state. Use explicit H2/H3 updates rather than mixing conclusions.

Full JUnit,geometry/numerical audit,original-text extraction and TS inputs remained in ignored artifacts/B-acceptance-20261017/. Original reporting added only this report and smallJSON evidence, no DB/cache/log/key/taskbook attachment. English translation retains raw evidence unchanged.
