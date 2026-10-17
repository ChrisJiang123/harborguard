# Proposed sonar deployment and finer seabed display

Date: 2026-10-18. Scope: frontend only. These are **proposed demonstration
locations, not surveyed or installed Port of Los Angeles sonar positions**.
Real deployment requires equipment specifications, local authority approval,
navigation/anchor restrictions, mooring/cable design and an acoustic site survey.

## Layout actually changed

The old bundled file had several stations on cells without H12617 water support;
the emergency fallback used an arbitrary circular layout. Both are now replaced
with a single hand-authored proposal along the existing demo approach corridor,
outer bend, inner bend and terminal-side water approaches. Stations flank the
synthetic T3/T4 routes rather than sitting directly on their paths. Roles are
reference watch areas, not official facility names or a claim of complete port
protection. Other basins and terminals remain outside this limited proposal.

| Station | Latitude | Longitude | Proposed watch role |
| --- | ---: | ---: | --- |
| B1 | 33.7145 | -118.2705 | Southern approach |
| B2 | 33.7163 | -118.2720 | Western approach flank |
| B3 | 33.7182 | -118.2656 | Outer bend east flank |
| B4 | 33.7200 | -118.2672 | Outer bend west flank |
| B5 | 33.7212 | -118.2656 | Waterside approach |
| B6 | 33.7240 | -118.2643 | Inner corridor west flank |
| B7 | 33.7258 | -118.2605 | Inner corridor east flank |
| B8 | 33.7276 | -118.2626 | Northern corridor flank |
| B9 | 33.7305 | -118.2576 | Inner bend approach |
| B10 | 33.7320 | -118.2575 | Terminal-side water approach |

`src/data/sonarDeployment.ts` is the proposal source; `make:replays` regenerates
the bundled buoy file and all three **synthetic** replay fixtures. No actual
backend recording is rewritten. Incoming backend/other recorded coordinates
always take priority and are **not moved** to make the picture look better.
The proposal annotation matches both stable ID and coordinates, not ID alone.

Proposed heads are illustrated 3 m below the fixed reference water surface,
suspended from buoy markers. This is an assumption, not equipment telemetry.
No invented head depth is applied to live or differently located recorded
stations. The old downward giant cone is removed: it falsely suggested a known
beam/coverage volume. Remaining 600 m rings are **nominal range**, not a ray-traced
acoustic mask, verified probability of detection or proof of visibility through
land/quays. Pulse animation is a source ping indicator, not simulated acoustics.

The rationale follows installation principles, not a product-specific design:
[Sonardyne installation guidance](https://www.sonardyne.com/underwater-surveillance-options-for-critical-asset-protection/)
describes site-dependent depth, pier/column installations and overlapping
perimeter arrangements. Its published ranges are NOT used as a performance
claim for HarborGuard. Actual channel exclusion width, tide, seabed clearance,
propeller noise, ship occlusion, multipath, sound-speed profile, maintenance,
cabling and permissions are unverified. No frontend change fixes B/C ping
selection, empty sonar imagery or real YOLO behavior.

## Automated verification actually run

`npm.cmd run check:sonar` passes:

- All 10 stations have four valid neighboring H12617 water cells; minimum support-cell floor depth 6.89 m MLLW, >2 m below the assumed 3 m head.
- Minimum distance to sampled synthetic vessel center paths: 60.5 m, including pre-demo route portions. Sampling is 1 s; this is NOT a surveyed navigation exclusion/safe-distance certification.
- Bundled buoy JSON, default mock and seek-restored synthetic replays use identical positions.
- A changed coordinate is not annotated as the proposal. No live state remapping is introduced.

Final execution: `build`, `lint`, `check:a1`–`check:a6`, `check:recovery`,
`check:english`, `check:vessels`, `check:sonar` all exited 0. A4 includes an
opacity-only edge test with unchanged input depths and opaque valid crop
perimeters. A comparison against preceding commit `2c677a3` verified that the
three generated replay fixtures change only buoy lat/lon/range, not target
motion or event/approval content. `git diff --check` passed; edits stay inside
`frontend/`. Source BAGs, Python packages, `.env`, `node_modules` and `dist` remain
ignored. The known ~1,003 kB uncompressed 3D bundle warning remains.

## Seabed change and its limits

The inspection patch is now 1601×1409 at ~0.99×0.99 m display sampling, replacing
the previous 801×705/~2 m version. It still uses H12617 MBES BAGs, not new or
synthetic soundings. Valid output: 542,742 samples (24.06% of its rectangle):
541,854 supported by the original 1 m BAG and 888 by the original 2 m BAG.
The latter are interpolated display samples, not new 1 m measurements.
The main harbor remains ~8 m; whole-harbor 1 m data is NOT claimed.

Combined seabed triangles: 2,236,512 (local patch 1,080,182). Water remains 8,876
merged flat triangles. Shared grid coordinates and 35,577 common samples are
checked; no LOD overlap or cross-NoData faces are added. Mesh smooth normals
remain in use. One-cell **inward display feathering** at valid/NoData boundaries
uses vertex alpha with multisample alpha-to-coverage to soften jagged silhouettes.
It never alters depths, positions or fills holes; it is not a reconstructed quay
or measured coastline. Rectangle/LOD edges remain opaque. Its effect depends on
browser MSAA and still requires visual validation. Coarse land (~20–26 m), far
harbor boundaries and survey gaps remain visible limitations.

## Browser validation status

The attempt to validate this revision returned **local browser use disabled in
Work settings**. No new screenshot or FPS result is claimed. Previous screenshots
and 68/65/95 FPS readings belong to the earlier 2 m patch, not this denser mesh.
Build/lint/A1–A6/recovery/English/vessel and new layout tests are recorded
separately from pending browser/GPU/projector/field validation. A6 stays incomplete.

## Data links for a higher-resolution replacement

Use [NOAA Bathymetric Data Viewer](https://www.ncei.noaa.gov/maps/bathymetry/),
enable **NOS Hydrographic Surveys / BAG** and **Multibeam**, then search the IDs
below. Download **Bathymetry → MB … MLLW … .bag**, not a backscatter TIFF,
GeoImage PDF, ordinary land DEM or shaded-relief screenshot. Bring the BAG plus
its survey report/metadata and tide note. Grid spacing is not measurement accuracy.

| Survey catalog | Acquisition | Native grid offered | Area |
| --- | --- | --- | --- |
| [W00711](https://www.ngdc.noaa.gov/nos/W00001-W02000/W00711.html) | March 2024 | 0.5 m | Long Beach outer harbor |
| [W00710](https://www.ngdc.noaa.gov/nos/W00001-W02000/W00710.html) | April 2023 | 0.5 m and 1 m | Long Beach inner harbor / Area 8 |
| [W00660](https://www.ngdc.noaa.gov/nos/W00001-W02000/W00660.html) | August 2021 | 0.5 m and 1 m | Terminal Island vicinity |

These are verified NOAA catalog products, **not integrated data**. Their NOAA
survey polygon bounding boxes reach only approximately longitude -118.245 to
-118.247 at the western end, whereas the current inspection center is near
-118.250. A polygon envelope is only a discovery check, not proof of complete
soundings. None is assumed to cover this west-port inspection patch. Do not
move the harbor scene or substitute east-port data without making that change
explicit. W00711 uses NAD83(2011), while H12617 uses legacy NAD83; both advertise
MLLW but epoch/location-specific datum alignment must be verified from products.
Their NOAA catalogs exclude navigation use.

For the current center, find MBES data covering approximately 33.7324 N,
118.2500 W (patch bounds are in the JSON) with actual elevation/depth values,
coverage and uncertainty. If 0.5 m does not cover this location, retaining honest
1–2 m survey data is preferable to relabeling unrelated high-resolution data.
