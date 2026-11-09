"""TEST ONLY browser ownership. No provider authentication or actual worker."""
from time import monotonic
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from app.main import app
from app import cloud_jobs,work_sessions
import app.main as main


@pytest.fixture(autouse=True)
def clear():
    cloud_jobs.PLANS.clear();cloud_jobs.JOBS.clear()
    yield
    cloud_jobs.PLANS.clear();cloud_jobs.JOBS.clear()


QUERY={'purpose_type':'vegetation','bbox':[126.7,36.4,126.71,36.41],
 'start_date':'2025-07-01','end_date':'2025-07-03',
 'target_scene':{'collection':'sentinel-2-l2a','id':'TEST_ONLY_0'},
 'scene_refs':[{'collection':'sentinel-2-l2a','id':'TEST_ONLY_0'}]}


@pytest.mark.parametrize('kind',['cloud','estimate'])
def test_plan_job_cancel_and_artifact_are_owned(monkeypatch,kind):
    async def plan(*args,**kwargs):
        cloud_jobs.PLANS['a'*32]={'expires':monotonic()+100,'digest':'b'*64}
        return {'status':'planned','plan_id':'a'*32,'confirmation_digest':'b'*64}
    monkeypatch.setattr(main,'make_plan',plan)
    owner=TestClient(app);other=TestClient(app)
    response=owner.post('/'+kind+'/plan',json=QUERY)
    assert response.status_code==200 and work_sessions.COOKIE in owner.cookies
    cookie=response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'samesite=strict' in cookie
    assert 'max-age='+str(work_sessions.TTL) in cookie
    assert other.post('/'+kind+'/jobs',json={'plan_id':'a'*32,'confirmation_digest':'b'*64}).status_code==404
    identifier,_=work_sessions.identity(Request({'type':'http','headers':[(b'cookie',f'{work_sessions.COOKIE}={owner.cookies[work_sessions.COOKIE]}'.encode())]}))
    cloud_jobs.JOBS['c'*32]={'job_id':'c'*32,'plan_id':'a'*32,'status':'succeeded','stage':'TEST ONLY',
      'created_at':'TEST ONLY','updated_at':'TEST ONLY','error':None,'result':{'status':'succeeded'},'artifact':b'PK TEST ONLY',
      'owner':identifier,'kind':'observed' if kind=='cloud' else 'estimate','expires':monotonic()+100}
    for suffix in ('','/download','/cancel'):
        method='post' if suffix=='/cancel' else 'get';path='/'+kind+'/jobs/'+'c'*32+suffix
        assert getattr(other,method)(path).status_code==404
        assert getattr(owner,method)(path).status_code==200
    # A forged cookie and a new process signing key cannot revive a prior owner.
    other.cookies.set(work_sessions.COOKIE,owner.cookies[work_sessions.COOKIE][:-1]+'x')
    assert other.get('/'+kind+'/jobs/'+'c'*32).status_code==404
    monkeypatch.setattr(work_sessions,'KEY',b'TEST_ONLY_RESTARTED_KEY')
    assert owner.get('/'+kind+'/jobs/'+'c'*32).status_code==404


def test_cross_origin_plan_is_rejected_before_worker(monkeypatch):
    async def forbidden(*args,**kwargs):raise AssertionError('No processing')
    monkeypatch.setattr(main,'make_plan',forbidden)
    assert TestClient(app).post('/cloud/plan',json=QUERY,headers={'Origin':'https://evil.test'}).status_code==403
