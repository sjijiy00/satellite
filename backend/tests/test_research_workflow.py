"""TEST ONLY: hierarchy, actual local raster tiling, durable ownership/files."""
import asyncio
import copy
import hashlib
import json
import os
import subprocess
import sys
import time
import zipfile
from uuid import uuid4
import numpy as np
import pytest
import rasterio
from fastapi.testclient import TestClient
from app import place_search as geo, artifact_store as store, processing_repository as repo, processing, work_sessions
from app.main import app
from app.pixel_policy import QualityError
from app.product_processing import execute, read_scene, read_tiled_scene
from app.processing_models import ProcessingRequest
from test_product_engines import sample


def document(first,second='',third=''):
    parts=[p for p in [first,second,third] if p]
    return {'address_type':'REGION','address_name':' '.join(parts),'x':'127.03','y':'37.26','address':dict(region_1depth_name=first,region_2depth_name=second,region_3depth_name=third,b_code='TEST_ONLY')}


@pytest.mark.parametrize('query,doc,match',[
 ('수원',document('경기도','수원시'),True),('수원시',document('경기도','수원시'),True),
 ('서울 강서구',document('서울특별시','강서구'),True),('서울 강서구',document('부산광역시','강서구'),False),
 ('수원 영통구 매탄동',document('경기도','수원시 영통구','매탄동'),True),
 ('수원 영통구 매탄동',document('경기도','수원시'),False),
 ('중구',document('서울특별시','중구'),True),('광주',document('경기도','광주시'),True),
 ('매탄동',document('경기도','수원시 영통구','매탄1동'),False),
])
def test_requested_hierarchy_is_not_replaced_with_parent(query,doc,match):
    found=geo.candidate(doc,query,'TEST_ONLY')
    assert bool(found)==match
    if found:assert found['role']=='camera_only' and 'boundary' not in found and 'bbox' not in found


@pytest.mark.parametrize('profile,method',[('es_s2','ndvi'),('pc_landsat','surface_temperature')])
def test_large_fixed_rasters_tiled_core_matches_single_read_and_saved_files(tmp_path,monkeypatch,profile,method):
    monkeypatch.setattr(store,'ROOT',tmp_path/'results')
    q,p,_,g=sample(tmp_path,method,profile,bbox=[126.7,36.4,126.8,36.48])
    assert 50e6<g['aoi'].area<200e6
    qa_key='scl' if profile=='es_s2' else 'qa_pixel'
    with rasterio.open(p['scenes'][0]['assets'][qa_key]['path'],'r+') as ds:
        a=ds.read(1);a[80:180,100:200]=9 if profile=='es_s2' else 8;a[:3,:]=0 if profile=='es_s2' else 1;ds.write(a,1)
    direct=read_scene(p['scenes'][0],g,None)
    tiled=read_tiled_scene(p['scenes'][0],g,None)
    for key,a in direct[0].items():np.testing.assert_allclose(tiled[0][key],a,equal_nan=True,atol=1e-10)
    np.testing.assert_array_equal(direct[1],tiled[1]);np.testing.assert_array_equal(direct[2],tiled[2]);np.testing.assert_array_equal(direct[4],tiled[4])
    assert sum(t['height']*t['width'] for t in tiled[5])==g['width']*g['height']
    p['bounded_tiling']=True;identifier=uuid4().hex;result=execute(p,identifier)
    assert result['result']['tiling']['enabled'] and len(result['result']['tiling']['tiles'])>1
    assert result['result']['common_valid_area_m2']<result['result']['aoi_area_m2']
    with zipfile.ZipFile(store.verified_download(identifier,result['artifact'])) as z:
        m=json.loads(z.read('manifest.json'))
        for name,e in m['files'].items():assert hashlib.sha256(z.read(name)).hexdigest()==e['sha256']


def test_failed_tile_does_not_publish_partial_artifact(tmp_path,monkeypatch):
    from app import product_processing as product
    monkeypatch.setattr(store,'ROOT',tmp_path/'results')
    _,p,_,g=sample(tmp_path,bbox=[126.7,36.4,126.8,36.48]);p['bounded_tiling']=True
    original=product.read_scene;seen=[]
    def fail(scene,grid,opener):
        seen.append(1)
        if len(seen)==2:raise QualityError('TEST ONLY denied tile')
        return original(scene,grid,opener)
    monkeypatch.setattr(product,'read_scene',fail);identifier=uuid4().hex
    with pytest.raises(QualityError,match='타일'):execute(p,identifier)
    assert not store.folder(identifier).exists()


def test_result_owner_and_verified_zip_survive_new_python_process(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'ROOT',tmp_path/'results');q,p,_,_=sample(tmp_path)
    identifier=uuid4().hex;result=execute(p,identifier)
    client=TestClient(app);request=type('Request',(),{'cookies':{}})()
    owner,cookie=work_sessions.identity(request,True)
    job={'job_id':identifier,'owner':owner,'status':'succeeded','stage':'TEST ONLY actual fixture','created_at':'TEST_ONLY','updated_at':'TEST_ONLY','input':q,'events':[],**{k:result[k] for k in ['result','artifact']},'error':None,'plan_id':uuid4().hex,'idempotency_key':uuid4().hex}
    processing.retain_terminal(job)
    script='''import json,sys
from pathlib import Path
from app import artifact_store as a,processing_repository as r,work_sessions as s
d=json.load(sys.stdin);a.ROOT=Path(d['root'])
req=type('Request',(),{'cookies':{s.COOKIE:d['cookie']}})()
owner,_=s.identity(req);j=r.load(d['id'],owner)
assert j['status']=='succeeded';assert a.verified_download(d['id'],j['artifact']).is_file()
assert r.load(d['id'],'TEST_ONLY_OTHER_OWNER') is None
print('RESTART_OWNER_AND_FULL_HASH_VERIFIED')
'''
    proc=subprocess.run([sys.executable,'-c',script],input=json.dumps({'root':str(store.ROOT),'cookie':cookie,'id':identifier}),text=True,capture_output=True,cwd=str(__import__('pathlib').Path(__file__).resolve().parents[1]),creationflags=0x08000000 if os.name=='nt' else 0)
    assert proc.returncode==0,proc.stderr
    assert proc.stdout.strip()=='RESTART_OWNER_AND_FULL_HASH_VERIFIED'
    loaded=repo.load(identifier,owner);path=store.verified_download(identifier,loaded['artifact'])
    raw=path.read_bytes();path.write_bytes(bytes([raw[0]^1])+raw[1:])
    assert store.retention(identifier,loaded['artifact'])['state']=='changed'
    with pytest.raises(QualityError):store.verified_download(identifier,loaded['artifact'])


def test_restart_marks_running_failed_and_never_replays(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'ROOT',tmp_path/'results');identifier=uuid4().hex
    repo.save({'job_id':identifier,'owner':'TEST_ONLY','status':'running','input':{},'idempotency_key':'TEST_ONLY_DUPLICATE'})
    job=repo.load(identifier,'TEST_ONLY');assert job['status']=='failed' and job['artifact'] is None
    assert repo.duplicate('TEST_ONLY','TEST_ONLY_DUPLICATE')['job_id']==identifier


def test_storage_quota_expiry_and_metadata_tamper_are_not_success(tmp_path,monkeypatch):
    monkeypatch.setattr(store,'ROOT',tmp_path/'results');q,p,_,_=sample(tmp_path)
    monkeypatch.setattr(store,'DISK_LIMIT',1)
    with pytest.raises(QualityError,match='저장'):execute(p,uuid4().hex)
    identifier=uuid4().hex;repo.save({'job_id':identifier,'owner':'TEST_ONLY','status':'cancelled','input':{}})
    with repo.connection() as db:db.execute("UPDATE jobs SET body='{}' WHERE id=?",(identifier,))
    with pytest.raises(QualityError,match='메타데이터'):repo.load(identifier,'TEST_ONLY')


def test_second_worker_cannot_execute_same_private_store(tmp_path,monkeypatch):
    from pathlib import Path
    monkeypatch.setattr(store,'ROOT',tmp_path/'results');repo.claim_worker()
    script="from pathlib import Path;import sys;from app import artifact_store as a,processing_repository as r;from app.pixel_policy import QualityError;a.ROOT=Path(sys.argv[1])\ntry:r.claim_worker()\nexcept QualityError:print('SECOND_WORKER_BLOCKED')\nelse:raise AssertionError('second worker incorrectly accepted')"
    p=subprocess.run([sys.executable,'-c',script,str(store.ROOT)],cwd=Path(__file__).resolve().parents[1],text=True,capture_output=True,creationflags=0x08000000 if os.name=='nt' else 0)
    assert p.returncode==0 and p.stdout.strip()=='SECOND_WORKER_BLOCKED'


def test_unobserved_tiles_are_recorded_not_replaced_with_valid_zeros(tmp_path,monkeypatch):
    from app import product_processing as product
    monkeypatch.setattr(store,'ROOT',tmp_path/'results')
    _,p,_,g=sample(tmp_path,bbox=[126.7,36.4,126.8,36.48]);s=p['scenes'][0]
    s['geometry']={'type':'Polygon','coordinates':[[[126.7,36.4],[126.735,36.4],[126.735,36.48],[126.7,36.48],[126.7,36.4]]]}
    result=read_tiled_scene(s,g,None)
    assert any(t['state']=='unobserved_or_outside_roi' for t in result[-1])
    assert any(t['observed_cells']>0 for t in result[-1])
