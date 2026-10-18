# Taskbook Acceptance Scope

Taskbook B is the primary development basis. The initial goal is a locally runnable, testable MVP with integrable interfaces. Implementation, code verification, and acceptance requiring teammates, people, or external systems are distinct.

2026-10-17 update: historical main `782d04d` includes A #7/#11, B #10, and C #4. See the [complete B report](../backend/docs/B-final-acceptance.md) for all 37 original checkboxes and historical evidence, [sonar safety](../backend/docs/sonar-safety-integration.md) for real-model limits, and the [integration report](final-integration-report.md) for handoff migration tests. Implemented does not automatically mean accepted.

| Stage | Implemented backend capability | Remaining team/external acceptance |
| --- | --- | --- |
| B0–B1 | 21 REST operations, 14 events, Pydantic v2, CORS, 5 Hz target, 500-event window, same-database persistence; in main | New-main browser regression; all-history pagination remains unapproved/unaccepted. A 500-event cache is not complete history |
| B2 | 12 valid zones: 6 berths, 4 channels, 2 anchorages; bidirectional graph, 5 assets, 10 buoys, 40 vessel schedules, centralized parameters, frontend static copies | Demonstration geometry has not been validated against real charts, land/water boundaries, or deployments; A map display |
| B3 | Seeded scenarios, five target types, fixed-step motion, WGS84 conversion, pause/resume/speed/reset, truth fallback | A map-motion acceptance |
| B4 | Anonymous acoustic measurements, forward intersections, SNR consistency rejection of false multi-vessel intersections, clustering, Kalman, Mahalanobis association, confirmation/deletion, AIS, history/prediction | Physical sonar and real-sea performance are outside this demo's validation |
| B5 | Five-factor risk, three alert levels/hysteresis, mammal protection, PNGs, option optimization, structured persistent approve/reject; delivered YOLO tested separately on synthetic images | Real-model level 3 occurs at 505 s, exceeding the original 500 s limit; real-sea recognition and new-main browser decisions pending |
| B6 | Conservative disaster decisions, bounded retries, BFS, faults, replay tools, Agent validation/broadcast; template HTTP/WS verified in an isolated candidate | Real YOLO leaves the fuel berth unsurveyed; latest LIVE differs from old replay; cloud/local models need separate acceptance |
| B7 | Regression, explicit model labels, state-size bounds, isolated startup/five-minute runbook; 20 ms is best effort | New-model 20-minute endurance, three full-team rehearsals, target computer, first-install timing; average 5 Hz does not establish every latency/interval bound |

B supplies options/state. Security restricted zones require operator approve. Disaster clear/blocked/unsurveyed are simulated survey conclusions and do not automatically close a real port. Fallback detections are labeled model=stub; offline recommendations model=template.
