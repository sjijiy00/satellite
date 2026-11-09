"""Opt-in real STAC → AOI QA plan → confirmed job → saved ZIP → TIFF reopen."""
import io
import json
import os
import time
import zipfile

import pytest
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile

from app.main import app

pytestmark=[pytest.mark.live,pytest.mark.skipif(os.getenv('LIVE_STAC')!='1',reason='LIVE_STAC=1 enables public COG integration')]

QUERY={'purpose':'식생 상태의 구름을 해결','purpose_type':'vegetation',
       'bbox':[126.70,36.40,126.71,36.41], 'start_date':'2021-07-01','end_date':'2021-07-31',
       'scene_refs':[{'collection':'sentinel-2-l2a','id':'S2B_52SBF_20210716_0_L2A'},
                     {'collection':'sentinel-2-l2a','id':'S2B_52SBF_20210726_0_L2A'}],
       'target_scene':{'collection':'sentinel-2-l2a','id':'S2B_52SBF_20210716_0_L2A'}}


def test_real_plan_confirm_job_export_and_reopen(tmp_path):
    with TestClient(app) as client:
        response=client.post('/cloud/plan',json=QUERY)
        assert response.status_code==200,response.text[:500]
        plan=response.json()
        assert plan['status']=='planned',plan.get('error')
        assert plan['can_execute'] and plan['used_scene_count']==2
        assert plan['period']['start']=='2021-07-01' and plan['period']['end']=='2021-07-31'
        assert plan['original_valid_area_m2']<plan['composite_valid_area_m2']<plan['aoi_area_m2']
        assert plan['remaining_gap_area_m2']>0
        started=client.post('/cloud/jobs',json={'plan_id':plan['plan_id'],'confirmation_digest':plan['confirmation_digest']})
        assert started.status_code==202
        job_id=started.json()['job_id']
        assert client.post('/cloud/jobs',json={'plan_id':plan['plan_id'],'confirmation_digest':plan['confirmation_digest']}).status_code==409
        deadline=time.monotonic()+115
        while time.monotonic()<deadline:
            status=client.get(f'/cloud/jobs/{job_id}').json()
            if status['status'] not in ('queued','running'):break
            time.sleep(.25)
        assert status['status']=='succeeded',status.get('error')
        response=client.get(f'/cloud/jobs/{job_id}/download')
        assert response.status_code==200 and response.content[:2]==b'PK'
        path=tmp_path/'real-observed-composite.zip';path.write_bytes(response.content)
        with zipfile.ZipFile(path) as archive:
            assert set(archive.namelist())=={'analysis_bands.tif','valid_mask.tif','source_index.tif','source_date.tif','manifest.json'}
            manifest=json.loads(archive.read('manifest.json'))
            assert manifest['used_scene_count']==2 and manifest['remaining_gap_area_m2']>0
            assert manifest['period']['start']=='2021-07-01'
            assert all('?' not in a['href'] for s in manifest['source_index_mapping'] for a in s['assets'].values())
            for name,expected in [('analysis_bands.tif',3),('valid_mask.tif',1),('source_index.tif',1),('source_date.tif',1)]:
                with MemoryFile(archive.read(name)) as mem:
                    with mem.open() as raster:
                        assert raster.count==expected and raster.crs.is_projected and raster.nodata is not None
                        assert raster.width==manifest['grid']['width'] and raster.height==manifest['grid']['height']
        print(json.dumps({k:plan[k] for k in ('original_valid_area_m2','composite_valid_area_m2','remaining_gap_area_m2','used_scene_count')}
                         | {'zip_bytes':path.stat().st_size},ensure_ascii=True))
