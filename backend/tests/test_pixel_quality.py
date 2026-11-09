"""Fixed tiny GeoTIFF fixtures, never available to the service as fake results."""
import copy
import asyncio
import json
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_origin
from fastapi.testclient import TestClient
from app.main import app
from app.pixel_raster import diagnose_scene,make_grid,area_weights,radiometry,process_pixels
from app.pixel_policy import QualityError
from app import pixel_quality as qa
from app import pixel_raster as raster
from shapely.geometry import box,mapping
from test_analysis_conditions import QUERY,raw


@pytest.fixture
def rasters(tmp_path):
    grid={'crs':'EPSG:6933','transform':from_origin(0,80,20,20),'width':4,'height':4}
    scene={'id':'TEST_ONLY','datetime':'2025-07-01T00:00:00Z','boa_offset_applied':False,'required_keys':['red','nir'],'assets':{}}
    def write(key,data,res=20):
        path=tmp_path/(key+'.tif')
        with rasterio.open(path,'w',driver='GTiff',width=data.shape[1],height=data.shape[0],count=1,dtype=data.dtype,
                           crs=grid['crs'],transform=from_origin(0,80,res,res),nodata=0,tiled=True,blockxsize=16,blockysize=16) as dst:
            dst.write(data,1)
        scene['assets'][key]={'path':str(path),'nodata':0,'scale':.0001,'offset':0}
    write('scl',np.full((4,4),4,dtype='uint8'))
    for k in ('red','nir'):write(k,np.full((4,4),1000,dtype='uint16'))
    return grid,scene,write


def diagnose(rasters,weights=None,common=None):
    g,s,_=rasters;weights=np.full((4,4),400.) if weights is None else weights
    return diagnose_scene(s,g,weights,weights if common is None else common)


def test_known_scl_exclusions_and_valid_areas(rasters):
    g,s,write=rasters
    write('scl',np.array([[4,5,6,0],[8,9,10,3],[1,2,7,11],[4,5,6,4]],dtype='uint8'))
    data=np.full((4,4),1000,dtype='uint16');data[3,3]=0;write('red',data)
    r,mask=diagnose(rasters)
    assert r['status']=='checked' and r['valid_area_m2']==2400
    assert mask.sum()==6 and r['exclusions_m2']['band_nodata_or_mixed_invalid']==400
    assert r['exclusions_m2']['cloud_cirrus']==1200
    assert sum(r['exclusions_m2'].values())+r['valid_area_m2']==6400
    assert all(h['file_header_read'] for h in r['headers'])


def test_categorical_scl_and_conservative_10m_average(rasters):
    _,_,write=rasters
    data=np.full((8,8),1000,dtype='uint16');data[0,0]=0;write('red',data,10)
    r,mask=diagnose(rasters)
    assert r['valid_area_m2']==6000 and not mask[0,0]
    assert r['exclusions_m2']['band_nodata_or_mixed_invalid']==400


def test_all_cloud_is_real_zero_not_failure(rasters):
    rasters[2]('scl',np.full((4,4),9,dtype='uint8'))
    r,mask=diagnose(rasters)
    assert r['status']=='checked' and r['valid_area_m2']==0 and not mask.any()


@pytest.mark.parametrize('missing',['scl','red'])
def test_no_pixels_is_null_not_zero(rasters,missing):
    rasters[2](missing,np.zeros((4,4),dtype='uint8' if missing=='scl' else 'uint16'))
    r,mask=diagnose(rasters)
    assert r['status']=='no_pixels' and r['valid_area_m2'] is None and mask is None


def test_missing_quality_file_preserves_unknown(rasters):
    rasters[1]['assets']['scl']['path']='TEST_ONLY_MISSING.tif'
    r,mask=diagnose(rasters)
    assert r['status']=='failed' and r['valid_area_m2'] is None and mask is None


def test_individual_and_common_denominators_differ(rasters):
    common=np.zeros((4,4));common[:,:2]=400
    r,_=diagnose(rasters,common=common)
    assert r['valid_area_m2']==6400 and r['valid_in_common_area_m2']==3200


def test_fractional_area_weights_and_limits():
    g=make_grid([126.7,36.4,126.701,36.401])
    w=area_weights(g['aoi'],g)
    assert w.sum()==pytest.approx(g['aoi'].area,abs=.001)
    assert np.any((w>0)&(w<400))
    with pytest.raises(QualityError):make_grid([126.5,36.3,127,36.8])


@pytest.mark.parametrize('scale,offset,applied,status',[(.0001,0,True,'confirmed_metadata'),(.0001,-.1,False,'confirmed_metadata'),
    (.0001,-.1,True,'unknown'),(None,0,False,'unknown'),(0,0,False,'unknown'),(float('nan'),0,False,'unknown')])
def test_scale_offset_not_guessed(scale,offset,applied,status):
    assert radiometry({'scale':scale,'offset':offset},{'boa_offset_applied':applied})['status']==status


def test_inconsistent_nodata_fails_not_zero(rasters):
    rasters[1]['assets']['scl']['nodata']=None
    r,mask=diagnose(rasters)
    assert r['status']=='failed' and r['valid_area_m2'] is None


def test_api_aoi_limit_rejects_before_network(monkeypatch):
    async def never(*args):raise AssertionError('network not allowed')
    monkeypatch.setattr(qa.a2,'request_metadata',never)
    r=TestClient(app).post('/pixel-quality',json=QUERY)
    assert r.status_code==200 and r.json()['common_valid_area_m2'] is None
    assert '25 km' in r.json()['error']


def test_api_limits_and_single_job():
    client=TestClient(app)
    assert client.post('/pixel-quality',json=QUERY|{'scene_b':QUERY['scene_a']}).status_code==422
    assert client.post('/pixel-quality',json=QUERY|{'purpose_type':'thermal'}).status_code==422
    assert client.post('/pixel-quality',json=QUERY|{'minimum_valid_percent':101}).status_code==422
    qa.JOB_LOCK.acquire()
    try:
        d=client.post('/pixel-quality',json=QUERY).json()
        assert d['status']=='busy' and d['common_valid_area_m2'] is None
    finally:qa.JOB_LOCK.release()


@pytest.mark.parametrize('fault',['missing_scl','missing_band','reverse','same_day','wrong_product','restricted'])
def test_api_preflight_reuses_existing_rules(monkeypatch,fault):
    rows=[raw('TEST_A','2025-07-05'),raw('TEST_B','2025-07-20')]
    for r in rows:
        for k,a in r['assets'].items():
            a['href']=f'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/TEST_ONLY/{k}.tif'
            a['raster:bands']=[{'nodata':0,'scale':.0001,'offset':0}]
    if fault=='missing_scl':rows[0]['assets'].pop('scl')
    if fault=='missing_band':rows[0]['assets'].pop('nir')
    if fault=='reverse':rows[0]['properties']['datetime']='2025-07-25T00:00:00Z'
    if fault=='same_day':rows[1]['properties']['datetime']='2025-07-05T06:00:00Z'
    if fault=='wrong_product':rows[0]['properties']['processing:level']='L1C'
    if fault=='restricted':rows[0]['assets']['red']['storage:requester_pays']=True
    async def fake(c,m,url,b):return 200,{},rows[0 if url.endswith('TEST_A') else 1]
    async def never(*args):raise AssertionError('worker must not start')
    monkeypatch.setattr(qa.a2,'request_metadata',fake);monkeypatch.setattr(qa,'run_worker',never)
    d=TestClient(app).post('/pixel-quality',json=QUERY|{'bbox':[126.7,36.4,126.71,36.41]}).json()
    assert d['status']=='failed' and d['common_valid_area_m2'] is None


def test_two_date_common_mask_exact_areas_and_partial_failure(rasters,monkeypatch,tmp_path):
    # Actual tiny TIFFs; fixed equal-area grid with analytically known 400 m² cells.
    g,a,write=rasters;g.update(aoi=box(0,0,80,80),bbox=[0,0,80,80])
    monkeypatch.setattr(raster,'make_grid',lambda _:g)
    monkeypatch.setattr(raster,'project_footprint',lambda geom,g:raster.shape(geom))
    a.update(geometry=mapping(box(0,0,80,80)))
    b=copy.deepcopy(a);b.update(id='TEST_ONLY_B',datetime='2025-07-02T00:00:00Z',geometry=mapping(box(0,0,40,80)))
    # B covers only the left half. Its top-left cell is cloud.
    data=np.full((4,4),4,dtype='uint8');data[0,0]=9
    write('b_scl',data);b['assets']['scl']=a['assets'].pop('b_scl')
    # A has a cloud in a DIFFERENT cell of the common half.
    data=np.full((4,4),4,dtype='uint8');data[1,0]=9;write('scl',data)
    payload={'bbox':g['bbox'],'scenes':[a,b],'minimum_valid_percent':70}
    d=process_pixels(payload)
    assert d['status']=='checked' and d['aoi_area_m2']==6400
    assert d['common_observed_area_m2']==3200 and d['common_valid_area_m2']==2400
    assert d['common_valid_percent_aoi']==37.5 and d['common_valid_percent_observed']==75
    assert d['common_excluded_area_m2']==800 and d['operational_threshold']['met'] is True
    assert [s['valid_area_m2'] for s in d['scenes']]==[6000,2800]
    assert [s['valid_in_common_area_m2'] for s in d['scenes']]==[2800,2800]
    payload['minimum_valid_percent']=80
    assert process_pixels(payload)['operational_threshold']['met'] is False
    b['assets']['scl']['path']=str(tmp_path/'MISSING_TEST_ONLY.tif')
    d=process_pixels(payload)
    assert d['status']=='partial' and d['scenes'][0]['valid_area_m2']==6000
    assert d['common_valid_area_m2'] is None and d['operational_threshold']['met'] is None


def test_worker_deadline_kills_and_reaps_process(monkeypatch):
    class Process:
        killed=False;returncode=None
        def communicate(self,*args,**kw):
            if not self.killed:raise qa.subprocess.TimeoutExpired('TEST_ONLY',.01)
            self.returncode=-1;return b'',b''
        def kill(self):self.killed=True
        def poll(self):return self.returncode
        def wait(self):self.returncode=-1
    p=Process();monkeypatch.setattr(qa.subprocess,'Popen',lambda *a,**kw:p)
    d=asyncio.run(qa.run_worker({}))
    assert p.killed and p.returncode==-1
    assert d['status']=='limited' and d['common_valid_area_m2'] is None


def test_calibration_nan_is_json_safe():
    r=radiometry({'scale':float('nan'),'offset':float('inf')},{})
    assert r['status']=='unknown' and r['scale'] is None and r['offset'] is None
    json.dumps(r,allow_nan=False)
