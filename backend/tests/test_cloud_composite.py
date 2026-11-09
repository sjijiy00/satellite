"""TEST_ONLY small GeoTIFFs: deterministic observed pixels, provenance and failure bounds."""
import base64
from datetime import date
import io
import json
import zipfile

import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from rasterio.transform import from_origin
from shapely.geometry import box,mapping

from app import cloud_composite as composite
from app import pixel_raster
from app.pixel_policy import QualityError
from app.models import CompositePlanRequest


@pytest.fixture
def tiny(tmp_path,monkeypatch):
    grid={'crs':'EPSG:6933','transform':from_origin(0,80,20,20),'width':4,'height':4,
          'aoi':box(0,0,80,80),'bbox':[0,0,80,80]}
    monkeypatch.setattr(composite,'make_grid',lambda _:grid)
    monkeypatch.setattr(composite,'project_footprint',lambda geom,g:pixel_raster.shape(geom))
    scenes=[]
    for i,day in enumerate(('2021-07-16','2021-07-26')):
        scene={'id':f'TEST_ONLY_{i}','collection':'sentinel-2-l2a','datetime':day+'T02:00:00Z',
               'geometry':mapping(box(0,0,80,80)),'platform':'sentinel-2b','processing_baseline':'03.01',
               'boa_offset_applied':False,'required_keys':['red','nir','green'],'assets':{},
               'item_url':f'https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/TEST_ONLY_{i}'}
        for key,value,dtype in (('scl',4,'uint8'),('red',1000 if i==0 else 2000,'uint16'),
                                ('nir',3000 if i==0 else 5000,'uint16'),('green',2000 if i==0 else 4000,'uint16')):
            path=tmp_path/f'{i}-{key}.tif'
            with rasterio.open(path,'w',driver='GTiff',width=4,height=4,count=1,dtype=dtype,
                               crs='EPSG:6933',transform=grid['transform'],nodata=0,
                               tiled=True,blockxsize=16,blockysize=16) as dst:
                dst.write(np.full((4,4),value,dtype=dtype),1)
            scene['assets'][key]={'path':str(path),'url':f'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/TEST_ONLY/{i}-{key}.tif',
                                  'nodata':0,'scale':.0001,'offset':0}
        scenes.append(scene)
    with rasterio.open(scenes[0]['assets']['scl']['path'],'r+') as dst:
        a=dst.read(1);a[0,0]=9;a[0,1]=3;a[0,2]=0;dst.write(a,1)
    with rasterio.open(scenes[1]['assets']['scl']['path'],'r+') as dst:
        a=dst.read(1);a[0,2]=9;dst.write(a,1)
    return {'bbox':[0,0,80,80],'start_date':'2021-07-01','end_date':'2021-07-31',
            'purpose':'vegetation','temporal_mode':'single','target_id':'TEST_ONLY_0',
            'allow_date_change':False,'minimum_valid_percent':70,'scenes':scenes},grid


def files(report):
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(report['artifact_base64']))) as archive:
        output={}
        for name in ('analysis_bands.tif','valid_mask.tif','source_index.tif','source_date.tif'):
            with MemoryFile(archive.read(name)) as mem:
                with mem.open() as raster:output[name]=(raster.read(),raster.nodata,raster.crs.to_string(),raster.descriptions)
        output['manifest']=json.loads(archive.read('manifest.json'))
        output['names']=set(archive.namelist())
        return output


def test_actual_observation_selection_and_same_source_for_every_band(tiny):
    payload,grid=tiny
    planned=composite.process_composite(payload|{'analysis_mode':'composite_plan'})
    assert planned['status']=='planned' and planned['can_execute'] and planned['artifact_base64'] is None
    assert planned['original_valid_area_m2']==5200 and planned['composite_valid_area_m2']==6000
    assert planned['remaining_gap_area_m2']==400 and planned['used_scene_count']==2
    assert planned['scenes'][0]['exclusions_m2']['cloud_cirrus']==400
    assert planned['scenes'][0]['exclusions_m2']['cloud_shadow']==400
    result=composite.process_composite(payload|{'analysis_mode':'composite_execute'})
    output=files(result)
    assert output['names']=={'analysis_bands.tif','valid_mask.tif','source_index.tif','source_date.tif','manifest.json'}
    bands,nodata,crs,descriptions=output['analysis_bands.tif']
    mask=output['valid_mask.tif'][0][0]
    source=output['source_index.tif'][0][0]
    dates=output['source_date.tif'][0][0]
    assert crs=='EPSG:6933' and nodata==-9999 and descriptions==('red','nir','green')
    assert source[0,:3].tolist()==[2,2,0] and mask[0,:3].tolist()==[1,1,0]
    assert np.allclose(bands[:,0,0],[.2,.5,.4]) and np.allclose(bands[:,1,0],[.1,.3,.2])
    assert np.all(bands[:,0,2]==-9999)
    assert dates[0,0]==(date(2021,7,26)-date(1970,1,1)).days
    assert dates[1,0]==(date(2021,7,16)-date(1970,1,1)).days
    assert output['manifest']['source_index_mapping'][1]['id']=='TEST_ONLY_1'
    assert output['manifest']['period']['end']=='2021-07-31'


@pytest.mark.parametrize('fault',['outside_period','duplicate','change','wrong_purpose','wrong_platform','wrong_baseline','wrong_scale','conflicting_offset'])
def test_conditions_never_mix_silently(tiny,fault):
    payload,_=tiny
    if fault=='outside_period':payload['end_date']='2021-07-16'
    if fault=='duplicate':payload['scenes'][1]['id']=payload['scenes'][0]['id']
    if fault=='change':payload['temporal_mode']='change'
    if fault=='wrong_purpose':payload['purpose']='flood'
    if fault=='wrong_platform':payload['scenes'][1]['platform']='sentinel-2a'
    if fault=='wrong_baseline':payload['scenes'][1]['processing_baseline']='05.11'
    if fault=='wrong_scale':payload['scenes'][1]['assets']['red']['scale']=.001
    if fault=='conflicting_offset':
        payload['scenes'][1]['boa_offset_applied']=True;payload['scenes'][1]['assets']['red']['offset']=-.1
    with pytest.raises(QualityError):composite.process_composite(payload|{'analysis_mode':'composite_execute'})


def test_all_cloud_and_missing_quality_are_not_zero_score(tiny):
    payload,_=tiny
    for scene in payload['scenes']:
        with rasterio.open(scene['assets']['scl']['path'],'r+') as dst:
            dst.write(np.full((4,4),9,dtype='uint8'),1)
    r=composite.process_composite(payload|{'analysis_mode':'composite_plan'})
    assert r['status']=='blocked' and r['scenes'][0]['status']=='checked' and r['scenes'][0]['valid_area_m2']==0
    payload['scenes'][0]['assets']['scl']['path']='TEST_ONLY_MISSING.tif'
    r=composite.process_composite(payload|{'analysis_mode':'composite_plan'})
    assert r['status']=='blocked' and r['scenes'][0]['status']=='failed' and r['scenes'][0]['valid_area_m2'] is None


def test_single_day_does_not_use_other_day(tiny):
    payload,_=tiny
    payload['scenes']=payload['scenes'][:1]
    payload['end_date']='2021-07-16'
    r=composite.process_composite(payload|{'analysis_mode':'composite_plan'})
    assert r['status']=='blocked' and not r['can_execute'] and r['artifact_base64'] is None


def test_plan_model_limits_and_duplicate_scene():
    common={'purpose_type':'vegetation','bbox':[126.7,36.4,126.71,36.41],
            'start_date':'2021-07-01','end_date':'2021-07-31',
            'scene_refs':[{'collection':'sentinel-2-l2a','id':'TEST_ONLY_1'}],
            'target_scene':{'collection':'sentinel-2-l2a','id':'TEST_ONLY_1'}}
    assert CompositePlanRequest.model_validate(common).allow_date_change is False
    with pytest.raises(ValueError):CompositePlanRequest.model_validate(common|{'scene_refs':common['scene_refs']*2})
    with pytest.raises(ValueError):CompositePlanRequest.model_validate(common|{'end_date':'2021-09-01'})
