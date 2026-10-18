# Historical Backend MVP Verification

The 73-test/stub results below belong to the initial MVP, not current main. By 2026-10-17 main included B #10, C #4, A #11. Newer results: [integration report](final-integration-report.md), [machine record](final-integration-results.json), [sonar safety](../backend/docs/sonar-safety-integration.md). 20 ms is now best effort; real-YOLO level 3 at 505 s still FAILS the original 500 s requirement.

Validated on Windows, CPython 3.11.17 and requirements-lock.txt. DEBUG_TRUTH_TRACKS was off. C renderer/weights/Agent were not then available; detection was explicitly stub.

## Automated checks

- All 73 tests passed after incorporating the remote C0 skeleton; latest dev.ps1 test took 55.19 s. Includes token-for-token C/B contract matching and null metrics for NaN.
- Ruff: all backend Python passed; compileall: all backend Python compiled.
- pip check: no conflicts. PowerShell setup/check/record ran successfully.
- Fresh Python 3.11.17 venv, locked dependencies and editable install: 30.41 s. Real-service smoke test ~5.04 Hz. This measured B installation on this computer, not full A/C startup.
- Sample JSON assigned as TypeScript literals to original StateMsg/EventMsg[] passed tsc --noEmit --strict --skipLibCheck.
- 13 GETs (including PNG), 8 POSTs, 14 event types, WS state/events validated. JSON passed frozen models; PNGs decoded to 640×640.
- Real Uvicorn without Agent returned 502 and a clear error; health stayed ok. MockTransport verified 20 s timeout→504.
- One upstream httpx TestClient deprecation warning; tests passed. Runtime does not require TestClient.
- Windows lacked GNU make. Equivalent Python commands/dev.ps1 were used; Linux/macOS make commands were not run here.

## Scenario A

Seed 42, 1200 simulation seconds, speed 10, anonymous acoustic observations and the actual tracking chain.

| Metric | Measured |
| --- | --- |
| First L1 | t=1.0 s, ~0.10 wall s |
| First L2 | t=150.7 s, ~15.07 wall s |
| First L3 | t=483.1 s, ~48.31 wall s |
| First options | Same simulation instant; 3 local options + port-closure baseline |
| Dominant track ID from first detection to asset arrival | 90.53%, 965/1066 one-second samples |
| Full-scenario position RMSE | 12.24 m |
| Anonymous confirmed false tracks per 300 s | 0 / 0 / 0 / 0; offline criterion >100 m from every truth target |
| UUV incorrectly inheriting AIS vessel | 0 |
| Max state | 26620 bytes, below 50 KB |
| 0.1 s numerical-substep P99 | 5.26 ms |
| Longest substep | 36.88 ms near sonar-image encoding |

Taskbook three-buoy straight-line test passed position RMSE <30 m and speed error <0.3 m/s after 30 s. Full scenario includes turns/stops and speed RMSE=0.454 m/s; the straight-line threshold does not apply to turns.

IDs still change during the stationary post-arrival segment; including all 1200 s gives ~80.4% dominant ID. The specified first-detection-to-arrival window is 90.53%. Some substeps exceed 20 ms, so an every-substep guarantee was not met. Normal computation and 10 Hz/5 Hz demo pacing worked.

Raw reports: perception_metrics_a_600.json and perception_metrics_a_1200.json.

```bash
python -m backend.app.perception.benchmark --seconds 1200 --out docs/perception_metrics_a_1200.json
```

## Scenario B

Seed 7, 600 simulation seconds, speed 10. All four debris objects were detected at t=0.1; B4/B7 failed at t=60. Historical stub result: 6 clear, 4 blocked, 2 unsurveyed. Entrance/southern main channel and container berth 1 could reopen. The taskbook assumption of 1.5 h per zone yielded 9 h saved. Debris did not raise security alerts. These are old stub results, not newer real-model conclusions.

## Replays

| File | Messages | State frames | Duration | Max state |
| --- | --- | --- | --- | --- |
| replay_a.jsonl | 722 | 601 | 120 wall s | 26117 B |
| replay_b.jsonl | 335 | 301 | 60 wall s | 2032 B |

Two complete recordings per seed had identical event/time sequences and identical JSONL SHA256. All static sonar URLs mapped to decodable PNGs; an isolated static HTTP service served both JSONL files and all 18 images. With live checks, each scenario ran at least three times without key-event timing changes. A's replay player was not yet available, so full browser playback remained for A.

## Real-time endurance

Command: python -m backend.tools.soak --seconds 1200 --port 8000 --report artifacts/soak.json. Real Uvicorn cycled A/B, resets, and six faults. RSS/single-core CPU included Windows venv launcher and Python child. Occupied ports are refused; only the tool's process tree is cleaned up.

20-minute run passed: 1200.13 s, 6001 states, 1142 events, 5.00 Hz average, 14 scenario starts, zero service ERRORs. Max state=26125 B. Total Python RSS=88.18–100.88 MB, returning to ~93–101 MB after warmup across scenario changes; no sustained monotonic growth observed. Peak sampled single-core CPU=17.5%, below 50%. Raw samples: soak_metrics.json.

At 10× an outer wall tick advances 1 simulation second through multiple 0.1 s substeps. There were 289 >20 ms tick warnings, max 145.4 ms, mainly image generation/initial debris detection. Every tick <20 ms therefore did not pass; average delivery frequency and stability passed.

After this B-only soak, the branch incorporated origin/main's C0 skeleton. All 73 tests passed again; a 15 s real-service smoke test measured ~5.03 Hz. Git comparison confirmed C agent/ml/scripts/dependencies/docs/shared-contract-v1.md unchanged, with original root README retained and B entry appended.

## Team acceptance still needed at that historical stage

Real port geometry/land-water checks; A map/buttons/replay/reconnect; C YOLO/Agent/Ollama failover; three-person rehearsals; full five-minute cold startup. See acceptance.md. Unavailable teammate modules were outside the local-pass claim.
