"""A4 fixed GeoTIFF expected values and failure boundaries; never service fixtures."""
import base64
import copy
import io
import json
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from rasterio.io import MemoryFile
from shapely.geometry import box,mapping
from fastapi.testclient import TestClient

from app import pixel_raster as raster
from app.change_analysis import process_change,ndvi,NODATA,calibration_for_change
from app.main import app
from app import pixel_quality as qa
from test_analysis_conditions import QUERY,raw


@pytest.fixture
def pair(tmp_path,monkeypatch):
    grid={'crs':'EPSG:6933','transform':from_origin(0,80,20,20),'width':4,'height':4,
          'aoi':box(0,0,80,80),'bbox':[0,0,80,80]}
    monkeypatch.setattr(raster,'make_grid',lambda _:grid)
    monkeypatch.setattr(raster,'project_footprint',lambda geom,g:raster.shape(geom))
    scenes=[]
    for i,(date,nir) in enumerate([('2021-07-16',3000),('2021-07-26',5000)]):
        s={'id':f'TEST_ONLY_{i}','collection':'sentinel-2-l2a','datetime':date+'T02:00:00Z',
           'geometry':mapping(box(0,0,80,80)),'processing_baseline':'03.01',
           'boa_offset_applied':False,'required_keys':['red','nir'],'assets':{},
           'source_url':f'https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/TEST_ONLY_{i}'}
        for key,value,dtype in [('scl',4,'uint8'),('red',1000,'uint16'),('nir',nir,'uint16')]:
            path=tmp_path/f'{i}-{key}.tif'
            with rasterio.open(path,'w',driver='GTiff',width=4,height=4,count=1,dtype=dtype,
                               crs='EPSG:6933',transform=from_origin(0,80,20,20),nodata=0,
                               tiled=True,blockxsize=16,blockysize=16) as dst:
                dst.write(np.full((4,4),value,dtype=dtype),1)
            s['assets'][key]={'path':str(path),'url':f'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/TEST_ONLY/{i}-{key}.tif',
                              'nodata':0,'scale':.0001,'offset':0}
        scenes.append(s)
    return {'bbox':grid['bbox'],'scenes':scenes,'purpose':'vegetation','minimum_valid_percent':70},grid


def unpack(report):
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(report['artifact_base64']))) as archive:
        names=archive.namelist()
        manifest=json.loads(archive.read('processing.json'))
        with MemoryFile(archive.read('ndvi_change.tif')) as mem:
            with mem.open() as src:
                raster_data=src.read();ndvi_header={'crs':src.crs.to_string(),'nodata':src.nodata,'descriptions':src.descriptions,'transform':src.transform}
        with MemoryFile(archive.read('valid_mask.tif')) as mem:
            with mem.open() as src:mask=src.read(1);mask_nodata=src.nodata
    return names,manifest,raster_data,ndvi_header,mask,mask_nodata


def test_expected_ndvi_difference_geotiffs_and_processing_record(pair):
    payload,grid=pair
    report=process_change(payload)
    assert report['status']=='computed' and report['analysis_completed']
    assert report['analysis_area_m2']==6400 and report['excluded_common_area_m2']==0
    assert report['ndvi_before_mean']==pytest.approx(.5)
    assert report['ndvi_after_mean']==pytest.approx(2/3)
    assert report['ndvi_difference_mean']==pytest.approx(1/6)
    names,manifest,data,header,mask,mask_nodata=unpack(report)
    assert names==['ndvi_change.tif','valid_mask.tif','processing.json']
    assert header['crs']=='EPSG:6933' and header['nodata']==NODATA and header['transform']==grid['transform']
    assert header['descriptions']==('NDVI_before','NDVI_after','NDVI_difference_after_minus_before')
    assert np.allclose(data[0],.5,atol=1e-6) and np.allclose(data[1],2/3,atol=1e-6)
    assert np.allclose(data[2],1/6,atol=1e-6) and np.all(mask==1) and mask_nodata==0
    assert manifest['formula']=='NDVI=(NIR-RED)/(NIR+RED); difference=after-before'
    assert manifest['files']['ndvi_change.tif']['nodata']==NODATA
    assert manifest['sources'][0]['assets']['red']['scale']==.0001
    assert manifest['input']['bbox']==[0,0,80,80]


def test_cloud_and_nodata_excluded_only_on_common_pixels(pair):
    payload,_=pair
    second=payload['scenes'][1]
    with rasterio.open(second['assets']['scl']['path'],'r+') as dst:
        a=dst.read(1);a[0,0]=9;dst.write(a,1)
    with rasterio.open(second['assets']['red']['path'],'r+') as dst:
        a=dst.read(1);a[0,1]=0;dst.write(a,1)
    r=process_change(payload)
    assert r['status']=='computed' and r['analysis_area_m2']==5600
    assert r['excluded_common_area_m2']==800 and r['qa_excluded_area_m2']==800
    _,_,data,_,mask,_=unpack(r)
    assert np.all(mask[0,:2]==0) and np.all(data[:,0,:2]==NODATA)


@pytest.mark.parametrize('fault',['all_cloud','missing_file','calibration_conflict','wrong_scale','no_overlap','reverse','duplicate','wrong_purpose'])
def test_unusable_pairs_never_export(pair,fault):
    payload,_=pair
    if fault=='all_cloud':
        for s in payload['scenes']:
            with rasterio.open(s['assets']['scl']['path'],'r+') as dst:dst.write(np.full((4,4),9,dtype='uint8'),1)
    if fault=='missing_file':payload['scenes'][1]['assets']['scl']['path']='TEST_ONLY_MISSING.tif'
    if fault=='calibration_conflict':
        payload['scenes'][0]['boa_offset_applied']=True;payload['scenes'][0]['assets']['red']['offset']=-.1
    if fault=='wrong_scale':payload['scenes'][0]['assets']['red']['scale']=0
    if fault=='no_overlap':payload['scenes'][1]['geometry']=mapping(box(100,100,180,180))
    if fault=='reverse':payload['scenes'].reverse()
    if fault=='duplicate':payload['scenes'][1]['id']=payload['scenes'][0]['id']
    if fault=='wrong_purpose':payload['purpose']='flood'
    r=process_change(payload)
    assert r['status']=='blocked' and r['artifact_base64'] is None
    assert r['analysis_area_m2'] is None


def test_numeric_guard_zero_denominator_nan_inf_and_negative_reflectance():
    red=np.array([[0.,np.nan,np.inf,-.1,.2]])
    nir=np.array([[0.,.3,.3,.3,.4]])
    values,valid=ndvi(red,nir,np.ones(red.shape,dtype=bool))
    assert valid.tolist()==[[False,False,False,False,True]]
    assert np.isnan(values[0,:4]).all() and values[0,4]==pytest.approx(1/3)


@pytest.mark.parametrize('baseline,applied,scale,offset,expected',[
    ('03.01',False,.0001,0,True),('05.11',True,.0001,0,True),('05.11',False,.0001,-.1,True),
    ('05.11',True,.0001,-.1,False),('03.01',False,.0001,-.1,False),
    ('05.11',None,.0001,0,False),('03.01',False,.001,0,False),
    ('03.01',False,float('nan'),0,False),('03.01',False,.0001,float('inf'),False)])
def test_baseline_calibration_consistency(baseline,applied,scale,offset,expected):
    assert calibration_for_change({'scale':scale,'offset':offset},
                                  {'processing_baseline':baseline,'boa_offset_applied':applied}) is expected


def test_different_source_grid_reprojects_to_one_output_grid(pair,tmp_path):
    payload,grid=pair
    scene=payload['scenes'][1]
    for key in ('scl','red','nir'):
        path=scene['assets'][key]['path']
        with rasterio.open(path) as src:data=src.read(1)
        with rasterio.open(path,'w',driver='GTiff',width=4,height=4,count=1,dtype=data.dtype,
                           crs='EPSG:6933',transform=from_origin(10,90,20,20),nodata=0,
                           tiled=True,blockxsize=16,blockysize=16) as dst:dst.write(data,1)
    r=process_change(payload)
    assert r['status']=='computed' and 0<r['analysis_area_m2']<6400
    _,_,data,header,mask,_=unpack(r)
    assert header['transform']==grid['transform'] and np.any(mask==0) and np.any(mask==1)
    assert np.all(data[:,mask==0]==NODATA)


def test_export_never_records_signed_urls(pair):
    payload,_=pair
    payload['scenes'][0]['source_url']+='?token=TEST_SECRET'
    payload['scenes'][0]['assets']['red']['url']+='?X-Amz-Signature=TEST_SECRET'
    r=process_change(payload)
    assert r['status']=='computed'
    _,manifest,*_=unpack(r)
    assert manifest['sources'][0]['item_url'] is None
    assert manifest['sources'][0]['assets']['red']['href'] is None
    assert 'TEST_SECRET' not in json.dumps(manifest)


def test_a4_request_requires_vegetation_s2_and_distinct_items():
    client=TestClient(app)
    assert client.post('/change-analysis',json=QUERY|{'purpose_type':'thermal'}).status_code==422
    assert client.post('/change-analysis',json=QUERY|{'scene_b':QUERY['scene_a']}).status_code==422
    assert client.post('/change-analysis',json=QUERY|{'scene_b':{'collection':'landsat-c2-l2','id':'TEST_B'}}).status_code==422


@pytest.mark.parametrize('fault',['baseline','platform','offset_conflict','missing_band','wrong_product'])
def test_a4_metadata_preflight_blocks_before_raster_worker(monkeypatch,fault):
    rows=[raw('TEST_A','2025-07-05'),raw('TEST_B','2025-07-20')]
    for row in rows:
        row['properties']['s2:processing_baseline']='03.01'
        row['properties']['earthsearch:boa_offset_applied']=False
        for key,asset in row['assets'].items():
            asset['href']=f'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/TEST_ONLY/{key}.tif'
            asset['raster:bands']=[{'nodata':0,'scale':.0001,'offset':0}]
    if fault=='baseline':rows[1]['properties']['s2:processing_baseline']='05.11'
    if fault=='platform':rows[1]['properties']['platform']='sentinel-2a'
    if fault=='offset_conflict':
        rows[0]['properties']['earthsearch:boa_offset_applied']=True
        rows[0]['assets']['red']['raster:bands'][0]['offset']=-.1
    if fault=='missing_band':rows[1]['assets'].pop('nir')
    if fault=='wrong_product':rows[1]['properties']['processing:level']='L1C'
    async def fake(c,m,url,b):return 200,{},rows[0 if url.endswith('TEST_A') else 1]
    async def never(*args):raise AssertionError('raster worker must not run')
    monkeypatch.setattr(qa.a2,'request_metadata',fake)
    monkeypatch.setattr(qa,'run_worker',never)
    d=TestClient(app).post('/change-analysis',json=QUERY|{'bbox':[126.7,36.4,126.71,36.41]}).json()
    assert d['status']=='failed' and d['common_valid_area_m2'] is None
    assert not d.get('artifact_base64')
