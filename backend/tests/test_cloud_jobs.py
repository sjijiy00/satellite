"""In-process job state, duplicate guard and cancellation; no service fixtures."""
import asyncio
from time import monotonic

import pytest
from fastapi import HTTPException

from app import cloud_jobs


def test_cancelled_job_cannot_publish_late_result(monkeypatch):
    payload={'bbox':[126.7,36.4,126.71,36.41],'scenes':[]}
    digest=cloud_jobs._digest(payload)
    async def prepare(_):return payload,0
    async def slow(_):await asyncio.sleep(10)
    monkeypatch.setattr(cloud_jobs,'_payload',prepare)
    monkeypatch.setattr(cloud_jobs,'run_worker',slow)
    async def scenario():
        cloud_jobs.PLANS.clear();cloud_jobs.JOBS.clear()
        cloud_jobs.PLANS['a'*32]={'query':object(),'payload':payload,'digest':digest,'expires':monotonic()+100}
        first=cloud_jobs.start_job('a'*32,digest)
        with pytest.raises(HTTPException) as error:cloud_jobs.start_job('a'*32,digest)
        assert error.value.status_code==409
        await asyncio.sleep(.01)
        assert cloud_jobs.get_job(first['job_id'])['status']=='running'
        cancelled=cloud_jobs.cancel_job(first['job_id'])
        assert cancelled['status']=='cancelled'
        await asyncio.sleep(.02)
        assert cloud_jobs.get_job(first['job_id'])['status']=='cancelled'
        assert cloud_jobs.get_job(first['job_id'])['artifact'] is None
        cloud_jobs.PLANS.clear();cloud_jobs.JOBS.clear()
    asyncio.run(scenario())


def test_confirmation_digest_and_plan_expiry():
    cloud_jobs.PLANS.clear();cloud_jobs.JOBS.clear()
    cloud_jobs.PLANS['b'*32]={'query':object(),'payload':{},'digest':'f'*64,'expires':monotonic()+100}
    with pytest.raises(HTTPException) as error:cloud_jobs.start_job('b'*32,'0'*64)
    assert error.value.status_code==409
    cloud_jobs.PLANS['b'*32]['expires']=monotonic()-1
    with pytest.raises(HTTPException) as error:cloud_jobs.start_job('b'*32,'f'*64)
    assert error.value.status_code==404
    cloud_jobs.PLANS.clear()
