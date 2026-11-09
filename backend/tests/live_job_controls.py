"""Opt-in cancellation/idempotency/ownership on a real public canonical plan.
No credentials, original downloads, or signed/confirmation values are recorded.
"""
from datetime import datetime,timezone
import json,os,pathlib,sys,time
import httpx
assert os.getenv('LIVE_STAC')=='1' and os.getenv('LIVE_PROCESSING')=='1'
root=pathlib.Path(sys.argv[1]);base='http://127.0.0.1:3012'
query=json.loads((root/'live-delivery/vegetation_index/rasterio.json').read_text(encoding='utf8'))['input']
with httpx.Client(base_url=base,headers={'Origin':base},timeout=120) as client:
    response=client.post('/api/processing/plans',json=query);assert response.status_code==200
    plan=response.json();body={k:plan[k] for k in ('plan_id','confirmation_digest')};body['idempotency_key']='LIVE_VALIDATION_CANCEL_ONCE'
    started=client.post('/api/processing/jobs',json=body);assert started.status_code==202
    identifier=started.json()['job_id'];seen_running=False
    for _ in range(100):
        job=client.get('/api/processing/jobs/'+identifier).json()
        if job['status']=='running':seen_running=True;break
        assert job['status'] in ('queued','running'),job['status'];time.sleep(.05)
    assert seen_running
    cancelled=client.post('/api/processing/jobs/'+identifier+'/cancel');assert cancelled.status_code==200 and cancelled.json()['status']=='cancelled'
    repeated=client.post('/api/processing/jobs',json=body);assert repeated.json()['job_id']==identifier
    time.sleep(.3)
    restored=client.get('/api/processing/jobs/'+identifier).json();assert restored['status']=='cancelled' and restored['artifact'] is None
    download=client.get('/api/processing/jobs/'+identifier+'/download');assert download.status_code==409
    with httpx.Client(base_url=base,timeout=30) as other:
        denied=other.get('/api/processing/jobs/'+identifier);assert denied.status_code==404
    result={'at':datetime.now(timezone.utc).isoformat(),'canonical_public_plan':True,'observed_running':seen_running,'cancelled':True,
            'idempotency_same_job':True,'refresh_status':'cancelled','download_http':download.status_code,'other_session_http':denied.status_code,
            'scope':'actual running job cancelled; not a successful calculation/download proof'}
    (root/'live-job-controls.json').write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(result))
