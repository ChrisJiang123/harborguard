# NOAA H12617 multibeam bathymetry

The default seabed is now **survey-derived multibeam bathymetry**, not CRM,
CoNED, an ordinary land DEM, a backscatter image, or procedural terrain.

- Survey: [H12617, San Pedro and Vicinity](https://www.ngdc.noaa.gov/nos/H12001-H14000/H12617.html).
- Acquisition: 2013-09-13 to 2013-11-03 (survey catalog); archived BAG packaging 2019-09-26 is NOT the acquisition date.
- Instrument: Reson 7125 MBES. Historical finalized grids, not raw sonar pings or current port soundings.
- Products: `H12617_MB_1m_MLLW_1of2.bag` and `H12617_MB_2m_MLLW_2of2.bag` from the catalog's **Bathymetry** section. 1 m is preferred wherever all support cells are valid; otherwise the measured 2 m product is used. No other terrain fills gaps.
- NOAA catalog license: CC0-1.0. NOAA explicitly says these products are **not for navigation**.

## Coordinates, sign and reference plane

Native BAG horizontal coordinates: NAD83 / UTM zone 11N (EPSG:26911), metres.
BAG metadata locates pixel centers, rows south-to-north. `pyproj` transforms
sample coordinates to NAD83 geographic (EPSG:4269); exported frontend rows run
north-to-south. The app's shared local ENU display still has no
realization-specific NAD83/WGS84 correction.

The BAG elevation band uses negative, upward-positive elevations relative to
MLLW. Frontend `depth = -elevation`, metres positive down. Original missing value
`1e6` is rejected **before** bilinear interpolation; all four support values
must be valid. Missing/unsupported/land samples export as `-9999`.

Water is the fixed **0 m MLLW demonstration reference**, NOT MSL, current tide,
or a real-time observed surface. Shore elevations remain NAVD88. No spatial
MLLW/NAVD88 transformation has been applied. Do not use their visual juxtaposition
as an engineering elevation tie. Survey-specific tide/epoch documentation and
local datum/field checks remain necessary. The generic BAG vertical-CRS remarks
alone do not establish a location/epoch-specific transformation.
Business target depths keep their existing source semantics; no backend-depth
datum conversion has been introduced. Real-target/survey datum alignment requires
separate source confirmation before safety or engineering interpretation.

## Display products and LOD

| File | Grid | Approximate display sampling | Survey-supported samples |
| --- | --- | --- | --- |
| `seabed-dem.json` | 1401×911 | 7.94×7.95 m | 599,472 (46.97% of rectangle) |
| `seabed-detail-mb.json` | 1601×1409 | 0.99×0.99 m | 542,742 (24.06% of rectangle) |

The harbor crop is west -118.31, south 33.70, east -118.19, north 33.765.
The local patch surrounds the existing underwater inspection view. Its edges
align with harbor-grid samples (8 subdivisions per coarse edge). Coarse faces
and contours under the patch are removed; colors share the same scale. The
patch is not a separate simulation. Outside it the harbor retains ~8 m sampling.
This is **not** a whole-harbor 1 m display or a guarantee of 1 m accuracy.
Native resolution counts are now embedded: local patch 541,854 samples with 1 m
support and 888 with 2 m support; interpolating the latter does not create new
1 m observations. One-cell inward display feathering softens NoData silhouettes
without changing coordinates/depths or adding coverage. See
[sonar/layout and data-discovery notes](../../SONAR-DEPLOYMENT.md) for newer
0.5 m Long Beach surveys and their location limitations.

Per-product BAG SHA-256, native grid/origin, crop windows, display-value SHA-256,
NoData counts, bounds, and source provenance are embedded in each JSON metadata.
The productUncert band is read while generating the subsets. Metadata records
the range of maximum support-cell uncertainties; this is **not** project RMSE,
newly estimated uncertainty, or a navigation certification. Original per-cell
uncertainty remains available in the BAG, not silently converted into accuracy.

## Reproduce / replace

```powershell
python -m pip install --target work/gis-python -r scripts/requirements-bathymetry.txt
npm.cmd run refresh:multibeam
npm.cmd run check:a4
```

Use an installed Python 3.12+ executable in place of `python` if needed. Original
BAGs (~227 MiB combined) and native subsets stay in ignored `work/bag-cache/`.
Generation validates metadata, sign, dimensions, coverage and support cells
before exporting. No source BAG, binary download cache or Python package is
committed. `npm install` alone is sufficient to run the app using bundled JSON;
Python is only needed to regenerate data.

To replace the survey, use a documented MBES BAG/GeoTIFF/XYZ grid with known CRS,
vertical datum, units/sign, survey time, quality/uncertainty and NoData. Convert
offline to the existing version-1 JSON. For a custom `VITE_BATHYMETRY_URL`, the
bundled H12617 detail patch is disabled. Never relabel an interpolated regional
DEM or ordinary land DEM as multibeam. Newer Long Beach surveys found in NOAA's
catalog (e.g. W00711, 2024, 0.5 m) are **not integrated here** and cannot be assumed
to cover the west-port demo merely from their product name.

Legacy `refresh:noaa-bathy` overwrites the main JSON with the old regional CRM;
`make:bathymetry` overwrites it with synthetic terrain. Neither is the default
multibeam regeneration command. Detail loading rejects different source/datum
metadata, so those commands cannot silently retain a mismatched MBES patch.
