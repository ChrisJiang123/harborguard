# HarborGuard Frontend

An underwater harbor-security digital twin, implemented against tasks A0–A6.

The interface is English, including 2D/3D controls, guidance, approvals, demo recommendations, logs and errors. The display layer translates known Chinese labels and standard backend messages in existing recordings without changing raw records or event identity. Unrecognized external free text retains its source language.

## Status and acceptance boundary

A0–A1 provide the UI shell, shared contract types, Zustand state, local mock data and WebSocket reconnect. A2 adds the 2D map; A3 adds controls and the Security workflow; A4 adds an integrated above/below-water 3D digital twin. A5 provides Recovery, JSONL playback, sonar-image dialogs, synthetic-data metrics and a local OSM shoreline fallback.

Local browser checks have exercised 2D/3D, replay and refresh recovery. Actual network-loss operation, the target projector and the current full B/C service combination require separate acceptance. The local shoreline is not a complete PMTiles offline basemap.

The 3D renderer is **Three.js / React Three Fiber, not Cesium**. The default seabed uses NOAA H12617 **multibeam** BAG products (original 1 m / 2 m grids, acquired 2013), with an approximately 8 m harbor display and an approximately 1 m local display patch. See [multibeam provenance and regeneration](public/data/MULTIBEAM-SOURCE.md). It is not a land DEM or a synthetic regional DEM presented as multibeam. **A6 remains incomplete**: historical-survey coverage/uncertainty, MLLW–NAVD88 alignment, live tide, current full-service rehearsal, target projector/network and field sign-off remain separate. The user cancelled recording; no recording is claimed. The latest 1 m display/sonar revision has automated tests; its originally recorded browser check was pending because browser control was disabled. Later browser notes below retain their own scope. See [sonar deployment and data links](SONAR-DEPLOYMENT.md).

## Run

Start B from the repository root (Python 3.11+):

```powershell
py -3.11 -m venv .venv
./dev.ps1 setup
./dev.ps1 backend
```

With dependencies prepared, use `./dev.ps1 backend` directly. Health: `http://localhost:8000/api/health`; API docs: `http://localhost:8000/docs`.

In another terminal:

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

| URL | Source |
| --- | --- |
| `http://localhost:5173/` | Live backend connection |
| `http://localhost:5173/?mock=1` | Local synthetic demo |
| `http://localhost:5173/?replay=demo_a.jsonl` | Synthetic Security replay |
| `http://localhost:5173/?replay=demo_b.jsonl` | Synthetic Recovery replay |
| `http://localhost:5173/?replay=demo_full.jsonl` | Three-minute synthetic combined replay |
| `http://localhost:5173/?replay=replay_a.jsonl` | B's recording, when supplied in `public/` |

For production preview, run `npm.cmd run build`, then `npm.cmd run preview -- --host 127.0.0.1 --port 5173`. B's current CORS allows that port; other ports require an approved origin configuration. Reuse an existing development server instead of starting a duplicate; source edits update through Vite.

## A1: basic demo

The local mock starts at 1×. Its scripted timeline is level 1 at 10 s, level 2 plus synthetic detection at 35 s, level 3 plus options at 60 s, a template recommendation at 66 s, and simulated arrival at an example asset at 90 s. These are mock timings, not live-backend guarantees.

The top bar supports 4×/10×, pause and restart. Click a target to select it; click again to deselect. The MOCK label identifies synthetic data.

Without query parameters, the app connects to `ws://localhost:8000/ws`. On failure it shows disconnection and retries after 1, 2, 5, 5 seconds. Valid contract messages activate LIVE. Connection source and the simulation's `network` field are distinct.

## A2: 2D map

The map uses the Port of Los Angeles OSM basemap, initially centered at 33.735, -118.255, zoom 14.

- The local example has 10 zones, asset warning rings, 10 buoy range circles and two initial simulated targets.
- Solid lines show history; dashed lines show prediction. Backend `level` determines color. The error ellipse draws the one-standard-deviation `err` in metric coordinates.
- Selection uses one shared state for map/list; blank-map clicks clear it.
- Offline buoys are gray with a cross. A true `pinging` flag triggers about 1.5 seconds of animation.
- After mock second 66, hovering or keyboard-focusing an option previews its restricted-zone boundary with a red dashed line.
- The harbor overview resets framing. The refresh control reloads business layers; local mode restarts its demo.

Live mode initially reads `/api/zones`, `/api/assets` and `/api/buoys`, then falls back to `public/data/` and finally explicitly labeled example layers. Mock mode reads local/static layers only. Geometry and mock use the same files and zone IDs.

Example zones are not OSM features or official security boundaries; B supplies business layers. OSM attribution remains visible. Online tiles load only for the current viewport; no bulk prefetch is performed. The offline line map comes from a small Overpass vector extract, not bundled public raster tiles. See [OSM tile policy](https://operations.osmfoundation.org/policies/tiles/).

## A3: Security and human approval

In local mode choose Scenario A and 10×; mock options and a template recommendation appear after about 7 wall-clock seconds.

- Options show open-berth share, affected vessels, delay vessel-hours and residual risk exactly as supplied.
- The Agent's option has a star and is initially selected; an operator may select another option, including full closure.
- Hovering an option previews restricted zones; focusing an evidence zone highlights it in cyan.
- Mock approval emits `decision` and `zone_changed`; confirmed approval/time and zone colors follow those events. Restart Scenario A to demonstrate rejection, which does not close zones.
- Only one operation request is sent at a time. In live mode HTTP acceptance alone is not confirmation: the app waits for a structured `decision`.
- Errors release loading state and remain visible; failed requests are never presented as successes.
- Scenario, reset, mode, simulated network, pause/resume and speed controls use REST in live mode and local mock operations in mock mode.
- Simulated network loss changes `network`; it does not disable the computer's Wi-Fi. LIVE/MOCK and external-network state remain separate.
- Recent logs show source/severity. The risk strip draws weighted contributions without recomputing backend risk or levels.
- Selecting a target shows its own alert recommendation. A non-alert fish target does not inherit another target's recommendation.
- Detection evidence or the sonar-image control opens the supplied class, confidence, buoy, model, time and annotated image. `stub` is explicitly synthetic.
- Scenario restart clears prior selection, recommendations and confirmation. Replay blocks every POST.

REST wrappers live in `src/data/api.ts`. A3 automated checks use simulated service/event flows and are not a substitute for B/C browser integration.

## A4: above/below-water 3D

Choose **3D View** in live, mock or replay mode. Select a target from the scene control or click its model. Selection flies the camera to that target. Shore buildings, water, seabed, vessels, buoys, routes and risk zones share one business-coordinate system.

- 2D/3D share `selectedTrackId`. Switching views preserves selection. Scenario restart clears the target but retains the chosen 2D/3D view.
- Layers include water, NOAA seabed, USGS 3DEP shore elevations, USGS/USDA NAIP orthophotography, OSM shore/breakwater/quay lines, LA County building footprints, buoys/sonar cones, vessels/underwater targets, trails, warning columns and routes.
- Orthophotos use the same EPSG:4326 bounds and draw only within the NOAA land mask. Building bases sample local shore elevation.
- Overview, above-water, underwater, follow-selected and reset presets are available. New selections enter follow mode; the selector includes normal-level vessels.
- Flights last 1.5 seconds and update toward moving targets. Manual drag stops the current flight while follow mode retains target translation.
- Drag rotates, wheel zooms and right-drag pans. Independent layer controls toggle shore terrain/buildings, seabed, vessels, buoys, routes and risks.
- Water can be hidden or set to 5%–60% opacity. Its 0 m reference plane is **not live tide or an engineering datum tie**.
- Seabed grid and interpolated 2 m contours (10 m major contours highlighted) toggle independently. NoData cells are not bridged. A 2× bilinear display subdivision, smooth normals and depth colors improve legibility; original samples are unchanged and no rocks, trenches or measurements are invented. Sources above 150,000 samples do not receive extra subdivision. Contour/display spacing is not measurement accuracy.
- Layers, Display Settings, Data sources, target information and the bottom legend expand/collapse by mouse or keyboard. Most start collapsed; selecting a target opens its details. Collapse retains settings and playback. Essential source, reference-water and scale notices remain visible. Narrow canvases use Scene Settings; overview framing adapts to aspect ratio.
- Depth is positive down. Default **3× vertical exaggeration** improves a kilometer-scale overview. Choices are 1×/2×/3×/4×/8×, with Restore true scale (1×). The interface continuously labels exaggerated scale. Shore DEM/building bases/heights, seabed, contours and dynamic target depth use the same display factor; water remains 0 m. Business depth, coordinates and source elevations do not change. Scaling reuses geometry and adds no real-time shadow cost. It does not improve source accuracy or resolve vertical datums.
- The recorded 2026-10-18 regression passed build, lint, A1–A6, recovery and English checks. A4 covered scale/reset, retained source vertices, NoData boundaries and geometry reuse. Browser notes cover water/underwater/overview, reset, retained collapsed settings, selection, pause, cross-scenario replay and 2D/3D switching; file playback is not live-backend integration.
- Category-specific target meshes are enlarged 5×. Vessels include hull/heading/cabin/mast; fish use 30 instances. Position, heading, status and labels come from the current snapshot. Labels use backend depth, not enlarged mesh height.
- Trails are solid; predictions dashed. A dashed projection and surface ring connect target to water. Backend level determines colors.
- Positions update refs from the store each frame. Trails reuse GPU buffers rather than rebuilding all geometry every 200 ms.
- Simplified risk volumes reduce only warning-column complexity.
- The bottom bar identifies live backend/local simulation/file replay, scenario, simulation time, pause, selected target status/heading/speed/depth/risk. Replay uses the same reducer snapshot.
- Expanded legend/FPS panel reports an approximately one-second sampling window; `?mock=1&stats=1` enables statistics. Canvas pixel ratio is 1.5–2 and adapts to 85% under load without pixelated upscaling. DEM corners and business geometry share overview framing. Sustained performance needs the actual demo computer.
- 3D code loads on first use; labels need no external font and models/textures are not downloaded at runtime.
- Creation or WebGL-context failure offers retry and return to 2D; the other panels remain available.

A4 checks include coordinate scale, all vertical factors/reset, DEM metadata/range/NoData, interpolation/source preservation, building bounds, buoy pulse, deterministic motion/pause, camera presets/narrow framing, interpolation, retained selection and 1,500 real Three.js trail-buffer reuse cycles. They do not replace sustained GPU acceptance.

The recorded local browser run used Windows in-app Chromium, `?mock=1&stats=1`, 609×703, Scenario A, four targets, ten buoys and all layers. Shore data/imagery loaded; underwater/overview switching, hiding water and return to 2D worked. Forwarded Vite console output had no errors and one existing `THREE.Clock` deprecation warning. Sample windows ranged roughly 47–140 FPS, with changing layout/view. This is not 1920×1080 acceptance; target-resolution verification remains necessary.

### Multibeam provenance and replacement

Default `public/data/seabed-dem.json` crops [NOAA H12617](https://www.ngdc.noaa.gov/nos/H12001-H14000/H12617.html), acquired with a **Reson 7125 multibeam echosounder in 2013**. Final BAGs have native 1 m and 2 m spacing. The 1401×911 harbor display is approximately 8 m with 599,472 supported samples, 1.15–28.27 m below MLLW. `seabed-detail-mb.json` adds an aligned 1601×1409 local approximately 1 m patch. Of 542,742 supported samples, 541,854 have native 1 m support and 888 have native 2 m support; they are not new measurements. Unsupported cells stay NoData. Display spacing, source spacing and accuracy are distinct. See [MULTIBEAM-SOURCE.md](public/data/MULTIBEAM-SOURCE.md) for hashes, bounds, sign/CRS conversion, uncertainty and limitations.

Open **3D View → Underwater** for the patch. **Display Settings → Show water** hides the reference surface. Opacity, navigation, vertical scale and Reset View remain available. **Layers → 1 m display inspection patch (1–2 m source)** toggles the patch without resetting playback; the rest remains approximately 8 m. One-cell inward edge feathering changes opacity only. At narrow widths open Scene Settings. Source details identify historical acquisition, MLLW, unsupported coverage and unresolved shore datum alignment. [Earlier browser validation](MULTIBEAM-VALIDATION.md) concerns the previous 2 m patch; the denser revision needs its own browser/performance check.

Mock/fallback and newly generated synthetic replay share the [proposed sonar layout](SONAR-DEPLOYMENT.md). It is a corridor/flank reference deployment, not installed equipment. Head depth 3 m and 600 m rings are assumptions; no acoustic-occlusion/coverage model is claimed. Live/other recorded positions are not relocated or assigned invented depth. `npm.cmd run check:sonar` checks water support, route offsets and source consistency; `npm.cmd run make:replays` regenerates proposal/fixtures. B/C ping selection and actual imagery are outside that frontend change.

To regenerate official BAGs, install `scripts/requirements-bathymetry.txt` into `work/gis-python`, then run `npm.cmd run refresh:multibeam`. Normal frontend startup needs no Python. BAGs/dependencies stay in ignored `work/`. `refresh:noaa-bathy` overwrites with legacy regional CRM; `make:bathymetry` overwrites with synthetic terrain; neither regenerates MBES. `VITE_BATHYMETRY_URL` accepts version-1 survey JSON; custom sources disable the bundled detail patch, as do incompatible source/datum metadata. Provenance classification is not field acceptance. Water is fixed 0 m MLLW, not MSL/live tide. Native UTM11N/NAD83 meters are sampled to NAD83 geographic rows north-to-south, depth positive down; no realization-specific NAD83/WGS84 or spatial vertical transformation is applied.

### Shore elevations, imagery and buildings

`public/data/shore-dem-usgs-3dep.json` crops the [USGS 3DEP Elevation ImageServer](https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer). `shore-ortho-usgs-naip.png` is a matching [USGS National Map NAIP](https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer) orthophoto. `npm.cmd run refresh:shore-dem` regenerates both; `refresh:shore-imagery` updates imagery only after PNG/dimension validation, retaining old assets on network failure. The 512×278 EPSG:4326 elevation display has approximately 20–26 m spacing; it is not 1 m data even where the upstream service offers 1 m products. Imagery increased from 1536×834 to 3072×1668 (4× pixels), roughly 3.6–4.3 m/display pixel; this does not establish source acquisition resolution or positional accuracy. Service copyright is dated 2025-01-09, while local acquisition dates vary. Shore heights are meters positive up in NAVD88; NAIP is a mosaic, not live video.

**Vertical alignment remains unaccepted.** Shore is NAVD88; seabed/water is MLLW. No NOAA VDatum spatial transformation has been applied. Zero-offset display is not an engineering tie, tide or construction level. Regional 3DEP is not a site survey. Replacements must document CRS, vertical datum, units/sign, NoData and acquisition time; see `refresh-usgs-shore-dem.mjs` and the shore JSON format.

`public/data/lacounty-port-buildings.geojson` stores GISNET Public Countywide Building Outline (2023) data. Geometry is projected to EPSG:4326 and shares origin `(33.73, -118.26)` with ENU conversion. Native EPSG:2229 is US survey feet; `HEIGHT` converts by `1200/3937`. Bounds match DEM coverage; footprints above 10,000 square feet limit draw calls. This snapshot has 487 buildings; records without height are excluded. Extruded geometry is batched and follows vertical exaggeration.

Building bases sample USGS NAVD88 ground; the roof datum is unverified. Absolute alignment to MLLW remains unaccepted. These are measured footprints/heights, not detailed LiDAR roofs/facades. See [LA-COUNTY-BUILDINGS.md](public/data/LA-COUNTY-BUILDINGS.md); `npm.cmd run refresh:buildings` refreshes them. Review redistribution terms before external distribution.

## A5: Recovery, replay and offline fallback

In **local mock** Scenario B at 10×, the right panel appears after approximately 5 seconds. At simulation second 12 some example zones become clear; second 24 adds blocked zones and an initial plan; second 45 shows 6 clear, 3 unsurveyed and 1 blocked plus a template recommendation. These numbers belong only to the built-in **10-zone mock**, not live B or a real survey.

- 2D/3D share `clear / unsurveyed / blocked` and backend coverage.
- The panel displays the four `reopen_plan` ID groups and `est_hours_saved` unchanged; clicking an ID locates its 2D zone. The frontend does not recompute reopening or savings. Mock 4.5/9-hour values are preset simulation responses.
- Buoy fault injection simulates down/up. Gray hatching shows potential coverage impact without subtracting overlapping buoys; it is not B's authoritative blind-zone calculation.
- Network injection does not disable Wi-Fi. The banner follows actual `recommendation.model`, distinguishing template/local/unknown instead of claiming template output is a trained LoRA.
- `/api/metrics` displays supplied raw fields. Null yolo/lora shows no supplied evaluation; errors show unavailable. No metrics, units or training state are invented.
- Live sonar reads `/api/sonar/{det_id}.png`. Mock SVGs are annotated illustrations, not sonar measurements or YOLO outputs; the frontend runs no detector.

### Replay

The demo replay control opens `demo_b.jsonl`; `demo_a.jsonl` also includes detection, template and simulated approval. Both are generated by local mock, not B recordings.

- Each JSONL line is `{"wall_ms":1234,"msg":{...}}`; `msg` keeps shared StateMsg/EventMsg.
- Playback uses `wall_ms`, retaining file order for ties; play/pause, 1×/2× and seek are supported.
- Seeking rebuilds snapshots/logs/detections/options/recommendations/decisions/plans through the same reducer. Scenario boundaries clear obsolete caches.
- Replay blocks all POST in both UI and request layers, starts no WebSocket, reads no live metrics and requests no online OSM tiles.
- Images live under `public/` with root-relative paths. Absolute backend URLs map to `/sonar/{det_id}.png`; absent images raise errors rather than going online.
- Missing files, reversed `wall_ms`, absent snapshots and invalid JSON raise errors without silent mock fallback. Limits: 30 MB and 200,000 messages.
- `npm.cmd run make:replays` regenerates explicitly synthetic fixtures; it does not replace B recordings.

### Local OSM and network limits

`public/data/harbor-osm.geojson` has 407 extracted shoreline/quay/breakwater/major-road features. See `public/data/OSM-SOURCE.md`. Offline-map selection, replay, simulated offline network or tile errors use this vector outline. It lacks full labels, feature fills and zoom-level tiles; outside the crop there is no additional basemap. Business zones and OSM provenance remain distinct.

Actual Wi-Fi-loss refresh requires the local development/preview server to stay running. Data, images, shoreline and 3D dependencies are local; this is not a PWA that works after server shutdown. Real disconnected-browser refresh remains a separate acceptance item. The taskbook's complete PMTiles/cached-basemap approach is not implemented. OSM public tiles forbid offline bulk prefetch; the outline is a lawful fallback, not equivalent acceptance for a full offline map package.

## A6: presentation and recording

Build and preview, then open **Demo preparation**.

- The panel reports viewport and offers fullscreen. Target projection is 1920×1080; readability at three meters still requires the actual projector.
- The three-minute synthetic replay spends its first 80 seconds in A, simulates approval at 70 seconds, switches to B at 80 seconds, reaches its final plan around 125 seconds, then injects buoy/network faults.
- Recording requires the user to click the recording control and personally select the HarborGuard tab in the browser picker. The request is 1920×1080, 30 fps, no audio, capped at 180 seconds/120 MB.
- Preview and download before closing or refreshing. Video stays in local memory and the chosen download folder; it is not uploaded or written to Git automatically.
- Use OBS/system recording for unsupported tab capture, system audio or incompatible formats. Browser output is commonly WebM; test on the demo computer and shared destination.
- Level-3 badges/targets/map markers flash. With no alerts, the app shows normal status. Backend disconnection shows reconnect without a blank screen. Optional audio alerts were not implemented.

The three-minute fixture proves neither live-backend integration, real network behavior nor local LoRA acceptance. Recording was cancelled by the user in the recorded acceptance; no recording or cross-device playback is claimed.

## Configuration and integration

### Refresh recovery and debris evidence

After the first WebSocket state, live mode reads `GET /api/events?since_seq=0` and `GET /api/log`, rebuilds timeline/options/detections/recommendations/decisions and merges arriving WebSocket messages. Stable recommendation/detection/alert IDs are preferred for deduplication; other events use `seq/event/t`. Current alerts with `options_ready` and tracks with `detection_id` also trigger existing detail requests. A reconnect snapshot below the previous connection's sequence indicates a backend restart; derived old-session state is cleared and unconfirmed prior history is disclosed. Refresh never reposts operations.

Contract v1 exposes at most 500 current cached events, without separate decision/recommendation lists or older-history pagination. A full 500-item response shows incomplete history; request/detail failures show degraded recovery. The recorded 2026-10-18 source review found structured, persisted `decision` for both approval and rejection; the old rejection-is-log-only statement is obsolete. Persistence does not make old approvals pageable under the frozen API. That review's port 8000 was offline, so it did not reverify runtime. For old/missing events the UI keeps status unconfirmed after HTTP success and prevents duplicate submission until structured confirmation arrives. It never derives approval from free-text logs. See `B-HANDOFF.md` and `ACCEPTANCE-A.md` for scoped evidence.

Recovery's debris-evidence entry lists only received `detection.cls === "debris"` records. Opening one shows its supplied class/confidence/buoy/model/time/image. Empty state is explicit; `model: "stub"` is labeled demo identification.

Copy the frontend `.env.example` to local-only `.env.local`:

```dotenv
VITE_API_BASE=http://localhost:8000/api
VITE_WS_URL=ws://localhost:8000/ws
VITE_BATHYMETRY_URL=/data/seabed-dem.json
```

Defaults target localhost:8000. Integration order: start B → health → frontend without query parameters → LIVE → Scenario A/B → 3D → select vessel and inspect position/heading/time → pause/resume → browser console. Use `?mock=1` without B, or `?replay=demo_full.jsonl` for deterministic synthetic playback. LIVE/MOCK/REPLAY remain explicit.

### APIs

- WebSocket: `GET /ws`, complete `state` and discrete `event`.
- GET: `/api/health`, `/state`, `/events`, `/zones`, `/assets`, `/buoys`, `/tracks/{id}`, `/alerts/{id}`, `/detections/{id}`, `/options/{alert_id}`, `/metrics`, `/log`, `/sonar/{det_id}.png` (all paths after the first also have the `/api` prefix).
- POST: `/api/scenario/{a|b}/start`, `/control`, `/mode`, `/inject`, `/decision`, `/recommendations`, `/log`, `/agent/ask` (same prefix convention).

REST errors stay visible while the app remains usable. Geometry falls back to static then labeled examples. Replay forbids POST. B static files belong in `public/data/`. Update `src/types/contract.ts` only against B's frozen contract; do not invent transport fields.

For Mac four-process startup, occupied-port protection, stopping and the four-minute live flow, see [mac-demo-runbook.md](../docs/mac-demo-runbook.md).

## Checks

```powershell
npm.cmd run build
npm.cmd run lint
npm.cmd run check:a1
npm.cmd run check:a2
npm.cmd run check:a3
npm.cmd run check:a4
npm.cmd run check:a5
npm.cmd run check:a6
npm.cmd run check:recovery
npm.cmd run check:english
npm.cmd run check:vessels
```

| Check | Scope |
| --- | --- |
| a1 | Event timing, mock approval, selection, pause/speed/reset, cache limits, WS reconnect |
| a2 | Coordinates, 36-point error ellipse, GeoJSON holes/multipolygons, example layers, file/API cache, B IDs, offline events, five-minute simulation |
| a3 | Approve/reject, option selection, alert context, risk contributions, controls, replay lock, event confirmation, HTTP errors, duplicate guard, reset |
| a4 | Coordinates, all vertical factors/reset, bounds, presets/narrow framing, 1.5-second interpolation/pulses, DEM metadata/NoData/relief/subdivision/contours, selection, GPU attributes |
| a5 | Recovery presets/raw plans, OSM provenance, sonar paths, raw/null metrics, JSONL validation/seek/reset/wall time/pause/2×/restart, POST locks and cleanup |
| a6 | Three-minute fixture, scene/approval/plan/fault timing, recorder limits/format/stop/cancel/cleanup |
| recovery | Delayed REST vs WS logs, restored decisions, stable IDs, fixed initial sequence baseline, restart detection, stale-request isolation, 500-event partial recovery |
| english | English UI and known recorded messages, retaining source IDs |
| vessels | NOAA water mask, speed/components/heading/displacement, turns/acceleration/stopping/north crossing, history/prediction/pause/reset/seeking |

Automated checks do not replace live browser or physical projection/network acceptance. Vessel fixtures use up to 3.8 m/s, 40 m route offsets, two-second history (60 points) and ten-second prediction samples to 100 seconds from one deterministic model. They are synthetic traffic, not AIS, collision avoidance or official navigation rules. T1's dramatic alert pacing is unchanged; vessel checks do not establish realistic UUV dynamics. Temporary `work/` output is ignored.

## Production preview and remaining acceptance

```powershell
npm.cmd run build
npm.cmd run preview
```

Use the printed preview port. Before delivery, verify actual projection, Wi-Fi-loss refresh, sustained 3D FPS and the current B/C combination. A short 1920×1080 browser check is not field projection acceptance. A6 remains conditionally demonstrable and not fully accepted; see `ACCEPTANCE-A.md`.
