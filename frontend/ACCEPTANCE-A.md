# HarborGuard A — Frontend Acceptance Recheck

Date: 2026-10-18 (Asia/Shanghai). Scope: `frontend/` only.

**Conclusion: the frontend supports a conditionally accepted synthetic demo; A6 is NOT fully accepted.** This is a review of implementation and execution evidence, not a claim that every original taskbook checkbox or field sign-off has passed. No recording was performed, per the user's cancellation.

Latest revision: [proposed sonar placement and ~1 m local display](SONAR-DEPLOYMENT.md).
Its automated checks are separate from earlier browser evidence: local browser
control is currently disabled in Work settings, so this revision has no new
visual/FPS acceptance. Existing live/recorded coordinates are not remapped.

## Version and evidence boundaries

- Feature branch: `feature/3d-vertical-relief`, following vessel-motion commit `051d3f1`. This report now includes the multibeam changes; the committed changeset SHA is the reproduction reference.
- Remote main inspected: `8613834` (PR #9). The feature branch retains its own unpushed frontend work; inspecting main did not merge or overwrite it.
- Build, frontend tests, mock generation, and the local production browser preview were exercised. Backend/Agent processes, database, frozen contract, backend tests, and B/C source were not changed or started by A.
- B's [versioned acceptance report](https://github.com/ChrisJiang123/harborguard/blob/8613834/backend/docs/B-final-acceptance.md) contains its own historical A/B/C integration evidence. Those tests were not rerun by A in this iteration and are not evidence that current services are online.

## Frontend acceptance matrix

| Area | Verified evidence | Remaining boundary |
| --- | --- | --- |
| A1 state and controls | Automated cadence, event timing, pause/resume/speed/reset, source labels, recovery generation/session/log-merge races | Current live backend reconnect/restart not rerun |
| A2 2D | Coordinate/GeoJSON/selection tests; browser switched from selected T3 in 3D to 2D and back, preserving selection and the shared source | No new real chart, official zone, or field position acceptance |
| A3 alerts, Agent, approval | Automated source-event state, option/approval/rejection errors, dedupe, unknown-state fallback; synthetic UI and recorded approval | No new real Agent, real recognition, or live human-approval round-trip verification |
| A4 3D | NOAA H12617 MBES 1–2 m BAG ingestion, ~8 m harbor / ~1 m local display, source hashes, NoData, edge-opacity and aligned LOD tests; proposed sonar consistency/route offset tests | Latest visual/FPS check blocked by Work browser setting; earlier 2 m evidence in MULTIBEAM-VALIDATION.md; historical survey, datum, tide and field acceptance pending |
| A5 replay | New deterministic T3/T4 source reused by mock and three regenerated replay fixtures; arbitrary seek, pause/resume, reset and prediction tests | Synthetic files are not B backend recordings; no new long live replay/soak acceptance |
| A6 presentation | Build/lint/A1–A6/recovery/English/vessel checks pass; 1920×1080 browser inspection exists | NOT fully accepted: sustained target-device FPS, projector/3 m readability, current A/B/C and field sign-off pending; backup recording excluded this run by user instruction |

## Vessel realism changes and measured model checks

- Replaced asset-relative sine sweeps with two hand-authored Los Angeles harbor reference routes. Both are on the bundled NOAA water mask; start offsets place the boats underway so channel bends are visible in the short demo without accelerating the underlying physical model.
- Rounded waypoint corners, arc-length timing, curvature-dependent speed limits, acceleration capped at 0.035 m/s², deceleration capped at 0.045 m/s². Cruise ceilings: T3 3.6 m/s, T4 3.8 m/s. Final destination is a zero-speed hold with the last course retained, not an instantaneous north-facing stop.
- Velocity components, reported speed/course, actual motion, past positions and future positions come from one deterministic sampler. Histories: at most 60 points, 2 s spacing. Prediction: 10 points at 10 s spacing. Pause/resume and tick chunk size do not alter the path; 2D/3D do not maintain separate simulations.
- Opposing reference lanes use a 40 m starboard offset each. This is a presentation choice, NOT an official traffic-separation rule or an active collision-avoidance system.
- Full reference corridor including pre-demo portions checked against all four neighboring cells: minimum observed grid depth **15.59 m MLLW** on the new H12617 display grid, no NoData crossings. Earlier 9 m result belongs to legacy CRM. Neither is under-keel clearance or current navigability.
- Measured in `check:vessels`: maximum sampled acceleration/deceleration **0.0450 m/s²**, maximum sampled turn rate **1.658°/s**, minimum simultaneous center separation **78.9 m**. These are properties of the synthetic fixtures, not vessel/AIS observations.
- 3D headings blend along the shortest angle across north; large/backward source-time jumps snap to the new course. Blank-canvas deselection is scoped to the canvas, not arbitrary HTML controls.
- T1/UUV alert choreography, risk values, decision timing and production telemetry are unchanged. T1 is still a dramatic preset, not newly validated UUV physics. These routes are not official docking plans or real vessel schedules.

## Actual browser check for the vessel revision

Windows, Codex in-app browser, production preview at port 4173. Initial replay inspection selected T3 and showed its source-backed readout. The tab subsequently changed to Local Demo, so the final revision was checked there rather than presenting mock output as replay/live output.

- At approximately mock t=28 s: T3 heading 42°, speed 3.4 m/s. At t=47 s: heading 32°, speed 3.3 m/s. After restoring 1× playback and resuming, at t=62 s: heading 24°, speed 3.3 m/s. Position, heading and follow view changed together through the channel bend.
- Pausing retained T3 selection; resuming retained it and continued movement. Switching 3D → 2D at t≈56 s displayed T3 at 33.72142, -118.26317 with depth 0 m; returning to 3D retained selection. Source remained explicitly MOCK.
- Screenshot: `D:\HarborGuard\frontend\artifacts\vessel-motion\vessel-turn.png`, 1920×1080, paused at approximately 47 s, display scale 3×. The screenshot shows 4× playback selected before it was restored to 1×. No video was captured. Temporary viewport override was reset afterwards.
- Final console error query returned `[]`. This iteration did not record a new FPS benchmark; the earlier 74/75/115 FPS screenshot readings belong to clarity revision `734e271`, not a sustained measurement of this revision.

## Automated execution

All exited 0 on this revision: `build`, `lint`, `check:a1`, `check:a2`, `check:a3`, `check:a4`, `check:a5`, `check:a6`, `check:recovery`, `check:english`, `check:vessels`.

The new vessel test covers full-route mask checks, motion/velocity/bearing consistency, gradual braking and stopped heading, bounded history, prediction equality, opposing-lane separation, angular wrap, pause/resume/reset, chunk-independent sampling, and seeks in all three generated files. A5 additionally checks selected-vessel retention while replay plays/pauses through timer ticks. Passing scripts are not browser, GPU, backend, or field certification.

Build retains the known approximately 998 kB uncompressed 3D chunk warning; it is not reported as an error-free performance certification.

## Backend report corrections

1. The old frontend handoff's “reject only writes a log” claim is obsolete for inspected code. `backend/app/decision/__init__.py` emits structured `decision` for both approve and reject. `storage.py` and `engine.py` contain durable history/checkpoint support. A did not implement or test those backend changes.
2. The existing `/api/events?since_seq=` route still calls the bounded 500-event bus; it is not a paginated structured history list. Durable storage alone does not give A access to every older approval/recommendation. The frontend still reports partial/unknown history and never infers authoritative approval from log text.
3. Actual read-only `GET http://127.0.0.1:8000/api/health` attempt on this iteration: connection refused. No successful response is invented. This says only that this local endpoint was unavailable, not that B's implementation failed its tests or that other deployments are offline.

## Remaining sign-off

- Current site bathymetry/coverage/uncertainty acceptance: historical NOAA H12617 multibeam is integrated; 1–2 m source, ~8 m harbor and ~1 m local display. This does not establish whole-harbor present-day accuracy. Newer 0.5 m Long Beach products found but not integrated or assumed to cover the demo; links and actual survey-envelope checks in SONAR-DEPLOYMENT.md.
- Land NAVD88 to water/seabed MLLW transformation and live tide.
- Current-version live approval/rejection refresh, reconnect/restart and history-window tests with B; actual Agent/recognition services with C.
- Synthetic replay Z-style zone references versus the named static business-zone IDs still limit some evidence/reopening-zone links. The UI's waiting/unknown indication is not claimed as successful route highlighting.
- Sustained GPU/thermal measurements, full live rehearsal and field/projector acceptance. Backup recording is not performed because the user cancelled it; it is not marked completed.
