# Raster shoreline teeth follow-up — 2026-10-17 PDT

The user's near-quay screenshot exposed geometry aliasing that framebuffer AA
cannot remove. The ~4.8 m land DEM was classified using a coarser regional
topobathy mask; its boundary was still a staircase. Nearest-floor closure panels
also fanned sideways and used separate face normals.

## Changes and limits

- Trace the actual four-corner-supported land mesh boundary into contours.
  Simplify within 10 m, then displace only a narrow land-side band. Keep crop
  edges and NoData pinned, and constrain every incident triangle's orientation.
  Narrow features that cannot move safely retain their original shape.
- Land and quay tops share the same vertices. Quay panels extend vertically;
  their smooth normals follow shared contour tangents. A separately shaded,
  hatched submerged apron closes to the supported model floor. Quay and apron
  batches add only two draw calls in total, not one draw call per boundary edge.
- The independent Display Settings checkbox **Reconstruct raster shoreline
  (illustrative, ≤10 m)** defaults on. Existing land smoothing, quay, water and
  rendering controls remain separate. The data legend declares reconstruction
  illustrative. All navigation, simulation, water-reference and vertical-scale
  disclaimers remain.

This is a bounded approximation of the existing raster outline, **not newly
surveyed shoreline geometry or additional source accuracy**. It does not install
CUDEM or a new vector shoreline. Source land heights/NoData and both H12617
files are unchanged. Land NAVD88, regional MSL and survey MLLW retain zero
offset; no new datum conversion is claimed. Measured steep slopes and source
relief remain visible, particularly at 3×. Residual constrained corners and
low-resolution imagery are not claimed to be eliminated.

## Verification

- Production build / strict TypeScript, lint, `check:a4`, diff whitespace checks.
- Full bundled land grid: sharp turns (>60° between boundary segments) **7,814 →
  789**; maximum horizontal displacement **9.999 m**; zero inverted faces,
  unchanged source heights, mask and crop coordinates. This metric is geometry
  complexity, not a survey-accuracy or image-quality score. Collinear/very small
  faces are allowed; topology and the indexed land domain stay connected.
- Native geometry diagnostic completed in approximately 0.35 seconds on this
  machine; it runs only when the terrain/outline setting changes, not every
  200 ms state snapshot. Changing the setting rebuilds the land mesh and may
  briefly lower the FPS readout; this is excluded from steady-view samples.
- In-app Chromium on this Mac, **1920×1080 dashboard**, **1220×760 CSS canvas**,
  **1830×1140 drawing buffer**, default effects and vertical 3×. Running local
  simulated Scenario A: eight one-second UI samples per view. Underwater mean
  **61.1 FPS**, minimum **59**; Surface mean **48.8 FPS**, minimum **48**.
  [Raw samples](browser-samples.json). This is a short check, not a sustained
  thermal test or a full 1920×1080 canvas benchmark. Earlier report measurements
  used a different browser setup and are not a matched FPS comparison.
- Surface/Underwater, repeated zoom, reconstruction off/on and source labels
  checked in the browser. Captured console errors: none. Backend, business
  rules, Scenario A/B definitions and model services were not changed.

## Same-camera visual check

Paused local simulated Scenario A at 01:11, Surface preset followed by 24 zoom
events, vertical 3×. Same 940×230 screenshot crop at x=570, y=540 of a 1920×1080
viewport. Only the reconstruction checkbox differs; **both pictures already
include the new quay panel/shading implementation**. These images isolate the
contour change, not the entire follow-up versus its parent commit.

Raster outline, reconstruction off:

![Original raster outline](contour-off.png)

Reconstructed outline, on:

![Continuous display outline](contour-on.png)
