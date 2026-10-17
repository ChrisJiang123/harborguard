"""Build a frontend-only NOAA multibeam BAG subset; no backend/contracts touched.

Dependencies: numpy, h5py, pyproj. Original BAGs stay in ignored work/bag-cache.
"""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'work/gis-python'))
import hashlib
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import h5py
import numpy as np
from pyproj import Transformer

CACHE = ROOT / 'work/bag-cache'
CACHE.mkdir(parents=True, exist_ok=True)
BASE = 'https://data.ngdc.noaa.gov/platforms/ocean/nos/coast/H12001-H14000/H12617/'
FILES = ['H12617_MB_1m_MLLW_1of2.bag', 'H12617_MB_2m_MLLW_2of2.bag']

def download(url, target):
    if target.exists():
        return
    print('Downloading', url, flush=True)
    temporary = target.with_suffix('.partial')
    with urllib.request.urlopen(url, timeout=60) as response, temporary.open('wb') as output:
        expected = int(response.headers.get('Content-Length', 0))
        if not 0 < expected <= 250_000_000:
            raise ValueError(f'Unexpected download size: {expected}')
        total = 0
        while block := response.read(1024*1024):
            total += len(block)
            if total > expected:
                raise ValueError('Download exceeds declared length')
            output.write(block)
        if total != expected:
            raise ValueError('Incomplete BAG download')
    temporary.replace(target)

NS = {'gmd': 'http://www.isotc211.org/2005/gmd', 'gco': 'http://www.isotc211.org/2005/gco', 'gml': 'http://www.opengis.net/gml/3.2'}

def sample_bag(path, lon, lat):
    with h5py.File(path, 'r') as bag:
        raw = b''.join(bag['BAG_root/metadata'][:]).rstrip(b'\0')
        metadata = ET.fromstring(raw)
        text = raw.decode()
        assert 'NAD83 / UTM zone 11N' in text and 'MLLW depth' in text and 'AXIS["Up",UP]' in text
        grid = metadata.find('.//gmd:MD_Georectified', NS)
        corners = grid.find('.//gml:coordinates', NS).text.split()
        x0,y0 = map(float,corners[0].split(','))
        x1,y1 = map(float,corners[1].split(','))
        sizes = [int(n.text) for n in grid.findall('.//gmd:dimensionSize/gco:Integer', NS)]
        spacing = [float(n.text) for n in grid.findall('.//gmd:resolution/gco:Measure', NS)]
        assert sizes == list(bag['BAG_root/elevation'].shape)
        # BAG rows run SOUTH -> NORTH. Upper corner is an exclusive bound.
        sy,sx = spacing
        assert abs((x1-x0)/sx-sizes[1]) < .001 and abs((y1-y0)/sy-sizes[0]) < .001
        x,y = Transformer.from_crs(4269,26911,always_xy=True).transform(lon,lat)
        px,py = (x-x0)/sx,(y-y0)/sy
        a,b = np.floor(px).astype(int),np.floor(py).astype(int)
        tx,ty = px-a,py-b
        inside = (a>=0)&(b>=0)&(a+1<sizes[1])&(b+1<sizes[0])
        left,right = max(0,int(a.min())), min(sizes[1],int(a.max())+2)
        bottom,top = max(0,int(b.min())), min(sizes[0],int(b.max())+2)
        elevation = bag['BAG_root/elevation'][bottom:top,left:right]
        uncertainty = bag['BAG_root/uncertainty'][bottom:top,left:right]
        ca,cb = np.clip(a-left,0,elevation.shape[1]-2),np.clip(b-bottom,0,elevation.shape[0]-2)
        samples = np.stack([elevation[cb,ca], elevation[cb,ca+1], elevation[cb+1,ca], elevation[cb+1,ca+1]])
        # BAG missing value is 1e6; check before interpolation, not afterwards.
        valid = inside & np.isfinite(samples).all(axis=0) & (samples<0).all(axis=0) & (samples>-200).all(axis=0)
        z = (samples[0]*(1-tx)+samples[1]*tx)*(1-ty)+(samples[2]*(1-tx)+samples[3]*tx)*ty
        u = np.stack([uncertainty[cb,ca],uncertainty[cb,ca+1],uncertainty[cb+1,ca],uncertainty[cb+1,ca+1]])
        # Conservative support-cell maximum, NOT interpolated uncertainty or RMSE.
        quality = np.where(np.isfinite(u).all(axis=0)&(u<1000).all(axis=0)&(u>=0).all(axis=0),u.max(axis=0),-9999)
        return -z,valid,quality,{'file':path.name,'url':BASE+'BAG/'+path.name,'sha256':hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),'grid_spacing_m':sx,'native_shape':sizes,'native_origin_sw_m':[x0,y0],'native_bounds_utm_m':[x0,y0,x1,y1],'cropped_window':[left,bottom,right,top],'source_nodata':1000000,'valid_output_samples':int(valid.sum())}

def export(bounds, width, height, name):
    lon,lat = np.meshgrid(np.linspace(bounds['west'],bounds['east'],width),np.linspace(bounds['north'],bounds['south'],height))
    depth = np.full((height,width),-9999,dtype=float)
    uncertainty = np.full_like(depth,-9999)
    provenance = []
    # Coarser measured 2 m product first; prefer 1 m where all support cells exist.
    for file in reversed(FILES):
        values,valid,quality,source = sample_bag(CACHE/file,lon,lat)
        depth[valid],uncertainty[valid] = values[valid],quality[valid]
        provenance.append(source)
    valid = depth!=-9999
    assert valid.sum()>width*height*.1, 'Survey does not meaningfully cover the requested crop'
    values = [int(v) if v.is_integer() else v for v in (round(float(v),2) for v in depth.flat)]
    supported = np.array(values)[valid.ravel()]
    quality = uncertainty[(uncertainty>=0)&valid]
    spacing = {'east_west': round((bounds['east']-bounds['west'])*111320*np.cos(np.deg2rad(lat.mean()))/(width-1),2),'north_south':round((bounds['north']-bounds['south'])*111320/(height-1),2)}
    document = {'version':1,'metadata':{
        'title':'NOAA H12617 multibeam bathymetry — San Pedro and vicinity (2013)',
        'source_kind':'survey','measurement_method':'multibeam_echosounder','survey_id':'H12617','instrument':'Reson 7125 MBES',
        'source':'NOAA/NOS H12617 (2013-09-13 to 2013-11-03), Reson 7125 multibeam; 1 m and 2 m finalized BAG products (2019 packaging). Historical archive, not present-day port conditions.',
        'source_url':'https://www.ngdc.noaa.gov/nos/H12001-H14000/H12617.html','source_products':provenance,
        'retrieved_at':datetime.now(timezone.utc).isoformat(),'horizontal_crs':'EPSG:4269','horizontal_units':'degrees','source_horizontal_crs':'EPSG:26911',
        'horizontal_transform':'pyproj NAD83 UTM11N -> NAD83 geographic; geographic NAD83 displayed in local ENU without realization-specific WGS84 correction.',
        'vertical_units':'m','vertical_datum':'MLLW (H12617 survey)','source_elevation_positive':'up','depth_positive':'down','source_spacing_m':1,
        'reference_water_level_m':0,'reference_water_level_note':'0 m MLLW demonstration reference, NOT MSL or live tide. Land remains NAVD88; no spatial vertical datum transformation applied. Do not infer precise shore/seabed elevation ties.',
        'nodata_value':-9999,'nodata_rule':'BAG 1e6, unsupported samples and missing support cells remain -9999; all four corners required; no CRM/CoNED/synthetic infill. 1 m measured product takes priority over 2 m measured product.',
        'width':width,'height':height,'bounds':bounds,'approximate_spacing_m':spacing,'min_depth_m':float(supported.min()),'max_depth_m':float(supported.max()),'nodata_cells':int((~valid).sum()),
        'coverage_percent':round(float(valid.mean()*100),2),'uncertainty_support_max_range_m':[round(float(quality.min()),3),round(float(quality.max()),3)],
        'uncertainty_note':'Range of maximum BAG productUncert over four interpolation support cells, valid rendered samples only; not project RMSE, not local measurement accuracy guarantee. See source BAG uncertainty band for per-cell data.',
        'accuracy_note':'Grid spacing is not survey accuracy. Historical MBES data; local uncertainty, dated coverage, vertical datum/epoch and field acceptance remain to be checked.',
        'intended_use':'Visualization only; NOAA explicitly excludes navigation. No artificial procedural seafloor detail. Unknown/land/outside-survey cells remain holes.',
        'license':'NOAA CC0-1.0','values_sha256':hashlib.sha256(json.dumps(values,separators=(',',':')).encode()).hexdigest(),
    },'values':values}
    output = ROOT/'public/data'/name
    temporary = CACHE/(name+'.partial')
    temporary.write_text(json.dumps(document,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
    output.write_bytes(temporary.read_bytes())
    print(f'{name}: {width}x{height}, {int(valid.sum())} measured-grid samples, {spacing}, depth {supported.min()}..{supported.max()} m MLLW; coverage {valid.mean()*100:.2f}%',flush=True)

if __name__ == '__main__':
    for name in FILES:
        target = CACHE / name
        download(BASE+'BAG/'+name, target)
    export({'west':-118.31,'south':33.70,'east':-118.19,'north':33.765},1401,911,'seabed-dem.json')
    # Align the patch perimeter with coarse source vertices to prevent LOD cracks.
    export({'west':-118.31+600*.12/1400,'south':33.765-544*.065/910,'east':-118.31+800*.12/1400,'north':33.765-368*.065/910},801,705,'seabed-detail-mb.json')
