import asyncio, copy, json, zipfile
from uuid import uuid4
import numpy as np
import pytest
import rasterio
from test_product_engines import sample, private_store
from app import artifact_store, product_processing
from app.processing_worker import execute
from app.processing_models import ProcessingRequest
from app.pixel_policy import QualityError


def change(scene,key,rows,value):
    with rasterio.open(scene['assets'][key]['path'],'r+') as ds:
        a=ds.read(1);a[rows,:]=value;ds.write(a,1)


def test_cloud_only_fill_preserves_target_and_exports_provenance(tmp_path):
    q,p,_,g=sample(tmp_path,'thermal_gapfill','pc_landsat');target,donor=p['scenes']
    change(target,'qa_pixel',slice(3,12),8) # cloudy target
    change(target,'qa_pixel',slice(12,15),16) # shadow
    change(target,'lwir11',slice(15,18),0) # noncloud NoData: must stay missing
    change(target,'cdist',slice(18,20),50) # cloud-adjacent observation: eligible
    change(target,'qa',slice(21,23),300) # uncertainty alone: not a cloud gap
    change(donor,'qa_pixel',slice(6,9),8) # both cloudy: stays missing
    change(donor,'qa',slice(9,12),300) # donor fails uncertainty: stays missing
    change(donor,'lwir11',slice(None),47000)
    result=execute(p,uuid4().hex);fill=result['result']['cloud_fill']
    assert fill['filled_area_m2']>0 and fill['remaining_gap_area_m2']>0
    assert fill['target_date_restored'] is False
    path=artifact_store.verified_download(result['artifact']['filename'][11:-4],result['artifact'])
    with zipfile.ZipFile(path) as z:
        def read(name):
            with rasterio.io.MemoryFile(z.read(name)) as m:
                with m.open() as ds:return ds.read()
        status=read('pixel_status.tif')[0];out=read('multi_date_temperature.tif')[0]
        assert status[4,5]==2 and status[13,5]==2
        assert status[7,5]==0 and status[10,5]==0 and status[16,5]==0
        assert status[20,5]==1
        assert status[18,5]==2 and status[22,5]==0
        assert np.all(out[status==0]==-9999)
        assert np.allclose(out[status==1],45000*.00341802+149)
        assert np.allclose(out[status==2],47000*.00341802+149)
        assert np.array_equal(read('source_index.tif')[0],status)
        days=read('source_date.tif')[0]
        assert np.all(days[status==2]-days[20,5]==10)
        assert np.all(read('target_temperature.tif')[0][status!=1]==-9999)
        assert np.all(read('filled_only.tif')[0][status!=2]==-9999)
        manifest=json.loads(z.read('manifest.json'))
        assert next(s for s in manifest['execution_record']['steps'] if s['id']=='composite')['status']=='completed'


def test_no_clear_observation_fails_without_artifact(tmp_path):
    _,p,_,_=sample(tmp_path,'thermal_gapfill','pc_landsat')
    for s in p['scenes']:change(s,'qa_pixel',slice(None),8)
    with pytest.raises(QualityError):execute(p,uuid4().hex)


@pytest.mark.parametrize('fault',['different_platform','same_date','reverse_allowed'])
def test_canonical_date_platform_contract(tmp_path,monkeypatch,fault):
    q,p,raws,g=sample(tmp_path,'thermal_gapfill','pc_landsat')
    if fault=='different_platform':raws[1]['properties']['platform']='landsat-8'
    if fault=='same_date':raws[1]['properties']['datetime']=raws[0]['properties']['datetime']
    if fault=='reverse_allowed':q['scenes'].reverse()
    async def canonical(ref):return next(r for r in raws if r['id']==ref['id'])
    monkeypatch.setattr(product_processing.media_access,'canonical',canonical)
    if fault=='reverse_allowed':assert asyncio.run(product_processing.prepare(ProcessingRequest.model_validate(q)))[0]['scenes'][0]['id']==q['scenes'][0]['id']
    else:
        with pytest.raises(QualityError):asyncio.run(product_processing.prepare(ProcessingRequest.model_validate(q)))
