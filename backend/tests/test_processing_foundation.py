"""TEST ONLY real local TIFF pixels; never a production provider fallback."""
import asyncio
import copy
import hashlib
import io
import json
import time
import zipfile
from uuid import uuid4
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from app.main import app
from app import processing,artifact_store as artifacts
from app.processing_models import ProcessingRequest
from app.analysis_catalog import QA_VERSION,catalog
from app.pixel_policy import QualityError
from app.pixel_raster import make_grid,process_pixels
from app.processing_raster import GRID_LIMITS,tiled_pixels
from app.processing_worker import execute
from app import media_access

def request_data(method='s2_quality',bbox=(126.7,36.4,126.71,36.41)):
    return dict(purpose_type='vegetation',analysis_id='vegetation_change' if method=='ndvi_change' else 'vegetation_index',
        method_id=method,roi={'confirmed':True,'mode':'bbox','bbox':bbox,'source':'manual_bbox'},
        start_date='2025-07-01',end_date='2025-07-31',reference_date=None,comparison_regions=[],threshold=None,
        qa_policy_version=QA_VERSION,scenes=[{'provider_id':'earth-search','collection':'sentinel-2-l2a','id':'TEST_ONLY_'+str(i),
            'asset_keys':['red','nir','green','scl']} for i in range(2)])

def raster_payload(tmp_path,bbox=(126.7,36.4,126.71,36.41),method='s2_quality'):
    query=request_data(method,bbox);g=make_grid(bbox,limits=GRID_LIMITS);scenes=[]
    for i in range(2):
        assets={}
        for key,value in [('red',1000),('nir',3000 if i else 2000),('green',1200),('scl',4)]:
            path=tmp_path/(f'TEST_ONLY_{i}_{key}.tif');dtype='uint8' if key=='scl' else 'uint16'
            with rasterio.open(path,'w',driver='GTiff',width=g['width'],height=g['height'],count=1,dtype=dtype,
                crs=g['crs'],transform=g['transform'],nodata=0,tiled=True,blockxsize=32,blockysize=32) as dst:
                a=np.full((g['height'],g['width']),value,dtype=dtype)
                if key=='scl':a[:2,:]=9
                dst.write(a,1)
            assets[key]={'path':str(path),'url':f'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/TEST_ONLY_{i}_{key}.tif',
                'nodata':0,'scale':.0001,'offset':0}
        scenes.append({'id':'TEST_ONLY_'+str(i),'collection':'sentinel-2-l2a','datetime':f'2025-07-{10+i*10}T00:00:00Z',
            'geometry':{'type':'Polygon','coordinates':[[[bbox[0],bbox[1]],[bbox[2],bbox[1]],[bbox[2],bbox[3]],[bbox[0],bbox[3]],[bbox[0],bbox[1]]]]},
            'platform':'sentinel-2b','processing_baseline':'03.00','boa_offset_applied':False,
            'required_keys':['red','nir'],'assets':{k:v for k,v in assets.items() if k!='green'},
            'source_url':'https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/TEST_ONLY_'+str(i)})
    return {'bbox':list(bbox),'scenes':scenes,'purpose':'vegetation','reference_date':None,'minimum_valid_percent':70,
        'method_id':method,'roi':query['roi'],'roi_fingerprint':ProcessingRequest.model_validate(query).roi.fingerprint(),
        'processing_input':query,'analysis_mode':'ndvi_change' if method=='ndvi_change' else 'quality'}

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    monkeypatch.setattr(artifacts,'ROOT',tmp_path/'artifacts')
    processing.PLANS.clear();processing.JOBS.clear()
    media_access._usage.clear()
    yield
    processing.PLANS.clear();processing.JOBS.clear()

def test_catalog_execution_contract_is_server_owned():
    c=catalog();assert len(c['analyses'])==10
    assert [t['id'] for t in c['analyses'] if not t['execution']['analysis_supported']]==['flood_extent','landcover_change']
    for method in c['processing_methods']:
        assert method['browser_download_required'] is False
        assert method['source_mode']=='canonical_server_range'
        assert {'valid_mask.tif','exclusion_mask.tif','manifest.json'}<=set(method['artifacts'])

@pytest.mark.parametrize('fault',['unconfirmed','provider','product','qa','duplicate','purpose','unknown_engine','url','threshold','regions'])
def test_bad_inputs_rejected_before_any_provider_call(monkeypatch,fault):
    q=request_data()
    if fault=='unconfirmed':q['roi']['confirmed']=False
    if fault=='provider':q['scenes'][0]['provider_id']='nasa-cmr'
    if fault=='product':q['scenes'][0].update(provider_id='planetary-computer',collection='pc-sentinel-2-l2a')
    if fault=='qa':q['qa_policy_version']='TEST_ONLY_WRONG'
    if fault=='duplicate':q['scenes'][1]=q['scenes'][0]
    if fault=='purpose':q['purpose_type']='thermal'
    if fault=='unknown_engine':q['method_id']='invented'
    if fault=='url':q['scenes'][0]['url']='https://example.test/TEST_ONLY'
    if fault=='threshold':q['threshold']=.5
    if fault=='regions':q['comparison_regions']=[q['roi']]
    async def forbidden(*a,**kw):raise AssertionError('provider must not run')
    monkeypatch.setattr(processing,'prepare',forbidden)
    assert TestClient(app).post('/processing/plans',json=q).status_code==422

@pytest.mark.parametrize('method',['s2_quality','ndvi_change'])
def test_actual_pixels_disk_manifest_download_reopen(tmp_path,method):
    payload=raster_payload(tmp_path,method=method);identifier=uuid4().hex
    result=execute(payload,identifier)
    assert result['status']=='succeeded' and 'artifact_base64' not in json.dumps(result)
    assert result['result']['map_layers']['quality'][0]['png_base64']
    path=artifacts.verified_download(identifier,result['artifact']);body=path.read_bytes()
    assert hashlib.sha256(body).hexdigest()==result['artifact']['sha256']
    with zipfile.ZipFile(io.BytesIO(body)) as z:
        manifest=json.loads(z.read('manifest.json'));assert manifest['verified_after_disk_write']
        assert manifest['input']['start_date']=='2025-07-01'
        for name,evidence in manifest['files'].items():
            assert hashlib.sha256(z.read(name)).hexdigest()==evidence['sha256']
            if name.endswith('.tif'):
                stored=tmp_path/name;stored.write_bytes(z.read(name))
                with rasterio.open(stored) as ds:
                    assert ds.crs and ds.nodata is not None and ds.width>0 and np.isfinite(ds.read()).all()
        if method=='ndvi_change':assert result['result']['ndvi_difference_mean']==pytest.approx(.5-1/3,abs=1e-6)
    path.write_bytes(body+b'TEST_ONLY_CORRUPTION')
    with pytest.raises(QualityError):artifacts.verified_download(identifier,result['artifact'])

def test_fixed_grid_tiles_equal_legacy_pixels_and_polygon(tmp_path):
    payload=raster_payload(tmp_path,bbox=(126.7,36.4,126.77,36.47))
    direct=process_pixels(payload,capture=True,grid=make_grid(payload['bbox'],limits=GRID_LIMITS))
    tiled=tiled_pixels(payload,None)
    assert tiled['tiling']['tile_count']>1
    assert tiled['common_valid_area_m2']==pytest.approx(direct['common_valid_area_m2'])
    assert np.array_equal(tiled['_analysis_arrays']['masks'][0],direct['_analysis_arrays']['masks'][0])
    a=tiled['_analysis_arrays']['bands'][0]['nir'];b=direct['_analysis_arrays']['bands'][0]['nir']
    assert np.allclose(a,b,equal_nan=True)
    w,s,e,n=payload['bbox'];payload['roi']={'mode':'polygon','geometry':{'type':'Polygon','coordinates':[[[w,s],[e,s],[w,n],[w,s]]]}}
    clipped=tiled_pixels(payload,None)
    assert clipped['aoi_area_m2']<tiled['aoi_area_m2']*.51
    assert clipped['common_valid_area_m2']<tiled['common_valid_area_m2']

def test_limit_and_failed_real_read_never_become_zero(tmp_path):
    payload=raster_payload(tmp_path)
    payload['scenes'][0]['assets']['scl']['path']=str(tmp_path/'TEST_ONLY_MISSING.tif')
    with pytest.raises(QualityError):execute(payload,uuid4().hex)
    payload['bbox']=[126,36,127,37]
    with pytest.raises(QualityError):tiled_pixels(payload,None)

def test_owned_plan_job_and_full_zip_response(tmp_path,monkeypatch):
    payload=raster_payload(tmp_path,method='ndvi_change')
    async def prepare(query):return payload,{'width':50,'height':50,'tile_count':1,'resolution_m':20,'aoi_area_m2':100,'maximum_aoi_km2':100}
    async def worker(p,identifier):return execute(p,identifier)
    monkeypatch.setattr(processing,'prepare',prepare);monkeypatch.setattr(processing,'run_file_worker',worker)
    with TestClient(app) as owner,TestClient(app) as other:
        p=owner.post('/processing/plans',json=request_data('ndvi_change'));assert p.status_code==200
        start={k:p.json()[k] for k in ('plan_id','confirmation_digest')};start['idempotency_key']='TEST_ONLY_ONCE'
        assert other.post('/processing/jobs',json=start).status_code==404
        r=owner.post('/processing/jobs',json=start);assert r.status_code==202
        identifier=r.json()['job_id']
        for _ in range(100):
            job=owner.get('/processing/jobs/'+identifier).json()
            if job['status'] not in ('queued','running'):break
            time.sleep(.01)
        assert job['status']=='succeeded',job
        assert owner.post('/processing/jobs',json=start).json()['job_id']==identifier
        assert other.get('/processing/jobs/'+identifier+'/download').status_code==404
        r=owner.get('/processing/jobs/'+identifier+'/download');assert r.status_code==200
        assert r.headers['content-type']=='application/zip' and len(r.content)==job['artifact']['bytes']
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:assert 'manifest.json' in z.namelist()
        processing.JOBS.clear()
        assert owner.get('/processing/jobs/'+identifier).status_code==200 # restored signed disk journal

def test_cancel_and_timeout_cleanup(tmp_path,monkeypatch):
    async def run():
        class Process:
            returncode=None;killed=False
            async def communicate(self,raw):await asyncio.sleep(10)
            def kill(self):self.killed=True;self.returncode=-1
            async def wait(self):return self.returncode
        p=Process()
        async def spawn(*a,**kw):
            assert not any('TOKEN' in k or 'API_KEY' in k for k in kw['env'])
            return p
        monkeypatch.setattr(asyncio,'create_subprocess_exec',spawn);monkeypatch.setattr(processing,'WORKER_SECONDS',.01)
        with pytest.raises(QualityError):await processing.run_file_worker({},uuid4().hex)
        assert p.killed
    asyncio.run(run())

def test_artifact_unsafe_zip_and_signed_manifest_blocked(tmp_path):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w') as z:z.writestr('../TEST_ONLY.tif',b'bad')
    with pytest.raises(QualityError):artifacts.unpack_artifact(out.getvalue())
    with pytest.raises(QualityError):artifacts.safe_value({'href':'https://example.test/TEST_ONLY?sig=TEST_ONLY'})

@pytest.mark.parametrize('fault',[None,'wrong_item','out_of_period','wrong_product','missing_qa','missing_selected_band','oversize'])
def test_real_canonical_preflight_and_no_browser_receipt(monkeypatch,fault):
    from app import analysis_conditions as a2
    q=request_data('ndvi_change');calls=[]
    if fault=='oversize':q['roi']['bbox']=[126,36,127,37]
    if fault=='missing_selected_band':q['scenes'][0]['asset_keys'].remove('scl')
    async def metadata(client,method,url,budget):
        identifier=url.rsplit('/',1)[-1];i=int(identifier[-1]);calls.append(identifier)
        raw={'id':identifier,'collection':'sentinel-2-l2a','geometry':{'type':'Polygon','coordinates':[[[126,36],[128,36],[128,38],[126,38],[126,36]]]},
            'properties':{'datetime':f'2025-07-{10+i*10}T00:00:00Z','platform':'sentinel-2b','instruments':['msi'],'s2:product_type':'S2MSI2A','s2:processing_baseline':'03.00','earthsearch:boa_offset_applied':False},
            'assets':{k:{'href':f'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/TEST_ONLY_{i}_{k}.tif','type':'image/tiff','roles':['data'],
                'eo:bands':[{'common_name':k}] if k!='scl' else [],'raster:bands':[{'nodata':0,'scale':.0001,'offset':0}]} for k in ('red','nir','green','scl')}}
        if fault=='wrong_item':raw['id']='TEST_ONLY_OTHER'
        if fault=='out_of_period':raw['properties']['datetime']='2025-08-01T00:00:00Z'
        if fault=='wrong_product':raw['properties']['s2:product_type']='L1C'
        if fault=='missing_qa':raw['assets'].pop('scl')
        return 200,{},raw
    monkeypatch.setattr(a2,'request_metadata',metadata)
    with TestClient(app) as c:
        r=c.post('/processing/plans',json=q)
        assert r.status_code==(200 if fault is None else 422),r.text
        if fault is None:
            assert r.json()['source_access']=='canonical_metadata_checked_pixels_pending'
            assert r.json()['pixel_quality'] is None
            processing.PLANS[r.json()['plan_id']]['expires']=0
            body={k:r.json()[k] for k in ('plan_id','confirmation_digest')};body['idempotency_key']='TEST_ONLY_EXPIRED'
            assert c.post('/processing/jobs',json=body).status_code==404
    if fault=='oversize':assert calls==[]

@pytest.mark.parametrize('method',['observed_composite','local_ridge'])
def test_existing_composite_ml_outputs_use_common_disk_contract(tmp_path,method):
    p=raster_payload(tmp_path)
    p.update(method_id=method,analysis_mode='estimate_execute' if method=='local_ridge' else 'composite_execute',
        target_id=p['scenes'][0]['id'],start_date='2025-07-01',end_date='2025-07-31',temporal_mode='single',allow_date_change=False)
    p['processing_input'].update(method_id=method)
    for i,scene in enumerate(p['scenes']):
        scene['required_keys']=['red','nir','green']
        scene['assets']['green']={**scene['assets']['red'],'path':str(tmp_path/f'TEST_ONLY_{i}_green.tif'),
            'url':scene['assets']['red']['url'].replace('red','green')}
    with rasterio.open(p['scenes'][1]['assets']['scl']['path'],'r+') as ds:
        a=ds.read(1);a[:2,:]=4;ds.write(a,1)
    result=execute(p,uuid4().hex)
    assert result['status']=='succeeded'
    assert result['result']['map_layers']['observed']['png_base64']
    assert {'valid_mask.tif','exclusion_mask.tif','manifest.json'}<=set(result['artifact']['files'])

def test_pc_range_uses_anonymous_signer_without_exporting_sas(monkeypatch):
    import httpx
    from app import raster_source as source
    url='https://landsateuwest.blob.core.windows.net/landsat-c2/TEST_ONLY/data.tif'
    requests=[];signed=[]
    async def sign(collection,target,force=False,failed=None):
        signed.append(force);return target+'?sig=TEST_ONLY', 'TEST_ONLY'
    async def validate(target):pass
    real=httpx.Client
    def handle(request):
        requests.append(request.method)
        assert 'Authorization' not in request.headers
        if request.method=='HEAD':return httpx.Response(200,headers={'content-length':'16384','etag':'TEST_ONLY_ETAG'})
        return httpx.Response(206,headers={'content-range':'bytes 0-16383/16384','content-length':'16384'},stream=httpx.ByteStream(b'TEST_ONLY'.ljust(16384,b'0')))
    monkeypatch.setattr(source.planetary,'signed',sign);monkeypatch.setattr(source.provider_transfer,'validate_destination',validate)
    monkeypatch.setattr(source.httpx,'Client',lambda **kw:real(transport=httpx.MockTransport(handle),**kw))
    payload={'scenes':[{'collection':'pc-landsat-c2-l2','assets':{'qa_pixel':{'url':url,'path':'TEST_ONLY.tif'}}}]}
    store=source.open_sources(payload)
    try:
        assert store.block('TEST_ONLY.tif',0,4)==b'TEST'
        assert '?sig=' not in json.dumps(store.info)
        assert requests==['HEAD','GET']
    finally:store.close()
    payload['scenes'][0]['collection']='hls-l30-002'
    with pytest.raises(QualityError):source.open_sources(payload)

def test_all_cloud_is_measured_zero_while_missing_file_is_unknown(tmp_path):
    p=raster_payload(tmp_path)
    for scene in p['scenes']:
        with rasterio.open(scene['assets']['scl']['path'],'r+') as ds:
            ds.write(np.full((ds.height,ds.width),9,dtype='uint8'),1)
    result=execute(p,uuid4().hex)
    assert result['status']=='succeeded'
    assert result['result']['common_valid_area_m2']==0
    assert result['result']['common_valid_percent_aoi']==0

def test_cancel_running_job_does_not_publish_late_artifacts(tmp_path,monkeypatch):
    import threading
    entered=threading.Event()
    p=raster_payload(tmp_path)
    async def prepare(q):return p,{'width':50,'height':50,'tile_count':1,'resolution_m':20,'aoi_area_m2':100,'maximum_aoi_km2':50}
    async def worker(payload,identifier):
        entered.set();await asyncio.sleep(100)
        raise AssertionError('cancelled worker must not publish')
    monkeypatch.setattr(processing,'prepare',prepare);monkeypatch.setattr(processing,'run_file_worker',worker)
    with TestClient(app) as c:
        plan=c.post('/processing/plans',json=request_data()).json()
        body={k:plan[k] for k in ('plan_id','confirmation_digest')};body['idempotency_key']='TEST_ONLY_CANCEL'
        wrong={**body,'confirmation_digest':'0'*64}
        assert c.post('/processing/jobs',json=wrong).status_code==409
        job=c.post('/processing/jobs',json=body).json();assert entered.wait(1)
        r=c.post('/processing/jobs/'+job['job_id']+'/cancel');assert r.json()['status']=='cancelled'
        assert c.get('/processing/jobs/'+job['job_id']+'/download').status_code==409
        assert not artifacts.folder(job['job_id']).exists()

def test_disk_cap_and_band_contract_are_enforced(tmp_path,monkeypatch):
    from app.pixel_raster import grid_info
    from app.analysis_catalog import METHODS
    p=raster_payload(tmp_path);g=make_grid(p['bbox'])
    wrong=artifacts.tiff_bytes(np.ones((g['height'],g['width']),dtype='float32'),g,-9999,['TEST_ONLY_WRONG_COUNT'])
    with pytest.raises(QualityError,match='밴드 수'):
        artifacts.publish(uuid4().hex,{'ndvi_change.tif':wrong},{'grid':grid_info(g)},['ndvi_change.tif'],METHODS['ndvi_change']['artifact_specs'])
    monkeypatch.setattr(artifacts,'DISK_LIMIT',1)
    with pytest.raises(QualityError,match='저장 공간'):
        execute(p,uuid4().hex)

def test_origin_ttl_and_file_expiry(tmp_path,monkeypatch):
    p=raster_payload(tmp_path)
    async def prepare(q):return p,{'width':50,'height':50,'tile_count':1,'resolution_m':20,'aoi_area_m2':100,'maximum_aoi_km2':50}
    monkeypatch.setattr(processing,'prepare',prepare)
    assert TestClient(app).post('/processing/plans',json=request_data(),headers={'Origin':'https://example.test'}).status_code==403
    identifier=uuid4().hex;result=execute(p,identifier);path=artifacts.verified_download(identifier,result['artifact'])
    import os
    os.utime(path,(time.time()-artifacts.TTL-1,time.time()-artifacts.TTL-1))
    with pytest.raises(QualityError,match='만료'):artifacts.verified_download(identifier,result['artifact'])

def test_registered_polygon_uses_server_boundary_provenance_not_browser_claims():
    from app.admin_boundaries import REGISTRY,load_boundary
    from app.processing_models import ROI
    metadata,feature,geometry=load_boundary('서울특별시')
    roi=ROI(confirmed=True,mode='polygon',bbox=geometry.bounds,source='registered_boundary',
        boundary_id=REGISTRY['서울특별시']['stem'],geometry={'type':'Point','coordinates':[0,0]},
        boundary_metadata={'source':'TEST_ONLY_UNTRUSTED'})
    assert roi.geometry==feature['geometry']
    assert roi.boundary_metadata['source']==metadata['source']
    assert roi.boundary_metadata['geojson_sha256']==metadata['geojson_sha256']
    with pytest.raises(ValueError):
        ROI(confirmed=True,mode='polygon',bbox=(126.7,36.4,126.71,36.41),source='registered_boundary',boundary_id=roi.boundary_id)
