#!/usr/bin/env python3
"""Offline regional display layer; never rewrites H12617 or its NoData.

python scripts/prepare-shore-fill.py --fetch-crm
python scripts/prepare-shore-fill.py --regional work/coastal/crm.json
python scripts/prepare-shore-fill.py --regional /offline/cudem.tif --datum NAVD88
python scripts/prepare-shore-fill.py --regional /offline/cudem.tif --datum NAVD88 --fallback work/coastal/crm.json

GeoTIFF input is cropped/reprojected to the existing harbor grid. CUDEM is
preferred when a locally verified Southern California tile is available. The
NOAA 8483 public URL list checked for this revision has no Los Angeles tile.
Dependencies: numpy, scipy; rasterio only for GeoTIFF input.
"""
import argparse
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import numpy as np
from scipy.ndimage import convolve, distance_transform_edt, map_coordinates

ROOT = Path(__file__).resolve().parents[1]
CRM_URL = ('https://www.ngdc.noaa.gov/thredds/dodsC/crm/'
           'crm_socal_1as_vers2.nc.ascii?Band1%5B9720:1:9954%5D%5B16884:1:17316%5D')
NODATA = -9999


def resample(values, bounds, target, shape):
    """Bilinear with explicit all-support mask; NoData never enters arithmetic."""
    rows = np.linspace(target['north'], target['south'], shape[0])
    cols = np.linspace(target['west'], target['east'], shape[1])
    y = (bounds['north'] - rows) / (bounds['north'] - bounds['south']) * (values.shape[0]-1)
    x = (cols - bounds['west']) / (bounds['east'] - bounds['west']) * (values.shape[1]-1)
    yy, xx = np.meshgrid(y, x, indexing='ij')
    mask = np.isfinite(values)
    weight = map_coordinates(mask.astype(float), [yy, xx], order=1, mode='constant', cval=0)
    sampled = map_coordinates(np.where(mask, values, 0), [yy, xx], order=1, mode='constant', cval=0)
    return np.where(weight > .999999, sampled, np.nan)


def smooth_masked(values):
    kernel = np.outer([1., 2., 1.], [1., 2., 1.])
    mask = np.isfinite(values)
    weights = convolve(mask.astype(float), kernel, mode='nearest')
    sums = convolve(np.where(mask, values, 0), kernel, mode='nearest')
    return np.where(mask, sums / np.maximum(weights, 1), np.nan)


def fetch_crm(path):
    with urllib.request.urlopen(CRM_URL, timeout=60) as response:
        raw = response.read().decode()
    section = re.split(r'Band1\.Band1\[\d+\]\[\d+\]\s*\n', raw)[1]
    rows = [np.fromstring(m[1], sep=',') for m in re.findall(r'^\[(\d+)\],\s*(.*)$', section, re.M)]
    elevations = np.array(rows, dtype=float)[::-1]
    assert elevations.shape == (235, 433), 'Unexpected CRM crop'
    def axis(name):
        return np.fromstring(re.search(r'Band1\.'+name+r'\[\d+\]\s*\n([^\n]+)', raw)[1], sep=',')
    lat, lon = axis('lat'), axis('lon')
    metadata = dict(width=433, height=235, bounds=dict(west=float(lon[0]), east=float(lon[-1]),
                    south=float(lat[0]), north=float(lat[-1])), nodata_value=NODATA,
                    source='NOAA/NCEI Southern California Coastal Relief Model v2, 1 arc-second',
                    source_url='https://www.ncei.noaa.gov/products/coastal-relief-model',
                    vertical_datum='MSL (NOAA Southern California CRM v2)', elevation_positive='up')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(metadata=metadata, values=elevations.ravel().tolist())))


def read_regional(path, target, shape, datum, nodata_override=None):
    if path.suffix.lower() in ('.tif', '.tiff'):
        import rasterio
        from rasterio.warp import reproject, Resampling, transform_bounds
        from rasterio.transform import from_bounds
        from rasterio.windows import Window, from_bounds as window_from_bounds
        # Target bounds describe sample centres; expand half a pixel for GDAL.
        dx = (target['east']-target['west'])/(shape[1]-1)
        dy = (target['north']-target['south'])/(shape[0]-1)
        transform = from_bounds(target['west']-dx/2, target['south']-dy/2,
                                target['east']+dx/2, target['north']+dy/2, shape[1], shape[0])
        with rasterio.open(path) as ds:
            if not datum:
                raise ValueError('GeoTIFF requires --datum from source metadata; never guess a vertical CRS')
            nodata = nodata_override if nodata_override is not None else ds.nodata
            if ds.crs is None or nodata is None:
                raise ValueError('GeoTIFF requires a CRS and explicit NoData metadata (or --nodata); never guess a missing-value sentinel')
            out = np.full(shape, np.nan, dtype=np.float32)
            # Read only the scene crop plus interpolation halo, not a full tile.
            extent = transform_bounds('EPSG:4326', ds.crs, target['west'], target['south'], target['east'], target['north'])
            w = window_from_bounds(*extent, transform=ds.transform)
            window = Window(np.floor(w.col_off)-2, np.floor(w.row_off)-2, np.ceil(w.width)+4, np.ceil(w.height)+4)
            try:
                window = window.intersection(Window(0, 0, ds.width, ds.height))
            except rasterio.errors.WindowError:
                return out, dict(source=f'Local regional GeoTIFF: {path.name} (no scene coverage)', vertical_datum=datum)
            raw = ds.read(1, window=window).astype(np.float32)
            valid = np.isfinite(raw) & (raw != nodata)
            # Decode scaled Int16/Float32 explicitly BEFORE resampling. Masked
            # samples never participate as zero, -9999 or a scaled extreme.
            source = np.where(valid, raw*ds.scales[0]+ds.offsets[0], np.nan).astype(np.float32)
            reproject(source, out, src_transform=ds.window_transform(window), src_crs=ds.crs,
                      src_nodata=np.nan, dst_transform=transform, dst_crs='EPSG:4326',
                      dst_nodata=np.nan, resampling=Resampling.bilinear)
        return out, dict(source=f'Local regional GeoTIFF: {path.name} (source provenance not verified)', vertical_datum=datum)
    document = json.loads(path.read_text())
    m = document['metadata']
    data = np.array(document['values'], dtype=float).reshape(m['height'], m['width'])
    data[data == m['nodata_value']] = np.nan
    if m.get('depth_positive') == 'down':
        data = -data
    return resample(data, m['bounds'], target, shape), m


def blend_fill(regional_depth, measured_depth, spacing, transition_m):
    """Only unmeasured cells transition. Boundary vertices retain surveyed depth.

    Source reference remains MSL/NAVD88 as declared. Offset = 0 m, NO datum
    transformation: this interpolation is a visual tie, never a surveyed tie.
    """
    measured = np.isfinite(measured_depth)
    if not measured.any():
        return regional_depth.copy()
    distance, nearest = distance_transform_edt(~measured, sampling=spacing, return_indices=True)
    nearest_depth = measured_depth[tuple(nearest)]
    t = np.clip(distance / transition_m, 0, 1)
    t = t*t*(3-2*t)
    fill = nearest_depth*(1-t) + regional_depth*t
    return np.where(measured, measured_depth, fill)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch-crm', action='store_true')
    parser.add_argument('--regional', type=Path, help='Local GeoTIFF or version-1 JSON; defaults to the bundled CRM crop')
    parser.add_argument('--datum')
    parser.add_argument('--nodata', type=float, help='Explicit source NoData for a GeoTIFF lacking that metadata')
    parser.add_argument('--source-title', help='Source title from the supplied GeoTIFF catalogue/metadata')
    parser.add_argument('--source-url', help='Provenance URL for the supplied regional source')
    parser.add_argument('--fallback', type=Path, help='Lower-priority CRM crop for uncovered CUDEM locations')
    parser.add_argument('--transition-m', type=float, default=32)
    parser.add_argument('--output', type=Path, default=ROOT/'public/data/seabed-fill-regional.json')
    args = parser.parse_args()
    if args.regional is None:
        args.regional = ROOT/('work/coastal/crm.json' if args.fetch_crm else 'scripts/fixtures/crm-socal-crop.json')
    if not 20 <= args.transition_m <= 50:
        parser.error('Transition must be 20–50 m')
    if args.fetch_crm:
        fetch_crm(args.regional)
    survey_path = ROOT/'public/data/seabed-dem.json'
    survey = json.loads(survey_path.read_text())
    m = survey['metadata']
    shape = (m['height'], m['width'])
    measured = np.array(survey['values'], dtype=float).reshape(shape)
    measured[measured == m['nodata_value']] = np.nan
    regional, provenance = read_regional(args.regional, m['bounds'], shape, args.datum, args.nodata)
    if args.source_title:
        provenance = dict(provenance, source=args.source_title)
    if args.source_url:
        provenance = dict(provenance, source_url=args.source_url)
    fallback_provenance = None
    spacing = (m['approximate_spacing_m']['north_south'], m['approximate_spacing_m']['east_west'])
    if args.fallback:
        fallback, fallback_provenance = read_regional(args.fallback, m['bounds'], shape, None)
        # CUDEM > CRM. Retain both native references explicitly; this display
        # transition must never be described as a vertical-datum transformation.
        regional = -blend_fill(-smooth_masked(fallback), -regional, spacing, args.transition_m)
        provenance = dict(provenance, source=provenance['source']+' > '+fallback_provenance['source'],
                          vertical_datum='Untransformed regional references: '+provenance['vertical_datum']+' / '+fallback_provenance['vertical_datum'])
    # Smooth regional relief before display exaggeration. Land remains masked.
    regional_depth = -smooth_masked(regional)
    regional_depth[(regional_depth <= 0) | ~np.isfinite(regional)] = np.nan
    values = blend_fill(regional_depth, measured, spacing, args.transition_m)
    # The new JSON also supplies the WATER mask, so preserve valid survey water.
    values = np.where(np.isfinite(measured), measured, values).astype(np.float32)
    valid = np.isfinite(values)
    # Decimal serialization at 0.1 mm avoids verbose binary-float tails. Runtime
    # positions remain Float32; this is not an 8-bit normalized height texture.
    exported = np.round(np.where(valid, values, NODATA).astype(float), 4).ravel().tolist()
    metadata = dict(title='Regional nearshore display fill — not surveyed', source_kind='regional_dem',
                    source=provenance['source'], source_url=provenance.get('source_url'),
                    horizontal_crs='EPSG:4326', horizontal_units='degrees', vertical_units='m',
                    vertical_datum=provenance['vertical_datum'], depth_positive='down', reference_water_level_m=0,
                    reference_water_level_note='Water 0 m (reference, not live tide). Regional datum untransformed; visual edge tie to H12617 MLLW only.',
                    datum_conversion=dict(applied=False, offset_m=0, reason='No source/epoch-specific verified datum grid supplied; do not infer a NAVD88/MSL/MLLW engineering tie.'),
                    width=m['width'], height=m['height'], bounds=m['bounds'], nodata_value=NODATA,
                    approximate_spacing_m=m['approximate_spacing_m'], native_resolution='1 arc-second CRM (~26×31 m); finer display sampling is interpolation' if args.regional.suffix == '.json' else 'See input GeoTIFF metadata; display sampling is not accuracy',
                    min_depth_m=float(values[valid].min()), max_depth_m=float(values[valid].max()), nodata_cells=int((~valid).sum()),
                    display_processing='Masked 3×3 Gaussian on regional elevations; distance-field edge interpolation into unmeasured cells only',
                    transition_m=args.transition_m, survey_sha256=hashlib.sha256(survey_path.read_bytes()).hexdigest(),
                    input_sha256=hashlib.sha256(args.regional.read_bytes()).hexdigest(),
                    fallback_source=fallback_provenance,
                    fallback_sha256=hashlib.sha256(args.fallback.read_bytes()).hexdigest() if args.fallback else None,
                    intended_use='Regional model fill (not surveyed). Not for navigation. H12617 data are untouched; renderer excludes survey-supported cells.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(dict(version=1, metadata=metadata, values=exported), separators=(',', ':'))+'\n')
    print(f'Wrote {args.output}: {int(valid.sum())} water-mask vertices; survey samples unchanged')


if __name__ == '__main__':
    main()
