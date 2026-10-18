# A Handoff: Final-Main Recovery Reproductions and Minimal Fixes

Historical tested main: a841bf9a70d8bf8237b9e03763852a34bed10368, including A #7/#11/#15. Exact-source R1–R4 function reproductions all FAIL. R1/R3 were rerun in the latest-main browser; R2 used identical A code in e1. The earlier complete four-case browser evidence is from5a68; three relevant recovery source files were unchanged througha841. R4's complete delayed-browser test was not rerun on latest main. B did not edit frontend/frozen contracts or automatically post this document to a teammate PR.

Latest checks: a841 showed two same-text live logs but one after refresh; GET log503 still lacked a recovery-error warning. e1 at t632 stored reject seq1158/1201 from Operator A/QA_CURRENT_2 without restrictions, but UI retained the former operator.

**Separate B defect:** metrics-only option updates were not broadcast on main. B fixed it in e1 (237 PASS/2 SKIP); A should not mask it by polling. A's old-REST/new-WS R4 still requires its own fix. At this report's date B's fix was not yet pushed/merged.

## R1: Legitimate identical logs lost (P1)

With B paused/ended, POST /api/log twice:
`{"level":"info","source":"operator","text":"QA_FINAL_SAME_TEXT_SAME_TIME"}`.
B succeeds and persists seq1495/1496 at t600; GET log returns both. Browser shows2 live,1 after refresh.

Fix mergeRecoveredLogs in frontend/src/store/useHarbor.ts: preserve identity-bearing log events by seq, even with identical content. ID-less REST logs must preserve multiplicity; content Sets or simplistic max-count merges do not establish perfect deduplication. Outside500, identity may be unknowable: degrade honestly without new fields.

## R2: New operator's event treated as duplicate (P1)

At paused t685, A13/opt-1 reject seq4201 operator Operator A followed by seq4366 operator QA_SECOND_OPERATOR. B retains both with no restricted zones; live UI retains Operator A, refreshing shows the second.

Fix eventIdentity/decision projection using event seq and an internal last-decision seq per alert. Older compensation cannot overwrite newer results; same-seq retransmissions apply once. Merely adding operator to a content key is insufficient. Clear state via existing session/generation on reset or genuine rollback. Reject is not undo-approve.

## R3: Failed GET logs not disclosed (P1)

An isolated QA proxy returned503 only for GET /api/log?limit=200; all other B responses/WS were real. After refresh LIVE/state continued, but no log-recovery partial/failure warning appeared. liveRecovery.ts forwarded eventsResult failure into RecoveryMeta but converted logsResult failure into an empty list; function reproduction returned phase=complete.

Add internal log-request success/error metadata. Failed logs must produce at least partial status and retry entry; distinguish event-only and both-request failure. Preserve live WS; failure is not an empty history. Never auto-retry decisions.

## R4: Old REST options overwrite newer WS (P1, actual reproduction)

1. Pause A10× at t655, A13 residual risk15%. Refresh starts GET /api/options/A13 recovery.
2. QA delays only that request's original old response6s, without modifying fields/labels/events. Ordinary detail reads are not delayed.
3. After capturing old response, resume B. Three seconds later t685 naturally emits options_ready seq4178, risk20%; opt-2 closure/speed-limit sets also change. Pause.
4. New WS arrives first. Real C submits template advice with residual0.20. Old REST then makes UI table15%, while Agent stays20%. Both raw payloads/screenshots retained.

Fix recoverLiveState final options spread plus cacheOptions/detail writes. Store internal per-alert options event seq and each request's session/generation/start boundary. Preserve the new complete option set if a newer event arrived during the request; otherwise REST fills gaps. Blindly reversing spread is insufficient because REST may also be newer than cache. Clear invalid selected-option IDs; map/table share the same option collection. Shared REST has no version field, so do not claim absolute ordering for arbitrary races.

Some delays happen to pass via8s client timeout or a later request reading new data. Regression must cover: old payload already captured, new WS first, old payload successfully returns.

## Other delivery items

- After B10 returns online, the latest buoy advice can still describe the prior three-offline snapshot while current state is8/10 online. A/C should label advice age/history or C should generate fresh recovery advice. No new shared retraction event or log-derived current decision. This nonblocking snapshot limit is separate from B broadcast fix.
- demo_a.jsonl/demo_b.jsonl/demo_full.jsonl Recommendation.summary exceeds60 characters and B rejects it. Shorten fixtures and assert lengths; do not relax contract. Old replay_a/replay_b are valid but stub, not latest-model evidence.
- Embedded browser reports “3D rendering is unavailable in this browser.” Verify WebGL/playback on recording/projector hardware; no evidence this is a B-interface defect. The1003.10kB3D chunk warning is nonblocking.
- Recorded duration60251.812ms with slider step100 makes End stop60200ms,~52ms short. Play finishes correctly. P2: explicit seek(duration) or keyboard-End handling; do not falsify valid JSONL timestamps.
- A temporary Z1…Z10 fallback came from the QA server's wrong GeoJSON MIME. application/geo+json restored all12 zones. **Not an A production bug.**
- B exported actual A/B/C streams and original PNGs in a separate maina841 yolo26n/template bundle, without modifying frontend. A can review the manifest for formal static deployment.

Limit fixes to frontend, preserving shared/B DB/C routes. Keep proven seq connection baseline, AbortController, session/generation, and500-window notices. Supply a new SHA plus R1–R4 regressions. B then reruns affected integration; old reports never automatically transfer to a new SHA.

Evidence: [machine record](evidence/final-delivery-20261017.json); local artifacts/final-delivery/browser-r*.json and PNGs in the final isolated worktree. The project owner can forward this file.
