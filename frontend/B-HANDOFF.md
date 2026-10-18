# Backend Gap Reproduction for B — Contract Freeze

Recorded 2026-10-17. This describes states A could not reconstruct under the frozen contract. A did not modify B, databases, or shared contracts.

> 2026-10-18 review: “current” below refers to a historical observation, not today's runtime. backend/app/decision/__init__.py now emits structured decision events for approve/reject; storage.py/engine.py implement persistence/checkpoint recovery. Do not continue saying rejection only logs or B is entirely nonpersistent. The frozen /api/events still reads a 500-event cache without paginated history. Persistence does not mean A can query all older decisions. In that review, 127.0.0.1:8000/api/health refused connection; no current B restart/decision round-trip or B tests were executed/modified. B's report was on remote main 8613834 at backend/docs/B-final-acceptance.md; its evidence was not rerun by A. See ACCEPTANCE-A.md for A's review conclusions.

## 1. /api/events covers only the latest 500 events

Interfaces: GET /api/events?since_seq={seq}, GET /api/log?limit={n}.

Historical measurement:

```text
GET /api/health             -> {"ok":true}
GET /api/events?since_seq=0 -> HTTP 200, 151 entries
First: {"type":"event","seq":1563,"t":0.0,"event":"scenario_changed",...}
GET /api/log?limit=3        -> HTTP 200, 3 entries
```

EVENT_CACHE_SIZE is 500. /api/events filters the memory queue by since_seq without page cursor, total, or truncation flag. Reproduce by generating >500 events, refreshing A, and querying since_seq=0: the earliest events are absent. Free-text /api/log cannot establish decision state.

Requested future behavior: B and the contract-review process provide persistent paginated recommendation/decision history, or at least an explicit truncation marker and stable cursor. Records need stable identity, related recommendation/option IDs, state, time, and structured decisions, surviving restart.

A currently warns when the response reaches 500 entries, but cannot recover earlier recommendations/approve/reject or distinguish exactly 500 total from truncation. Live continuity uses existing recommendation/detection/alert IDs and event fields.

## 2. Historical rejection lacked a structured decision — source fixed, runtime recheck pending

Interfaces: POST /api/decision, GET /api/events, WS /ws.

```json
{"alert_id":"A1","option_id":"opt-1","action":"reject","operator":"Operator A"}
```

At the historical audit, success was {"ok":true}; only approve appended decision, while reject appended an operator free-text log. Existing API tests checked HTTP success/no restriction but not a rejection event. The local scenario reached only level 1 at t=90 with no options, so no fabricated successful runtime response was recorded; the finding came from route/branch inspection.

Historical reproduction: prepare an active L3 alert with options_ready, record max seq, reject, then query later events or listen to WS. Only log appeared, not decision; refresh could not authoritatively distinguish rejected from untreated.

Required behavior: after durable rejection, publish the same structured decision shape as approval: alert_id, option_id, action reject, operator, and envelope simulation time. Any rejection reason would require a contract-defined field. Persistence failure must not return success.

At that stage A displayed “state cannot be confirmed” after successful rejection and prevented duplicate submission, replacing it if a structured decision arrived. Missing structured history is not shown as pending approval; A never parses log prose into decision state.

## Integration checks after B's change

1. Refresh after approve/reject and restore the same authoritative state from structured history.
2. For >500 events, older history pagination and page-continuation indication require contract approval; the frozen v1 cannot satisfy this request.
3. Records survive B restart.
4. Restore history/WS with stable-ID deduplication, no duplicate/regressing state. Current recommended ordering opens WS and buffers before history recovery.
5. A adopts new fields/endpoints only after B/team contract review, never by unilateral frozen-type extension.
