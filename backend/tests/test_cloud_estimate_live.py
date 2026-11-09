"""Opt-in public STAC/COG estimate integration. Never substitutes fixture data."""
import io
import json
import os
import time
import zipfile

import pytest
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile

from app.main import app
from test_cloud_composite_live import QUERY

pytestmark=[pytest.mark.live,pytest.mark.skipif(os.getenv('LIVE_STAC')!='1',reason='LIVE_STAC=1 enables public COG integration')]


def test_real_estimate_plan_confirm_export_and_reopen(tmp_path):
    with TestClient(app) as client:
        response=client.post('/estimate/plan',json=QUERY)
        assert response.status_code==200,response.text[:500]
        plan=response.json()
        assert plan['status']=='planned',plan.get('error')
        assert plan['can_execute'] and plan['validation']['status']=='passed'
        assert plan['areas']['observed_m2']>0 and plan['areas']['estimated_m2']>0
        started=client.post('/estimate/jobs',json={'plan_id':plan['plan_id'],'confirmation_digest':plan['confirmation_digest']})
        assert started.status_code==202,started.text
        job_id=started.json()['job_id']
        assert client.post('/estimate/jobs',json={'plan_id':plan['plan_id'],'confirmation_digest':plan['confirmation_digest']}).status_code==409
        deadline=time.monotonic()+115
        while time.monotonic()<deadline:
            status=client.get(f'/estimate/jobs/{job_id}').json()
            if status['status'] not in ('queued','running'):break
            time.sleep(.25)
        assert status['status']=='succeeded',status.get('error')
        response=client.get(f'/estimate/jobs/{job_id}/download')
        assert response.status_code==200 and response.content[:2]==b'PK'
        path=tmp_path/'real-estimated-image.zip';path.write_bytes(response.content)
        with zipfile.ZipFile(path) as archive:
            manifest=json.loads(archive.read('manifest.json'))
            assert manifest['artifact_type']=='local_supervised_estimate'
            assert manifest['period']['start']==QUERY['start_date']
            assert manifest['validation']['status']=='passed'
            assert set(archive.namelist())=={'target_observed.tif','estimated_only.tif','estimate_with_observed.tif',
                                            'pixel_status.tif','donor_index.tif','donor_date.tif','manifest.json'}
            for name in archive.namelist():
                if not name.endswith('.tif'):continue
                with MemoryFile(archive.read(name)) as mem:
                    with mem.open() as raster:
                        assert raster.crs.is_projected and raster.nodata is not None
                        assert raster.width==manifest['grid']['width'] and raster.height==manifest['grid']['height']
        print(json.dumps({'status':status['status'],'zip_bytes':path.stat().st_size,
                          'areas':plan['areas'],'validation':plan['validation']},ensure_ascii=True))
