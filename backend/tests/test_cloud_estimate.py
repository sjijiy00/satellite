"""TEST_ONLY deterministic small TIFFs for local cloud-gap estimation, never service fixtures."""
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

from app import cloud_estimate,pixel_raster
from app.pixel_policy import QualityError


@pytest.fixture
def paired_tiffs(tmp_path,monkeypatch):
    size=32
    grid={'crs':'EPSG:6933','transform':from_origin(0,size*20,20,20),'width':size,'height':size,
          'aoi':box(0,0,size*20,size*20),'bbox':[0,0,size*20,size*20]}
    monkeypatch.setattr(cloud_estimate,'make_grid',lambda _:grid)
    monkeypatch.setattr(cloud_estimate,'project_footprint',lambda geom,g:pixel_raster.shape(geom))
    rows,cols=np.indices((size,size))
    donor={
        'red':(1000+4*rows+2*cols+7*((rows*cols)%17)).astype('uint16'),
        'nir':(2300+3*rows+5*cols+8*((rows+2*cols)%11)).astype('uint16'),
        'green':(1300+2*rows+7*cols+6*((3*rows+cols)%13)).astype('uint16')}
    target={
        'red':np.rint(donor['red']*.72+350).astype('uint16'),
        'nir':np.rint(donor['nir']*.78+400).astype('uint16'),
        'green':np.rint(donor['green']*.82+300).astype('uint16')}
    target_scl=np.full((size,size),4,dtype='uint8')
    target_scl[4:12,4:12]=9
    donor_scl=np.full((size,size),4,dtype='uint8')
    donor_scl[4,4]=9  # Cloud at both times stays unresolved.
    scenes=[]
    for index,(day,bands,scl) in enumerate((('2021-07-16',target,target_scl),('2021-07-26',donor,donor_scl))):
        scene={'id':f'TEST_ONLY_{index}','collection':'sentinel-2-l2a','datetime':day+'T02:00:00Z',
               'geometry':mapping(box(0,0,size*20,size*20)),'platform':'sentinel-2b',
               'processing_baseline':'03.01','boa_offset_applied':False,
               'required_keys':['red','nir','green'],'assets':{},
               'item_url':f'https://earth-search.aws.element84.com/v1/collections/sentinel-2-l2a/items/TEST_ONLY_{index}'}
        for key,values in {**bands,'scl':scl}.items():
            path=tmp_path/f'{index}-{key}.tif'
            with rasterio.open(path,'w',driver='GTiff',width=size,height=size,count=1,dtype=values.dtype,
                               crs=grid['crs'],transform=grid['transform'],nodata=0,
                               tiled=True,blockxsize=16,blockysize=16) as dst:dst.write(values,1)
            scene['assets'][key]={'path':str(path),
                'url':f'https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/TEST_ONLY/{index}-{key}.tif',
                'nodata':0,'scale':.0001,'offset':0}
        scenes.append(scene)
    payload={'bbox':[0,0,size*20,size*20],'start_date':'2021-07-01','end_date':'2021-07-31',
             'purpose':'vegetation','temporal_mode':'single','target_id':'TEST_ONLY_0',
             'minimum_valid_percent':70,'scenes':scenes}
    return payload,grid,target,donor


def _zip_rasters(report):
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(report['artifact_base64']))) as archive:
        names=set(archive.namelist())
        manifest=json.loads(archive.read('manifest.json'))
        rasters={}
        for name in names-{'manifest.json'}:
            with MemoryFile(archive.read(name)) as memory:
                with memory.open() as src:
                    rasters[name]={'pixels':src.read(),'crs':src.crs.to_string(),'nodata':src.nodata,
                                   'transform':src.transform,'descriptions':src.descriptions}
        return names,manifest,rasters


def test_plan_execute_reopen_and_observed_estimated_provenance(paired_tiffs):
    payload,grid,target,donor=paired_tiffs
    plan=cloud_estimate.process_estimate(payload|{'analysis_mode':'estimate_plan'})
    assert plan['status']=='planned' and plan['can_execute'] is True
    assert plan['artifact_base64'] is None and plan['validation']['status']=='passed'
    assert plan['areas']['observed_m2']>0 and plan['areas']['estimated_m2']>0
    assert plan['areas']['remaining_gap_m2']>0
    assert plan['source_dates']==['2021-07-26']
    result=cloud_estimate.process_estimate(payload|{'analysis_mode':'estimate_execute'})
    assert result['status']=='succeeded' and result['artifact_size_bytes']>0
    assert result['map_layers']['observed']['png_base64']
    assert result['map_layers']['estimated']['png_base64']
    names,manifest,rasters=_zip_rasters(result)
    assert names=={'target_observed.tif','estimated_only.tif','estimate_with_observed.tif',
                   'pixel_status.tif','donor_index.tif','donor_date.tif','manifest.json'}
    for name,raster in rasters.items():
        assert raster['crs']=='EPSG:6933' and raster['nodata'] is not None
        assert raster['pixels'].shape[-2:]==(32,32)
        assert raster['transform']==grid['transform']
    status=rasters['pixel_status.tif']['pixels'][0]
    source=rasters['donor_index.tif']['pixels'][0]
    dates=rasters['donor_date.tif']['pixels'][0]
    observed=rasters['target_observed.tif']['pixels']
    estimated=rasters['estimated_only.tif']['pixels']
    combined=rasters['estimate_with_observed.tif']['pixels']
    assert status[0,0]==1 and status[4,5]==2 and status[4,4]==0
    assert source[0,0]==0 and source[4,5]==1 and source[4,4]==0
    assert dates[0,0]==cloud_estimate.DATE_NODATA
    assert dates[4,5]==(date(2021,7,26)-date(1970,1,1)).days
    assert dates[4,4]==cloud_estimate.DATE_NODATA
    assert np.allclose(observed[:,0,0],[target[key][0,0]*.0001 for key in cloud_estimate.BANDS])
    assert np.allclose(combined[:,0,0],observed[:,0,0])
    assert np.all(estimated[:,0,0]==cloud_estimate.FLOAT_NODATA)
    assert np.all(observed[:,4,5]==cloud_estimate.FLOAT_NODATA)
    assert np.all(estimated[:,4,5]!=cloud_estimate.FLOAT_NODATA)
    assert np.allclose(combined[:,4,5],estimated[:,4,5])
    assert np.all(combined[:,4,4]==cloud_estimate.FLOAT_NODATA)
    assert manifest['pixel_status_encoding']['1']=='목표일 실제 관측'
    assert manifest['pixel_status_encoding']['2']=='다른 날짜 자료로 학습한 모델 추정'
    assert manifest['donor_index_mapping'][0]['id']=='TEST_ONLY_1'
    assert manifest['source_date_encoding'].startswith('int32 UTC days')
    assert manifest['validation_interpretation'].find('구름 아래 정확도')>=0


def test_insufficient_training_pairs_block_execution(paired_tiffs):
    payload,_,_,_=paired_tiffs
    path=payload['scenes'][0]['assets']['scl']['path']
    with rasterio.open(path,'r+') as dst:
        scl=np.full((32,32),9,dtype='uint8');scl[:10,:10]=4;dst.write(scl,1)
    result=cloud_estimate.process_estimate(payload|{'analysis_mode':'estimate_plan'})
    assert result['status']=='blocked' and result['can_execute'] is False
    assert result['validation']['status']=='insufficient'
    assert result['areas']['estimated_m2']==0
    assert result['artifact_base64'] is None


def test_no_improvement_over_copy_baseline_blocks_estimate(paired_tiffs):
    payload,_,_,donor=paired_tiffs
    for key in cloud_estimate.BANDS:
        with rasterio.open(payload['scenes'][0]['assets'][key]['path'],'r+') as dst:dst.write(donor[key],1)
    result=cloud_estimate.process_estimate(payload|{'analysis_mode':'estimate_plan'})
    assert result['status']=='blocked' and result['can_execute'] is False
    assert result['donors'][0]['validation']['status']=='below_baseline'
    assert result['areas']['estimated_m2']==0


@pytest.mark.parametrize('fault',['outside_period','same_day','too_far','change','wrong_purpose','wrong_baseline'])
def test_invalid_period_purpose_and_product_are_rejected(paired_tiffs,fault):
    payload,_,_,_=paired_tiffs
    if fault=='outside_period':payload['end_date']='2021-07-16'
    elif fault=='same_day':payload['scenes'][1]['datetime']='2021-07-16T08:00:00Z'
    elif fault=='too_far':payload['scenes'][1]['datetime']='2021-07-31T02:00:00Z'
    elif fault=='change':payload['temporal_mode']='change'
    elif fault=='wrong_purpose':payload['purpose']='flood'
    elif fault=='wrong_baseline':payload['scenes'][1]['processing_baseline']='05.11'
    with pytest.raises(QualityError):cloud_estimate.process_estimate(payload|{'analysis_mode':'estimate_plan'})


def test_manifest_never_contains_signed_asset_or_item_query(paired_tiffs):
    payload,_,_,_=paired_tiffs
    payload['scenes'][1]['assets']['red']['url']+='?X-Amz-Signature=TEST_SECRET_TOKEN'
    payload['scenes'][1]['item_url']+='?token=TEST_SECRET_TOKEN'
    result=cloud_estimate.process_estimate(payload|{'analysis_mode':'estimate_execute'})
    assert result['status']=='succeeded'
    _,manifest,_=_zip_rasters(result)
    serialized=json.dumps(manifest)
    assert 'TEST_SECRET_TOKEN' not in serialized
    assert 'X-Amz-Signature' not in serialized
