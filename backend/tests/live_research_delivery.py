"""Explicit LIVE public large AOI + restart verification. No provider credentials.

Run against an isolated server. Cookies remain only in this process's memory;
the supervisor restarts that server after READY_FOR_RESTART is printed and
creates the non-secret restart-complete marker. Never used by the application.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import httpx

assert os.getenv('LIVE_STAC')=='1' and os.getenv('LIVE_PROCESSING')=='1'
root=Path(sys.argv[1]);out=root/'live-large';out.mkdir(exist_ok=True)
base=sys.argv[2] if len(sys.argv)>2 else 'http://127.0.0.1:3012/api'
bbox=[126.7,36.4,126.8,36.48]
proof={'scope':'actual public search, canonical Range pixels, bounded single-date tiling, complete ZIP; no AI/auth/full originals','bbox':bbox,'started_utc':__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat()}
try:
    with httpx.Client(base_url=base+'/',timeout=30,trust_env=False) as c:
        r=c.post('search',json={'purpose_type':'vegetation','detail_intent':'vegetation_index','bbox':bbox,'start_date':'2021-07-01','end_date':'2021-07-31','collections':['sentinel-2-l2a'],'max_items':100})
        proof['search_http']=r.status_code;assert r.status_code==200
        data=r.json();proof['search_returned']=data['returned']
        scene=next((s for s in data['items'] if s['id']=='S2B_52SBF_20210716_0_L2A'),None)
        assert scene, 'Representative Item not in actual search; no fabricated fallback'
        catalog=c.get('analysis/catalog')
        # Existing endpoint used by the current UI, not an invented contract.
        assert catalog.status_code==200
        method=next(m for m in catalog.json()['processing_methods'] if m['id']=='ndvi')
        product=next(p for p in method['products'] if p['collection']==scene['collection'] and p['provider_id']==scene['provider_id'])
        q={'purpose_type':'vegetation','analysis_id':'vegetation_index','method_id':'ndvi','roi':{'confirmed':True,'mode':'bbox','source':'manual_bbox','bbox':bbox},'start_date':'2021-07-01','end_date':'2021-07-31','qa_policy_version':method['qa_policy_version'],
           'scenes':[{'provider_id':scene['provider_id'],'collection':scene['collection'],'id':scene['id'],'asset_keys':product['required_keys']}]}
        proof['item']=scene['id'];r=c.post('processing/plans',json=q);proof['plan_http']=r.status_code
        assert r.status_code==200,'Canonical plan failed; inspect safe HTTP status, not raw response'
        plan=r.json();proof['grid']=plan['grid'];assert plan['grid']['aoi_area_m2']>50e6 and plan['grid']['tile_count']>1
        r=c.post('processing/jobs',json={k:plan[k] for k in ('plan_id','confirmation_digest')}|{'idempotency_key':plan['plan_id']});assert r.status_code==202
        identifier=r.json()['job_id'];proof['job_id']=identifier
        deadline=time.monotonic()+280
        while time.monotonic()<deadline:
            r=c.get('processing/jobs/'+identifier);assert r.status_code==200
            job=r.json()
            if job['status'] not in ('queued','running'):break
            time.sleep(1)
        proof['job_status']=job['status'];proof['error']=job.get('error')
        assert job['status']=='succeeded',job.get('error')
        proof['tile_records']=job['result']['tiling'];assert proof['tile_records']['one_global_grid']
        artifact=job['artifact'];r=c.get('processing/jobs/'+identifier+'/download');proof['download_http']=r.status_code
        assert r.status_code==200 and len(r.content)==artifact['bytes'] and hashlib.sha256(r.content).hexdigest()==artifact['sha256']
        file=out/'large-vegetation-index.zip';file.write_bytes(r.content);proof['zip_bytes']=len(r.content);proof['zip_sha256']=artifact['sha256']
        p=subprocess.run([sys.executable,str(Path(__file__).with_name('verify_analysis_delivery.py')),str(file),str(out/'rasterio.json')],capture_output=True,text=True,creationflags=0x08000000 if os.name=='nt' else 0)
        assert p.returncode==0,'Independent Rasterio reopen failed'
        proof['stored_reopened']=True
        (out/'result.json').write_text(json.dumps(proof,indent=2),encoding='utf8')
        print('READY_FOR_RESTART',flush=True)
        deadline=time.monotonic()+600
        while not (root/'restart-complete').exists():
            assert time.monotonic()<deadline,'Restart supervision timeout'
            time.sleep(1)
        r=c.get('processing/jobs/'+identifier);assert r.status_code==200 and r.json()['status']=='succeeded'
        received=c.get('processing/jobs/'+identifier+'/download');assert received.status_code==200 and received.content==file.read_bytes()
        other=httpx.get(base+'/processing/jobs/'+identifier,trust_env=False,timeout=10);assert other.status_code==404
        archive=c.get('processing/jobs');assert archive.status_code==200 and any(j['job_id']==identifier for j in archive.json()['jobs'])
        proof['restart_same_owner_download_sha256']=hashlib.sha256(received.content).hexdigest();proof['other_session_http']=other.status_code;proof['archive_restored']=True
except Exception as e:
    proof['failure_type']=type(e).__name__
    (out/'result.json').write_text(json.dumps(proof,indent=2),encoding='utf8')
    raise
(out/'result.json').write_text(json.dumps(proof,indent=2),encoding='utf8')
print('LARGE_ZIP_REOPEN_RESTART_OWNER_VERIFIED',flush=True)
