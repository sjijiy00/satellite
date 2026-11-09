"""Explicit bounded public E84 processing; no auth, paid AI or full originals."""
import hashlib
import io
import json
import os
from pathlib import Path
import time
import zipfile
from datetime import datetime,timezone
import pytest
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile
from app.main import app
from app.analysis_catalog import QA_VERSION
from app import artifact_store,processing

pytestmark=[pytest.mark.live,pytest.mark.skipif(os.getenv('LIVE_STAC')!='1' or os.getenv('LIVE_PROCESSING')!='1',reason='Explicit LIVE_STAC=1 + LIVE_PROCESSING=1 only')]

def test_public_canonical_pixels_to_verified_download(tmp_path,monkeypatch):
    monkeypatch.setattr(artifact_store,'ROOT',tmp_path/'artifacts')
    processing.PLANS.clear();processing.JOBS.clear()
    query={'purpose_type':'vegetation','analysis_id':'vegetation_change','method_id':'ndvi_change',
        'roi':{'confirmed':True,'mode':'bbox','bbox':[126.70,36.40,126.71,36.41],'source':'manual_bbox'},
        'start_date':'2021-07-01','end_date':'2021-07-31','qa_policy_version':QA_VERSION,
        'scenes':[{'provider_id':'earth-search','collection':'sentinel-2-l2a','id':id,'asset_keys':['red','nir','scl']} for id in ('S2B_52SBF_20210716_0_L2A','S2B_52SBF_20210726_0_L2A')]}
    out=Path('../test-results/foundation-20261103-200942/live');out.mkdir(parents=True,exist_ok=True)
    summary={'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'real canonical metadata + bounded public COG Range + actual generated artifact download; no full originals',
             'items':[s['id'] for s in query['scenes']],'bbox':query['roi']['bbox']}
    with TestClient(app) as client:
        r=client.post('/processing/plans',json=query);summary['plan_http']=r.status_code
        if r.status_code!=200:
            summary['plan_error']=r.json();(out/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
        assert r.status_code==200
        plan=r.json();r=client.post('/processing/jobs',json={'plan_id':plan['plan_id'],'confirmation_digest':plan['confirmation_digest'],'idempotency_key':'LIVE_PUBLIC_ONCE'})
        assert r.status_code==202;identifier=r.json()['job_id']
        end=time.monotonic()+100
        while time.monotonic()<end:
            job=client.get('/processing/jobs/'+identifier).json()
            if job['status'] not in ('queued','running'):break
            time.sleep(.5)
        summary.update(status=job['status'],error=job.get('error'))
        if job.get('result'):
            summary.update({k:job['result'].get(k) for k in ('analysis_area_m2','common_observed_area_m2','common_valid_percent_aoi','ndvi_before_mean','ndvi_after_mean','ndvi_difference_mean','tiling','transfer')})
            # Only public source references exist, but retain counts rather than URL lists.
            summary['transfer']={k:summary['transfer'].get(k) for k in ('bytes','requests')}
        (out/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
        assert job['status']=='succeeded',job.get('error')
        assert 0<job['result']['transfer']['bytes']<=64*1024**2
        r=client.get('/processing/jobs/'+identifier+'/download');assert r.status_code==200
        assert r.headers['content-type']=='application/zip' and len(r.content)==job['artifact']['bytes']
        assert hashlib.sha256(r.content).hexdigest()==job['artifact']['sha256']
        (out/'actual-processing-result.zip').write_bytes(r.content)
        with zipfile.ZipFile(io.BytesIO(r.content)) as z:
            manifest=json.loads(z.read('manifest.json'));assert manifest['verified_after_disk_write']
            for name,proof in manifest['files'].items():
                assert hashlib.sha256(z.read(name)).hexdigest()==proof['sha256']
                if name.endswith('.tif'):
                    with MemoryFile(z.read(name)) as mem:
                        with mem.open() as ds:assert ds.crs and ds.nodata is not None and ds.read().size>0
        summary.update(download_bytes=len(r.content),download_sha256=job['artifact']['sha256'],full_download_and_reopen=True)
        (out/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
