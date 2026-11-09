"""TEST ONLY fixed, real TIFF pixels; independent expected equations and file reopen."""
import copy,hashlib,io,json,zipfile
from uuid import uuid4
from datetime import date
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from app import artifact_store,product_processing,processing
from app.main import app
from app.product_policy import products,asset_policy,QA_VERSION
from app.processing_models import ProcessingRequest
from app.processing_raster import processing_grid
from app.processing_worker import execute
from app.pixel_policy import QualityError
from app.band_math import index
from app.landsat_temperature import kelvin_celsius,pixel_quality

@pytest.fixture(autouse=True)
def private_store(tmp_path,monkeypatch):monkeypatch.setattr(artifact_store,'ROOT',tmp_path/'artifacts')

def sample(tmp_path,method='ndvi',profile_id='es_s2',bbox=None):
    p=next(p for p in products(method) if p['profile_id']==profile_id);multi=method in ('mndwi_change','thermal_gapfill','thermal_ml');bbox=bbox or [126.7,36.4,126.71,36.41]
    q={'purpose_type':'thermal' if method in ('surface_temperature','hotspots','temperature_comparison','thermal_gapfill','thermal_ml') else 'urban' if method=='ndbi' else 'flood' if method.startswith('mndwi') else 'vegetation',
       'analysis_id':{'ndvi':'vegetation_index','mndwi':'water_extent','mndwi_change':'water_change','ndbi':'urban_index','thermal_gapfill':'surface_temperature','thermal_ml':'surface_temperature'}.get(method,method),
       'method_id':method,'roi':{'confirmed':True,'mode':'bbox','bbox':bbox,'source':'manual_bbox'},'start_date':'2025-07-01','end_date':'2025-07-31',
       'scenes':[{'provider_id':p['provider_id'],'collection':p['collection'],'id':'TEST_ONLY_'+str(i),'asset_keys':p['required_keys']} for i in range(2 if multi else 1)],'qa_policy_version':QA_VERSION}
    if method in ('mndwi','mndwi_change','hotspots'):q.update(threshold=20 if method=='hotspots' else .1,threshold_basis='TEST ONLY explicit user test criterion')
    if method=='temperature_comparison':q.update(comparison_regions=[{'confirmed':True,'mode':'bbox','source':'manual_bbox','bbox':[126.7,36.4,126.704,36.41]},{'confirmed':True,'mode':'bbox','source':'manual_bbox','bbox':[126.706,36.4,126.71,36.41]}],comparison_labels=['TEST_ONLY_city','TEST_ONLY_surroundings'])
    model=ProcessingRequest.model_validate(q);q=model.model_dump(mode='json');payload={'method_id':method,'bbox':bbox,'roi':q['roi'],'roi_fingerprint':model.roi.fingerprint(),'processing_input':q,'grid_resolution_m':p['resolution_m'],'scenes':[]}
    g,_=processing_grid(payload)
    values={'red':1000,'nir':3000,'green':4000,'swir16':2000,'scl':4} if profile_id=='es_s2' else {'red':10000,'nir08':20000,'green':20000,'swir16':10000,'lwir11':45000,'qa_pixel':64,'qa_radsat':0,'qa':50,'cdist':500}
    raws=[]
    for i,ref in enumerate(q['scenes']):
        props={'platform':'sentinel-2b' if profile_id=='es_s2' else 'landsat-9','datetime':f'2025-07-{10+10*i}T00:00:00Z','s2:product_type':'S2MSI2A','s2:processing_baseline':'03.01','earthsearch:boa_offset_applied':False} if profile_id=='es_s2' else {'platform':'landsat-9','datetime':f'2025-07-{10+10*i}T00:00:00Z','landsat:correction':'L2SP','landsat:collection_number':'02'}
        geometry={'type':'Polygon','coordinates':[[[bbox[0],bbox[1]],[bbox[2],bbox[1]],[bbox[2],bbox[3]],[bbox[0],bbox[3]],[bbox[0],bbox[1]]]]}
        scene={**ref,'datetime':props['datetime'],'platform':props['platform'],'processing_baseline':'03.01' if profile_id=='es_s2' else None,'geometry':geometry,'profile':p,'assets':{}}
        raw={**ref,'properties':props,'geometry':geometry,'assets':{}}
        for key in p['required_keys']:
            qa=key in ('scl','qa_pixel','qa_radsat');nodata=0 if profile_id=='es_s2' else {'qa_pixel':1,'qa_radsat':None,'qa':-9999,'cdist':-9999}.get(key,0)
            dtype='uint8' if key=='scl' else 'int16' if key in ('qa','cdist') else 'uint16'
            scale,offset=(1,0) if qa else (.0001,0) if profile_id=='es_s2' else (.00341802,149) if key=='lwir11' else (.01,0) if key in ('qa','cdist') else (.0000275,-.2)
            meta={'nodata':nodata,'data_type':dtype,**({} if qa else {'scale':scale,'offset':offset})}
            if key=='qa_radsat':meta.pop('nodata')
            url=('https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/' if profile_id=='es_s2' else 'https://landsateuwest.blob.core.windows.net/landsat-c2/')+ref['id']+'/'+key+'.tif'
            asset={'href':url,'raster:bands':[meta],'type':'image/tiff; application=geotiff; profile=cloud-optimized'}
            if key in p['bands'].values():asset['eo:bands']=[{'common_name':key}]
            raw['assets'][key]=asset
            policy=asset_policy(key,p,asset,props)
            path=tmp_path/(ref['id']+'_'+key+'.tif')
            # Local fixture uses the exact planned grid and the documented native
            # pixel size; S2 fixture overrides only this header expectation below.
            with rasterio.open(path,'w',driver='GTiff',width=g['width'],height=g['height'],count=1,dtype=dtype,crs=g['crs'],transform=g['transform'],nodata=nodata,tiled=True,blockxsize=32,blockysize=32) as ds:ds.write(np.full((g['height'],g['width']),values[key]+(1000 if i and key=='green' else 0),dtype=dtype),1)
            scene['assets'][key]={**policy,'path':str(path),'url':url,'resolutions':[p['resolution_m']]}
        payload['scenes'].append(scene);raws.append(raw)
    return q,payload,raws,g

@pytest.mark.parametrize('profile,method',[(p,m) for m in ('ndvi','mndwi','mndwi_change','ndbi') for p in ('es_s2','pc_landsat')]+[('pc_landsat',m) for m in ('surface_temperature','hotspots','temperature_comparison')])
def test_expected_pixels_and_real_output_contract(tmp_path,profile,method):
    q,p,_,g=sample(tmp_path,method,profile);result=execute(p,uuid4().hex);assert result['status']=='succeeded'
    file=artifact_store.verified_download(result['artifact']['filename'][11:-4],result['artifact'])
    with zipfile.ZipFile(file) as z:
        manifest=json.loads(z.read('manifest.json'));assert manifest['input']==q and manifest['verified_after_disk_write']
        for name,record in manifest['files'].items():
            assert hashlib.sha256(z.read(name)).hexdigest()==record['sha256']
            if name.endswith('.tif'):
                path=tmp_path/('received_'+name);path.write_bytes(z.read(name))
                with rasterio.open(path) as ds:assert ds.crs and ds.transform==g['transform'] and ds.read().size and ds.nodata is not None
        name='temperature.tif' if method in ('surface_temperature','hotspots','temperature_comparison') else method+'.tif'
        with rasterio.io.MemoryFile(z.read(name)) as memory:
            with memory.open() as ds:
                a=ds.read(masked=True)
                if name=='temperature.tif':assert float(a[0].mean())==pytest.approx(45000*.00341802+149,abs=1e-4);assert float(a[1].mean())==pytest.approx(45000*.00341802+149-273.15,abs=1e-4);assert ds.tags(1)['unit']=='K' and ds.tags(2)['unit']=='degC'
                elif method!='mndwi_change':
                    x,y=(.1,.3) if profile=='es_s2' else (.075,.35)
                    expected=(y-x)/(y+x) if method in ('ndvi','mndwi') else (x-y)/(x+y)
                    if profile=='es_s2' and method=='mndwi':expected=(.4-.2)/(.4+.2)
                    if profile=='es_s2' and method=='ndbi':expected=(.2-.3)/(.2+.3)
                    assert float(a[0].mean())==pytest.approx(expected,abs=1e-5)
        if method.startswith('mndwi'):assert len(result['result']['threshold_sensitivity'])==3
        if method=='temperature_comparison':assert result['result']['statistics']['mean_difference_celsius_first_minus_second']==pytest.approx(0,abs=1e-7)

@pytest.mark.parametrize('profile',['es_s2','pc_landsat'])
@pytest.mark.parametrize('fault',['cloud','shadow','nodata','zero_denominator','scale','qa_missing','outside_period','wrong_product','wrong_item','reverse'])
def test_failures_never_export_fake_zeros(tmp_path,monkeypatch,profile,fault):
    q,p,raws,g=sample(tmp_path,'mndwi_change',profile)
    if fault in ('cloud','shadow','nodata','zero_denominator'):
        for s in p['scenes']:
            keys=['scl' if profile=='es_s2' else 'qa_pixel'] if fault!='zero_denominator' else ['green','swir16']
            for key in keys:
                value=(9 if fault=='cloud' else 3 if fault=='shadow' else 0) if profile=='es_s2' else (8 if fault=='cloud' else 16 if fault=='shadow' else 1)
                if fault=='zero_denominator':value=0 if profile=='es_s2' else 7273 # slight positive numeric guard? explicitly test math below
                with rasterio.open(s['assets'][key]['path'],'r+') as ds:ds.write(np.full((ds.height,ds.width),value,dtype=ds.dtypes[0]),1)
        if fault=='zero_denominator' and profile=='pc_landsat':
            v,m=index('mndwi',{'green':np.array([0.]),'swir16':np.array([0.])},np.array([True]));assert not m.any() and np.isnan(v).all();return
        with pytest.raises(QualityError):execute(p,uuid4().hex)
        return
    if fault=='scale':raws[0]['assets']['green']['raster:bands'][0]['scale']=1
    if fault=='qa_missing':raws[0]['assets'].pop('scl' if profile=='es_s2' else 'qa_pixel')
    if fault=='outside_period':raws[0]['properties']['datetime']='2026-01-01T00:00:00Z'
    if fault=='wrong_product':raws[0]['properties']['s2:product_type']='L1C';raws[0]['properties']['landsat:correction']='L1TP'
    if fault=='wrong_item':raws[0]['id']='TEST_ONLY_OTHER'
    if fault=='reverse':raws.reverse()
    async def canonical(ref):
        if fault=='reverse':return {**raws[0 if ref['id']=='TEST_ONLY_0' else 1],'id':ref['id']}
        return raws[0 if ref['id']=='TEST_ONLY_0' else 1]
    monkeypatch.setattr(product_processing.media_access,'canonical',canonical)
    import asyncio
    with pytest.raises(QualityError):asyncio.run(product_processing.prepare(ProcessingRequest.model_validate(q)))

def test_user_criteria_regions_and_qa_zero_are_not_invented(tmp_path):
    q,_,_,_=sample(tmp_path,'hotspots','pc_landsat');q.pop('threshold')
    assert TestClient(app).post('/processing/plans',json=q).status_code==422
    q,_,_,_=sample(tmp_path,'temperature_comparison','pc_landsat');q['comparison_regions'][1]=q['comparison_regions'][0]
    assert TestClient(app).post('/processing/plans',json=q).status_code==422
    assert pixel_quality(np.array([64,128,8,16,1,512],dtype='uint16'),np.zeros(6,dtype='uint16')).tolist()==[True,True,False,False,False,False]
    assert kelvin_celsius(np.array([44947]))[0][0]==pytest.approx(302.62974494)

def test_thermal_uncertainty_cloud_distance_and_l2sr_rejection(tmp_path,monkeypatch):
    for key,value in [('qa',300),('cdist',0),('lwir11',0)]:
        q,p,raws,g=sample(tmp_path,'surface_temperature','pc_landsat')
        with rasterio.open(p['scenes'][0]['assets'][key]['path'],'r+') as ds:ds.write(np.full((ds.height,ds.width),value,dtype=ds.dtypes[0]),1)
        with pytest.raises(QualityError):execute(p,uuid4().hex)
    raws[0]['properties']['landsat:correction']='L2SR'
    async def canonical(ref):return raws[0]
    monkeypatch.setattr(product_processing.media_access,'canonical',canonical)
    import asyncio
    with pytest.raises(QualityError):asyncio.run(product_processing.prepare(ProcessingRequest.model_validate(q)))

def test_pc_qa_pixel_missing_header_tag_uses_actual_fill_bits(tmp_path):
    _,p,_,_=sample(tmp_path,'ndvi','pc_landsat');a=p['scenes'][0]['assets']['qa_pixel']
    with rasterio.open(a['path'],'r+') as ds:
        ds.nodata=None;data=ds.read(1);data[:ds.height//2,:]=1;ds.write(data,1)
    result=execute(p,uuid4().hex)
    assert 20<result['result']['common_valid_percent_aoi']<80
    assert next(h for h in result['result']['scenes'][0]['headers'] if h['key']=='qa_pixel')['nodata'] is None

def test_actual_water_candidate_change_not_flood_classification(tmp_path):
    q,p,_,_=sample(tmp_path,'mndwi_change');p['processing_input']['threshold']=.4
    result=execute(p,uuid4().hex);assert result['result']['statistics']['candidate_gain_area_m2']>0
    assert result['result']['statistics']['difference']['mean']==pytest.approx((.5-.2)/(.5+.2)-(.4-.2)/(.4+.2),abs=1e-6)
    assert '침수' in result['result']['conclusion']

def test_s2_offset_policy_and_header_conflict_are_not_double_corrected(tmp_path):
    from app.product_policy import asset_policy
    p=products('ndvi')[0];a={'raster:bands':[{'nodata':0,'scale':.0001,'offset':-.1,'data_type':'uint16'}]}
    props={'s2:processing_baseline':'05.11','earthsearch:boa_offset_applied':False}
    assert asset_policy('red',p,a,props)['offset']==-.1
    props['earthsearch:boa_offset_applied']=True
    with pytest.raises(QualityError):asset_policy('red',p,a,props)
    _,payload,_,_=sample(tmp_path,'ndvi')
    with rasterio.open(payload['scenes'][0]['assets']['red']['path'],'r+') as ds:ds.scales=(.00001,)
    with pytest.raises(QualityError):execute(payload,uuid4().hex)

@pytest.mark.parametrize('method',['ndvi','mndwi','mndwi_change','ndbi','surface_temperature','hotspots','temperature_comparison'])
@pytest.mark.parametrize('fault',['qa_missing','scale','period','product'])
def test_each_method_revalidates_required_assets_period_product_and_calibration(tmp_path,monkeypatch,method,fault):
    profile='pc_landsat' if method in ('surface_temperature','hotspots','temperature_comparison') else 'es_s2'
    q,_,raws,_=sample(tmp_path,method,profile);key='lwir11' if profile=='pc_landsat' else {'ndvi':'red','mndwi':'green','mndwi_change':'green','ndbi':'swir16'}[method]
    if fault=='qa_missing':raws[0]['assets'].pop('qa' if profile=='pc_landsat' else 'scl')
    if fault=='scale':raws[0]['assets'][key]['raster:bands'][0]['scale']=1
    if fault=='period':raws[0]['properties']['datetime']='2026-01-01T00:00:00Z'
    if fault=='product':raws[0]['properties'].update({'landsat:correction':'L1TP','s2:product_type':'L1C'})
    async def canonical(ref):return raws[0 if ref['id']=='TEST_ONLY_0' else 1]
    monkeypatch.setattr(product_processing.media_access,'canonical',canonical)
    import asyncio
    with pytest.raises(QualityError):asyncio.run(product_processing.prepare(ProcessingRequest.model_validate(q)))

def test_new_temperature_plan_job_and_owned_binary_download(tmp_path,monkeypatch):
    import time
    q,p,_,g=sample(tmp_path,'surface_temperature','pc_landsat')
    async def prepare(query):return p,{'width':g['width'],'height':g['height'],'tile_count':1,'resolution_m':30,'aoi_area_m2':g['aoi'].area,'maximum_aoi_km2':50}
    async def worker(payload,identifier):return execute(payload,identifier)
    monkeypatch.setattr(processing,'prepare',prepare);monkeypatch.setattr(processing,'run_file_worker',worker)
    processing.PLANS.clear();processing.JOBS.clear()
    with TestClient(app) as owner,TestClient(app) as other:
        plan=owner.post('/processing/plans',json=q);assert plan.status_code==200
        assert plan.json()['source_access']=='canonical_metadata_checked_pixels_pending'
        body={k:plan.json()[k] for k in ('plan_id','confirmation_digest')};body['idempotency_key']='TEST_ONLY_TEMPERATURE'
        job=owner.post('/processing/jobs',json=body);assert job.status_code==202;identifier=job.json()['job_id']
        for _ in range(100):
            result=owner.get('/processing/jobs/'+identifier).json()
            if result['status'] not in ('queued','running'):break
            time.sleep(.01)
        assert result['status']=='succeeded';assert other.get('/processing/jobs/'+identifier+'/download').status_code==404
        download=owner.get('/processing/jobs/'+identifier+'/download');assert download.status_code==200 and len(download.content)==result['artifact']['bytes']
        with zipfile.ZipFile(io.BytesIO(download.content)) as z:assert 'temperature.tif' in z.namelist()
    processing.PLANS.clear();processing.JOBS.clear()
