"""Opt-in real COG window diagnostic; no fixture results in this test."""
import os
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

pytestmark=[pytest.mark.live,pytest.mark.skipif(os.getenv('LIVE_STAC')!='1',reason='LIVE_STAC=1 enables real range reads')]


def test_real_two_date_pixel_quality():
    client=TestClient(app)
    query={'purpose_type':'vegetation','purpose':'식생 변화','bbox':[126.70,36.40,126.71,36.41],
           'start_date':'2025-07-01','end_date':'2025-07-31','recommendation_id':'s2_msi','max_items':10}
    response=client.post('/search',json=query)
    assert response.status_code==200,response.text
    items=sorted(response.json()['items'],key=lambda x:x['datetime'])
    a,b=items[0],items[-1]
    query.update(scene_a={'collection':a['collection'],'id':a['id']},scene_b={'collection':b['collection'],'id':b['id']})
    response=client.post('/pixel-quality',json=query)
    assert response.status_code==200,response.text
    d=response.json()
    print(json.dumps({k:d.get(k) for k in ('status','provenance','aoi_area_m2','common_observed_area_m2','common_valid_area_m2','common_valid_percent_aoi','common_valid_percent_observed')}|{'bytes':d.get('transfer',{}).get('bytes'),'requests':d.get('transfer',{}).get('requests')},ensure_ascii=True))
    assert d['status']=='checked',d
    assert d['common_valid_area_m2'] is not None
    assert 0<=d['common_valid_percent_observed']<=100
    assert 0<d['transfer']['bytes']<=d['limits']['transfer_bytes']
    assert d['transfer']['requests']<=d['limits']['range_requests']
    assert all(s['headers'] and s['status']=='checked' for s in d['scenes'])
    assert d['analysis_ready'] is False
