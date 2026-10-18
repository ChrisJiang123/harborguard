# Poster: actual 3D simulation capture

This replaces the sparse, time-zero replay image used by the previous poster.
The image is an unchanged browser capture of the real A frontend connected to
the real B backend and C template Agent. It is not a fabricated dashboard or a
composite of alerts from different runs.

## Source and isolated environment

- Official main: `d2d4c6fbdff72de5b2d2c02aab0c39723513f3a8`.
- Branch: `codex/harborguard-english-live`; B display strings translated to English.
- Independent SQLite database; `DEBUG_TRUTH_TRACKS=0`; one backend worker.
- Isolated ports: frontend `5186`, B `8030`, C `8031`.
- Cloud disabled; local provider deliberately unavailable; actual recommendation
  records report `model=template`. No models were downloaded, trained or replaced.
- Existing formal services on `5173`, `8000`, `8001`, `8003` and their databases
  were preserved. Completed acceptance services on nine other isolated ports
  were stopped only after matching their process identities and metadata.
- After capture and REST/WS/PNG verification, the dedicated `8030`/`8031`/`5186`
  services were stopped to release memory. Their SQLite database and all capture
  records remain intact. These test ports are not a published live deployment.

## What the captured frame actually contains

| Item | Observed value |
| --- | --- |
| Source | Scenario A, real backend simulation |
| Simulation time | 924 seconds, paused; displayed as 15:24 |
| Speed before pause | 10x |
| Tracks | 5 |
| Active alerts | A1/T3: level 3, risk 0.8074341905810423; A13/T60: level 2, risk 0.5761579730217736 |
| Online buoys | 10/10 |
| Response options | 4 |
| Latest recommendation | `rec-73e21ce15950`, template, `opt-1`, medium confidence |
| Recommendation warning | Residual risk 0.55 exceeds 0.2 |
| Activity logs | 46 |
| Cached business events | 109 |
| Latest detection | `det-6`, `yolo26n`, confidence 0.6964585781097412 |
| Approval | No approval or rejection was performed for the captured frame |
| Camera | Follow Selected, T3 |

The recommendation uses its actual context/version; its 0.80 alert-risk text is
not rewritten to match the later 0.81 state. The model's T60 classification is an
output, not proof of a second real intruder. Synthetic echoes, simulated AIS,
false tracks and classification errors remain limitations.

The UI retains its actual LIVE data-source label and visible paused indication.
The poster explicitly calls this a simulation. It does not imply live marine
sensors, actual tide, deployed buoys or operational navigation clearance.

## Image and print output

- Capture: [unchanged browser image](poster-live/security-3d.jpg).
- Evidence: [evidence.json](poster-live/evidence.json).
- Print PDF: [A3 poster](poster-live/HarborGuard-Poster-A3-3D.pdf).
- Screenshot SHA-256: `18c71c843082f9584153832a882892de46cc418041f8f6e9078731079af56252`.
- A3 portrait: 297 x 420 mm; vector text; embedded fonts; validated repository QR.
- A 3508 x 4961 raster preview is also exported at 300 dpi. The source browser
  capture is 1280 x 720 and remains unchanged; raster export does not create
  additional screenshot detail. The poster's large explanatory text is vector.

The browser encountered WebGL context loss under memory pressure during setup.
Reopening a fresh tab restored the actual 3D image. This is a captured frame,
not an assertion that a fresh five-minute 3D endurance/demo acceptance passed.
At the small browser viewport, the sticky approval block obscures part of the
Agent summary; the poster's adjacent text quotes the actual backend record.
No A production source or CSS was modified to stage this image.

## Reproduce the content

Use the normal [demo runbook](demo-runbook.md) with a new, compatible database,
one backend worker, `DEBUG_TRUTH_TRACKS=0` and the explicit offline template route.
Start scenario A at 10x, observe real alert escalation and Agent records, then
pause on an actual event-rich frame. Select T3, switch to 3D and choose Follow
Selected. Event timing and temporary false tracks must be observed, not forced
to match this image. Do not copy the private test port wrapper into deployment.

Upload the final PDF to Drive and paste its reviewer-accessible viewer link in
Devpost. The PDF and local ZIP do not themselves create that Drive link, a demo
video or a Devpost submission.
