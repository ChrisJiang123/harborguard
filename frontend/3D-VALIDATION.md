# 3D clarity and collapsible panels — 2026-10-18

Current shoreline changes and new on-device evidence are in [3D shoreline validation](../docs/3d-shoreline-realism/README.md). The records below retain their original historical scope.

Historical clarity evidence below predates the multibeam replacement. Current
seabed source, sample counts, datum, screenshots and measured readings are in
[MULTIBEAM-VALIDATION.md](MULTIBEAM-VALIDATION.md) and
[MULTIBEAM-SOURCE.md](public/data/MULTIBEAM-SOURCE.md). Do not use the old CRM
grid/FPS numbers as current MBES performance or acceptance evidence.

## Changes

- Default 3× vertical enhancement, always identified as non-true-scale; restore 1× remains available. Real-backend coordinates/depths, the 2D renderer, backend, and shared contract are unchanged. The subsequent vessel-motion revision intentionally changes synthetic T3/T4 positions in the shared 2D/3D mock/replay source.
- Native keyboard-accessible disclosure panels for Layers, Display Settings, Data sources, selected-target information, and scale/data legend. Closing a panel hides its content without resetting its controls. Narrow canvases expose Layers/Display Settings through Scene Settings.
- Supersampled rendering (DPR 1.5–2, adaptive floor 85%), no pixelated upscale, improved side lighting and lower overview angle. Camera framing now accounts for canvas aspect ratio.
- USGS/USDA NAIP orthophoto export upgraded from 1536×834 to 3072×1668 (9,154,383 bytes); four times as many display pixels. The underlying land DEM values/bounds are unchanged. The 4096-pixel request returned HTTP 504; the bounded 3072-pixel export succeeded and was validated before replacing the asset.
- Seabed display refinement: bilinear subdivision and smooth normals, no wireframe overlay, 2 m contour interval. Original source samples and land/NoData holes are preserved. This does not add new measurements or increase source accuracy.

## Historical browser observations (clarity revision `734e271`)

Local production preview: `http://127.0.0.1:4173/?replay=demo_full.jsonl&stats=1`.

- Windows, Codex in-app browser; temporary 1920×1080 viewport override, reset after testing.
- Observed canvas CSS size 1220×701.33; drawing buffer 1830×1052 (DPR 1.5).
- Hardware inventory includes NVIDIA GeForce RTX 5060 Laptop GPU and Intel Graphics. The browser's active GPU was not independently identified.
- Data: 487 building white models; 512×278 land grid with 66,211 valid land elevations; 433×235 NOAA regional seabed grid with 47,326 NoData cells; 103,552 source seabed triangles / 414,208 display triangles; 4 replay targets and 10 buoys.

The following are instantaneous approximately one-second UI readings captured in screenshots, not average FPS, minimum FPS, or a sustained performance benchmark. Replay was paused at 01:10; vertical display was 3×.

| View | Screenshot FPS | Water |
| --- | ---: | --- |
| Overview | 74 | Visible, 25% opacity |
| Surface | 75 | Visible, 25% opacity |
| Underwater | 115 | Hidden for terrain inspection |

Actual screenshots are saved locally under `D:\HarborGuard\frontend\artifacts\vertical-relief\`: `clear-overview-3x.png`, `clear-surface-3x.png`, `clear-underwater-3x.png`, and `compact-panels.png`. Screenshots are not committed.

Verified interactions at that revision: surface/underwater/overview/reset, 1× restore, scale changes, target selection/follow and source-backed synthetic target readout, water hiding, Layers expansion/collapse with buoy checkbox preserved, Display Settings expansion/collapse with the selected 2× value preserved, source/target/legend disclosure, Enter-key disclosure, and narrow-canvas Scene Settings. Playback/pause, A/B seek, and 2D/3D transitions were also exercised. No console errors were returned by the browser log checks. Screenshot-control timeout occurred once; reconnecting showed the page remained running and the underwater screenshot had been saved successfully. These FPS readings and screenshots are not a new sustained benchmark of later commits.

## Automated checks

Passed: `npm.cmd run build`, `lint`, `check:a1` through `check:a6`, `check:recovery`, and `check:english`.

The vessel-motion revision reran all of these and added passing `check:vessels`: full reference corridor including the pre-demo path checked against the bundled mask (minimum neighboring source-cell depth 9 m), maximum sampled acceleration/deceleration 0.0450 m/s², sampled turn rate 1.658°/s, and minimum simultaneous center separation 78.9 m. These are deterministic synthetic-model checks, not AIS observations, under-keel clearance, or collision-avoidance certification. See `ACCEPTANCE-A.md` for the current acceptance review and stale backend-report corrections.

A4 includes original-point preservation, bilinear center/extrema, no bridging of NoData cells, refined triangle count, unchanged source grid, vertical transform/restore, geometry reuse, and narrow-canvas framing. Build retains the existing approximately 998 kB uncompressed 3D chunk warning.

## Not completed / limitations

- Seabed remains the NOAA/NCEI 1-arc-second regional model (~25.7×30.9 m sampling). Near views still expose coarse/quantized source relief and stepped coastline boundaries. Refinement and the 2 m contour interval are presentation only, not survey-grade accuracy or real underwater imagery.
- A finer public-data candidate was found in the [NOAA-hosted Southern California CoNED archive](https://chs.coast.noaa.gov/htdata/raster2/elevation/CA_Southern_CoNED_DEM_2016_8658/). Its local harbor coverage, bathymetric source resolution, and datum compatibility have not been validated or integrated. Do not call it an installed 1 m harbor survey.
- Land NAVD88 versus seabed/water MSL alignment is still untransformed; reference water level is not live tide.
- This validation uses synthetic business replay, not new live-backend approval or recognition-service verification.
- Sustained FPS, thermal behavior, projector readability, field acceptance, live tide, and high-resolution bathymetry acceptance remain outstanding. Automated A6 passing is not full A6 acceptance. No recording was performed.
