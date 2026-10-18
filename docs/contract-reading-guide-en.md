# Frozen v1 Contract: English Reading Guide

This is a non-authoritative reading guide. The frozen originals remain unchanged: [B-maintained contract](../shared/contract.md), [C's transcribed copy](shared-contract-v1.md), and [TypeScript types](../shared/types.ts). This guide does not amend fields, enums, routes, event types, signatures, or cache semantics. Any contract change after the H2 freeze requires all three teammates' approval and a v1.1 version update.

For complete English request/response tables, message examples, units, recovery ordering, and decision semantics, see [the integration handoff](frontend-integration.md). The [generated OpenAPI](integration/openapi.json) describes the current Python constraints. Historical measurements apply only to the source SHA stated in each report.

## Processes and coordinates

- B: REST `http://localhost:8000/api`; WebSocket `ws://localhost:8000/ws`.
- C Agent: `http://localhost:8001`. A: `http://localhost:5173`. Optional Ollama: `http://localhost:11434`.
- Positions use WGS84 latitude/longitude. Depth is in meters, positive downward. The local origin is `lat0 = 33.7300`, `lon0 = -118.2600`. East coordinate: `x = (lon - lon0) * 111320 * cos(lat0)`; north coordinate: `y = (lat - lat0) * 110540`.
- `t` is simulation seconds from scenario start. Velocities are in m/s. Angles are in degrees, with heading measured clockwise from north.
- GeoJSON positions are `[lon, lat]`. Track history and prediction entries are `[lat, lon, depth_m, t]`.

## Types and envelopes

Classes are `unknown`, `uuv`, `fish_school`, `debris`, `marine_mammal`, and `vessel`. Alert levels range from 0–3; level 0 is background and does not enter the alert list. Zone states are `open`, `restricted`, `clear`, `unsurveyed`, and `blocked`.

`StateMsg` contains `type, seq, t, mode, network, scenario, paused, speed, buoys, tracks, alerts, zones`. It is a full snapshot delivered at 5 Hz. `EventMsg` contains `type, event, seq, t, data` and publishes when an event occurs. Both share the increasing sequence; gaps between event sequence values are normal because states also consume `seq`.

Track classification remains `unknown` before active-ping identification. `cue` is a passive acoustic hint. `err` describes a 1σ ellipse. State history contains at most 60 points; GET track returns full history. Prediction covers 5 minutes at 30-second intervals. Detection `bbox` uses pixel corners `[x1, y1, x2, y2]`, rather than normalized coordinates. Detection `model` is `yolo26n` or `stub`.

Risk uses unweighted components `C/P/B/Z/D`, each in the range 0–1, with weights `0.30/0.25/0.25/0.15/0.05`. A displays B's level rather than deriving its own. Option berth availability and residual risk are fractions in the range 0–1. Estimated saved hours use the stated per-zone `survey_h` assumption; they are not measured real-world savings.

Recommendation `kind` is `security/disaster/buoy`; `model` is `cloud/local/template`; `confidence` is `low/medium/high`. The summary is at most 60 characters and the explanation at most 300 characters. Evidence IDs must reference existing objects. Advice is not approval.

## REST, events, and recovery limits

The contract defines 21 REST operations and 14 event types. See the English handoff for every path, request, and response. WebSocket messages travel from server to client only; controls use REST. The existing `decision` event carries `alert_id, option_id, action, operator`. Approve and reject use the same shape. B persists before reporting success or broadcasting. An operator approves security restrictions; recommendation submission never executes them. Reject does not undo an earlier approved restriction.

GET `/api/events?since_seq=N` reads events with `seq > N` from the **most recent 500 events**. There is no all-history pagination, total count, or truncation marker. GET `/api/log` returns the current-scene cache, newest first, up to 1000 entries. Internal database persistence does not make every archived event publicly queryable.

On reconnect, buffer WebSocket messages, restore the current snapshot, fetch recent events and logs, merge by event `seq`, and preserve live changes received while REST requests are pending. Missing older decisions remain unconfirmed. Log prose is not structured approval state. Same-database restart preserves `seq` and safely pauses simulation; database replacement or rollback requires explicit session handling. Track IDs may repeat between scenarios.

## B/C Python boundary

Use the exact `render_ping` and `SonarDetector` signatures in the frozen originals. B passes the actual range, bearing, and seeded renderer settings; C returns grayscale `uint8` imagery and pixel-corner detections. This reading guide does not authorize changing these signatures or adding public fields.

Original Chinese samples, multilingual model tests, prompts, and hash-audited evidence may remain in the repository to preserve their meaning and provenance. English runtime documentation does not relabel those originals as new test runs.
