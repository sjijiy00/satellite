"""TEST ONLY fixed TIFF QA failures, private journals and local quota clocks."""
import asyncio
import io
import json
import math
from uuid import uuid4
import numpy as np
import pytest
import rasterio
from app import artifact_store, media_access, processing, processing_repository, processing_worker
from app.processing_failure import ProcessingBlocked
from app.provider_transfer import TransferError
from test_product_engines import sample


@pytest.mark.parametrize('key,value,reason,code',[
    ('qa',300,'st_uncertainty','no_valid_pixels'),
    ('cdist',50,'cloud_distance','no_valid_pixels'),
    ('qa_pixel',8,'base_qa_or_required_data','no_valid_pixels'),
    ('lwir11',0,'band_nodata_or_unobserved','no_observations'),
])
def test_completed_qa_failure_retains_measured_reasons_without_artifact(tmp_path,monkeypatch,key,value,reason,code):
    monkeypatch.setattr(artifact_store,'ROOT',tmp_path/'artifacts')
    _,payload,_,_=sample(tmp_path,'surface_temperature','pc_landsat')
    with rasterio.open(payload['scenes'][0]['assets'][key]['path'],'r+') as ds:
        ds.write(np.full((ds.height,ds.width),value,dtype=ds.dtypes[0]),1)
    identifier=uuid4().hex
    with pytest.raises(ProcessingBlocked) as caught:
        processing_worker.execute(payload,identifier)
    failure=caught.value.failure;qa=failure['qa']
    assert failure['code']==code and qa['status']=='checked_no_valid'
    assert qa['valid_area_m2']==0 and qa['aoi_area_m2']>0
    assert qa['scenes'][0]['exclusions_m2'][reason]>0
    assert 'statistics' not in qa and 'map_layers' not in qa
    assert not artifact_store.folder(identifier).exists()


def test_worker_transports_diagnostics_but_not_partial_network_failure(monkeypatch,tmp_path):
    monkeypatch.setattr(processing_worker,'open_sources',lambda _:None)
    envelope=json.dumps({'storage_root':str(tmp_path),'payload':{},'job_id':uuid4().hex})
    for error,expected in [(ProcessingBlocked('TEST ONLY QA',{'code':'no_valid_pixels'}),{'code':'no_valid_pixels'}),(RuntimeError('TEST ONLY partial read'),None)]:
        monkeypatch.setattr(processing_worker.sys,'stdin',io.StringIO(envelope))
        stdout=io.StringIO();monkeypatch.setattr(processing_worker.sys,'stdout',stdout)
        def fail(*args):raise error
        monkeypatch.setattr(processing_worker,'execute',fail)
        processing_worker.main();reply=json.loads(stdout.getvalue())
        assert reply['status']=='failed' and reply['failure']==expected
        assert reply['result']['common_valid_area_m2'] is None


def test_worker_failure_survives_parent_and_owner_journal(tmp_path,monkeypatch):
    monkeypatch.setattr(artifact_store,'ROOT',tmp_path/'artifacts')
    monkeypatch.setattr(media_access,'_usage',{})
    payload={'method_id':'surface_temperature'}
    failure={'code':'no_valid_pixels','qa':{'status':'checked_no_valid','valid_area_m2':0}}
    async def prepare(_):return payload,{}
    async def run(*_):return {'status':'failed','error':'TEST ONLY completed QA','failure':failure}
    monkeypatch.setattr(processing,'prepare',prepare);monkeypatch.setattr(processing,'run_file_worker',run)
    identifier=uuid4().hex
    job={'job_id':identifier,'owner':'TEST_ONLY_OWNER','status':'queued','artifact':None,'events':[],'input':{},'created_at':processing.stamp()}
    asyncio.run(processing.execute(identifier,job,{'query':None,'payload_digest':processing.digest(payload)}))
    assert job['failure']==failure and job['artifact'] is None
    assert job['result']['common_valid_percent_aoi'] is None
    restored=processing_repository.load(identifier,'TEST_ONLY_OWNER')
    assert restored['failure']==failure and processing.public(restored)['failure']==failure
    assert processing_repository.load(identifier,'TEST_ONLY_OTHER') is None


def test_quota_retry_waits_for_latest_blocking_window_without_charge(monkeypatch):
    monkeypatch.setattr(media_access.time,'monotonic',lambda:1000.25)
    monkeypatch.setattr(media_access,'_usage',{'TEST_ONLY_OWNER':(10.,100),'TEST_ONLY_GLOBAL':(20.,100)})
    before=dict(media_access._usage)
    with pytest.raises(TransferError) as caught:
        media_access.charge_many(('TEST_ONLY_OWNER','TEST_ONLY_GLOBAL'),1,limit=100)
    assert caught.value.retry_after_seconds==math.ceil(20+3600-1000.25)
    assert media_access._usage==before


def test_quota_failure_records_retry_time_without_starting_worker(tmp_path,monkeypatch):
    monkeypatch.setattr(artifact_store,'ROOT',tmp_path/'artifacts')
    payload={}
    async def prepare(_):return payload,{}
    def deny(*_):
        error=TransferError('quota_limit');error.retry_after_seconds=125;raise error
    async def unexpected(*_):pytest.fail('worker must not start')
    monkeypatch.setattr(processing,'prepare',prepare);monkeypatch.setattr(media_access,'charge_many',deny)
    monkeypatch.setattr(processing,'run_file_worker',unexpected)
    job={'owner':'TEST_ONLY','status':'queued','artifact':None,'events':[]}
    asyncio.run(processing.execute(uuid4().hex,job,{'query':None,'payload_digest':processing.digest(payload)}))
    assert job['failure']['code']=='transfer_quota' and job['failure']['retry_at']
    assert job['result']['common_valid_area_m2'] is None
