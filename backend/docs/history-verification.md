# B Persistence and Recovery Verification

Date:2026-10-17. Historical baseline main@5817b9c, branch codex/harborguard-backend-history. This validates those B changes, not full B0–B7, PR#6/#7 merge acceptance, or C template acceptance.

## Requirements checked

- Original taskbook B5 said approve emits decision/zone_changed, reject logs only. Original implementation matched; A's feedback was valid.
- Frozen v1 already defines decision {alert_id, option_id, action, operator}; requests permit approve/reject, and Python EVENT_DATA uses DecisionRequest.
- Owner's later instruction required structured reject when existing definitions allow it. Existing event/fields/enums reused; shared files/types unchanged.
- Previously seq, 500events, recommendations, logs, restrictions, details, PNGs were memory-only and lost on restart. No decision-detail/recommendation-list endpoint existed.
- /events remains ascending seq>N within the latest500, not “first500 from oldest.” Logs remain latest1000, newest-first, cleared on reset/new scene.

## Implementation/consistency

| Capability | Location | Result |
| --- | --- | --- |
| SQLite WAL+FULL, single-writer lock, migration version |app/storage.py, migrations/001_history.sql|Implemented/tested|
| All accepted events, advice, eachdecision, last-decision projection |storage.py, engine.py _history_objects|Implemented/tested; outside-window archives internal only|
| Runtime/RNG/Kalman/counters/restrictions/log checkpoint |checkpoint.py, engine.py|Implemented/tested; restart pauses safely|
| Prefer current details, fall back to stored details/PNG |api/rest.py, engine.py detail/image|Implemented/tested; historical details are not active/approval state|
| Commit before success/broadcast, rollback state/seq/logs/events |engine.py durable, bus.py, main.py503handler|Implemented; actual SQLite-failure injection passed|
| Reject existing decision plus original log/no zone change |decision/__init__.py|Implemented/tested|
| All-history pagination |Not implemented|PENDING, frozen-contract review required|
| A#7 browser on this B |Not run|PENDING; A latest456b808, no frontend commits mixed|

Persistence uses JSON, not pickle, with allowlisted simulation/tracking restoration. Static geometry/classifier initialize normally; PNGs store separately to avoid reencoding. Storage errors never silently fall back to memory. Corrupt/incompatible DB refuses startup. Memory retains current working sets, not every historical object. DB files are ignored.

## Tests executed

Original backend suite73PASS. Final **88PASS, 61.61s**:73existing+15new. Ruff backend/app/backend/tools/backend/tests PASS. One Starlette/httpx TestClient deprecation warning; team dependencies unchanged.

backend/tests/test_history.py covers:
- Durable approve/reject, structured REST/WS, restart state/details/PNGs/logs/advice, and global seq including states.
-526persistent events yield exactlylatest500 publicly; oldadvice/decisions remaininternal.
- SQLite triggers abort decision-event insert, recommendation projection, or runtimecheckpoint:503, atomic memory/disk rollback, no successbroadcast.
- Reset retains historical details; oldalertdecision409; counters increase acrossrestart; oldPNGs not overwritten.
- Both scenarios resume checkpoints identically to uninterrupted acoustic/Kalman runs forstate/log/RNG/PNG.
- CorruptDB, unknownschema, fingerprintmismatch, secondwriter refused; 21operations/statefields/decisionenum unchanged.
- Actual-response fixtures conform to frozenmodels.
- Runtime SQLitefailure leaves queries available, health503, simulationpaused; reset recovers after fault repair. Optional observer failure cannot undo committed data; offline recorder output failure still raises, preventing false recording success.

## Actual Uvicorn process check — not browser integration

Command: python -m backend.tools.history_smoke --directory artifacts/history-live-20261017-1 --port8004. New independentDB, realHTTP/WS, forced process termination/restart; DEBUG truth disabled; C not called. Recommendation explicitly tool-generated templatefixture; detectionsstub.

| Item | Actual | Verdict |
| --- | --- | --- |
| Total |63.126s|PASS|
| Three prepared starts |1.586/1.544/1.544s|PASS, not from-zero/fullABC|
| L1 |t38.0, wall3.752s|PASS|
| L2 |t150.7, wall15.109s|PASS|
| L3/options |t483.1, wall48.385s|PASS; t90 observation cannot establish escalation failure|
| State frequency |5.004Hz|PASS over~48sSecurity|
| Max received state |25381B|PASS<50000, notallscenes/long-term maximum|
| Reject |seq303, t485.0|PASS, complete fixture committed|
| Approve |seq305, t485.0|PASS, restrictionschanged|
| Forced-restart recovery |same t/alerts/zones/details/events, no seqrollback, pausedtrue|PASS|
| After520logs internalarchive |587events, including earlier advice/both decisions|PASS|
| Publicevents simultaneously |latest500, firstoverflow-20|PASS oldsemantics; old decision unqueryable via v1|
| Second forcedrestart |same500eventsrestored|PASS|
| Emptytrack RecoveryPNG |4×HTTP200+signature|PASS transport; real recognition PENDING|

Full rawreport/DB/serverlogs/eventJSON in ignored artifacts/history-live-20261017-1/. Small reviewable fixtures in backend/fixtures/history/. No DB/log/cache/keycommit.

## FAIL/PENDING/boundaries

1. PENDING, blocks full-history-refresh acceptance: storedoutside-window records have no public v1readpath. NeitherPASSnorlog-derivedapproval isvalid. Minimumv1.1proposal inhistory-handoff.md, unimplemented.
2. Historicalstrict everytick20ms FAIL:10×realservice logged260overruns, max135.0ms, includingcheckpoint/SQLite. Detection/algorithm unchanged. Overrun-onlylogs cannotyieldmean/P95. Concurrentregression wasrunning, so not a dedicated performance benchmark. Short5Hzpassed; dedicated new-version performance/20minutesstillneeded. Ownerlatermade20msbest effort.
3. PENDING actual A/C: didnotcombine this B with A#7latest456b808 or#6Ctemplate; no browserrefresh/disconnectpassclaimed. No newercloudroute.
4. PENDING external: model/physicalsonar, bathymetry/tides, projector, three-personrehearsal. StubPNGs/B scripts do not substitute.
5. v1has no terminaldecision/idempotencykey, globallyuniqueTrackID, datasetidentifier. Reject does not undo approve; no automatic UI business retries or approval using historical objects.
6. Deployment: fixedpath, oneworker, writablelocaldisk, preserveDB. Database replacementcannot hidefaults. First-installtiming/wheel distribution untested; prepared checkout startup used.

## Integration preparation

B-onlybranch. Owner cancherry-pick into an independent A/B/C branch, retain the verified template, andrerunbrowser. No mainchange, ForcePush, teammate remote modification, Push, orPRcreation/update atthissnapshot; ownerreview/confirmationrequired.
