"""Opt-in real A4 analysis and downloadable GeoTIFF/manifest validation."""
import base64
import io
import json
import os
import zipfile

import pytest
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile
from app.main import app

pytestmark=[pytest.mark.live,pytest.mark.skipif(os.getenv('LIVE_STAC')!='1',reason='LIVE_STAC=1 enables real A4 data')]

QUERY={'bbox':[126.70,36.40,126.71,36.41],'start_date':'2021-07-01','end_date':'2021-07-31',
       'purpose_type':'vegetation',
       'scene_a':{'collection':'sentinel-2-l2a','id':'S2B_52SBF_20210716_0_L2A'},
       'scene_b':{'collection':'sentinel-2-l2a','id':'S2B_52SBF_20210726_0_L2A'}}


def test_real_two_date_ndvi_and_export():
    response=TestClient(app).post('/change-analysis',json=QUERY)
    assert response.status_code==200,response.text[:500]
    d=response.json()
    print(json.dumps({k:d.get(k) for k in ('status','analysis_area_m2','common_observed_area_m2',
         'excluded_common_area_m2','ndvi_before_mean','ndvi_after_mean','ndvi_difference_mean','artifact_size_bytes')}
         |{'transfer_bytes':d.get('transfer',{}).get('bytes')},ensure_ascii=True))
    assert d['status']=='computed',d.get('error')
    assert 0<d['analysis_area_m2']<d['common_observed_area_m2']
    assert -1<=d['ndvi_before_mean']<=1 and -1<=d['ndvi_after_mean']<=1
    assert -2<=d['ndvi_difference_mean']<=2
    assert 0<d['transfer']['bytes']<=d['limits']['transfer_bytes']
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(d['artifact_base64']))) as archive:
        assert set(archive.namelist())=={'ndvi_change.tif','valid_mask.tif','processing.json'}
        record=json.loads(archive.read('processing.json'))
        assert record['sources'][0]['id']==QUERY['scene_a']['id']
        assert record['sources'][1]['id']==QUERY['scene_b']['id']
        assert record['numeric_policy']['classification_threshold'] is None
        assert all('?' not in a['href'] for s in record['sources'] for a in s['assets'].values())
        with MemoryFile(archive.read('ndvi_change.tif')) as mem:
            with mem.open() as src:
                assert src.count==3 and src.nodata==-9999 and src.crs.is_projected
                assert src.width==d['grid']['width'] and src.height==d['grid']['height']
        with MemoryFile(archive.read('valid_mask.tif')) as mem:
            with mem.open() as src:assert src.count==1 and src.nodata==0


def test_real_conflicting_offset_is_blocked():
    bad=QUERY|{'start_date':'2025-07-01','end_date':'2025-07-31',
      'scene_a':{'collection':'sentinel-2-l2a','id':'S2B_52SBF_20250705_0_L2A'},
      'scene_b':{'collection':'sentinel-2-l2a','id':'S2B_52SBF_20250725_0_L2A'}}
    d=TestClient(app).post('/change-analysis',json=bad).json()
    assert d['status']=='failed' and d['common_valid_area_m2'] is None
    assert '상충' in d['error']
    assert not d.get('artifact_base64')
