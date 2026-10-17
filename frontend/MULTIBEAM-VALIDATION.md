# Multibeam frontend validation — 2026-10-18

Scope: frontend only, on `feature/3d-vertical-relief`, following `051d3f1`.
Renderer: Three.js / React Three Fiber, not Cesium. No backend, database, frozen
contract or B/C tests were modified. No recording was performed.

## Data actually integrated

NOAA H12617 (2013), Reson 7125 MBES, finalized 1 m and 2 m BAG products. Both
original BAGs were downloaded, opened as HDF5, and checked for grid dimensions,
pixel-center coordinates, CRS, vertical reference and negative elevations.
Native support cells and the uncertainty band were read before interpolation.
See [full provenance](public/data/MULTIBEAM-SOURCE.md). The investigated CoNED
candidate was **not used** as the final seabed. W00711 (2024) was discovered but
not integrated or represented as verified demo coverage.

- Harbor: 1401×911, ~7.94×7.95 m display sampling; 599,472 valid samples, 46.97% rectangular coverage, depth 1.15–28.27 m MLLW.
- Local inspection: 801×705, ~1.98×1.99 m sampling; 135,763 valid samples, 24.04% rectangular coverage. Missing coverage includes land and unsupported survey locations, not an invitation to invent a seabed.
- Main and detail meshes share 35,577 common samples; automated equality within 0.011 m verifies the aligned LOD sampling. Coarse faces/contours are removed under the fine patch, colors use the same scale.
- Combined seabed: 1,425,206 triangles. Flat reference water: 8,876 triangles instead of 1,172,698 redundant triangles; exact supported-cell mask verified, with no overlap or NoData bridging. This is a geometry count, not an FPS claim.
- 487 LA County footprint/height white models; unchanged 512×278 USGS land DEM and 3072×1668 NAIP imagery. Business source is mock/replay, not actual vessel observations.

## Automated checks actually run

Exit 0: `build`, `lint`, `check:a1`–`check:a6`, `check:recovery`, `check:english`,
`check:vessels`. A4 includes the new multibeam provenance/value checksums,
fractional elevations, NoData preservation, same-source/datum/aligned-detail
validation, coarse/fine equality, non-overlapping LOD faces and merged water-mask
coverage tests. Vessel route checks against the new survey display grid pass;
minimum support-cell depth 15.59 m is not navigational clearance.

Build retains the known ~1,001 kB uncompressed 3D chunk warning. Passing A6's
script is not full A6/projector/field acceptance or an actual recording.

## Browser evidence

Local production preview, Windows / Codex in-app Chromium, viewport temporarily
1920×1080, `http://127.0.0.1:4173/?mock=1`, vertical display 3× (enhanced, not true
scale), four mock targets and ten buoys. Screenshots are saved outside source in
`D:\HarborGuard\frontend\artifacts\multibeam\`.

Actual browser checks: Overview, Surface, Underwater, water visibility, frame-rate
toggle, 2 m detail off/on, seabed off/on, T3 selection and pause. Selecting T3 at
mock t=01:59 showed heading 18°, speed 3.6 m/s, depth 0 m. Switching to 2D retained
T3, paused time and position 33.72330, -118.26239. Data source remained MOCK.
Final console-error query returned `[]`. No live backend/Agent validation was
performed in this iteration.

MBES/merged-water build DOM readings observed near screenshot capture (before
the final allocation-only mesh/contour fast path):

| View | Observed FPS readout | Conditions |
| --- | ---: | --- |
| Overview | 68 | Running mock; water and risk layers on |
| Surface | 65 | Running mock; water and risk layers on |
| Underwater | 95 | Paused mock; water and risk volumes hidden for terrain inspection |

These are individual approximately one-second UI readings, not average/minimum
FPS, a matched-condition comparison, a sustained benchmark, or a claim that
optimization improved FPS by a measured percentage. Camera transitions and layer
toggles produced different readings. Screenshot pixels can capture a subsequent
sample. Canvas measured 1220×760 CSS px, drawing buffer 1830×1140 (DPR 1.5), within
the 1920×1080 dashboard. The exact browser GPU was not independently identified.

Files: `overview.png`, `surface.png`, `underwater.png` in the artifact directory
above. Preset active classes were checked before final overview/underwater
captures. The underwater view shows real grid-derived floor relief, not a
photorealistic seabed texture. Earlier pre-optimization readings are not used as
current performance evidence.

After those captures, dense unrefined grids received a direct coordinate path
and contour cells are rejected before allocating point objects. Final build,
lint and A4 passed again with unchanged mesh/contour counts. The final bundle
was reloaded and visually checked in the browser (overview, saved as
`final-overview.png`, final console-error query `[]`); the earlier FPS
samples are not rebranded as a benchmark of this last CPU-only change.

## Remaining limits

- Not current-year, whole-harbor 1 m/0.5 m coverage; acquisition is 2013. No local survey/field accuracy certification, dredging-update confirmation or navigation approval.
- Land NAVD88 versus seabed/water MLLW remains an unresolved spatial vertical-datum alignment. Reference water is not live tide.
- Grid/coverage edges remain discrete at 2–8 m; land geometry still samples ~20–26 m. Gaps, coarse shore silhouettes and absence of detailed quay/façade models are not claimed fixed by adding artificial topography.
- Sustained thermal/GPU FPS, actual projector/3 m readability, live B/C rehearsal and field sign-off remain separate. A6 is not fully accepted.
