"""Explicit LIVE_STAC=1 only. Public metadata search and bounded HEAD, no login/download."""
import os
from urllib.parse import urlsplit
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app

pytestmark=[pytest.mark.live,pytest.mark.skipif(os.getenv('LIVE_STAC')!='1',reason='LIVE_STAC=1 enables public provider checks')]


@pytest.mark.parametrize('profile,purpose,provider',[
 ('s2_msi','vegetation','earth-search'),('landsat_tirs','thermal','earth-search'),
 ('s1_csar','flood','copernicus'),('viirs_sr','vegetation','nasa-cmr')])
def test_public_provider_search_and_access(profile,purpose,provider):
    response=TestClient(app).post('/search',json={'purpose_type':purpose,'recommendation_id':profile,
       'bbox':[126.7,36.4,126.71,36.41],'start_date':'2025-07-20','end_date':'2025-07-26','max_items':2})
    assert response.status_code==200
    data=response.json()
    assert data['items'] and data['collection_statuses'][0]['provider_id']==provider
    scene=data['items'][0]
    assert scene['provider_id']==provider and scene['purpose_plan']['profile_id']==profile
    assert scene['pixel_quality']['status']=='not_checked'
    assert all('2025-07-20'<=s['datetime'][:10]<='2025-07-26' for s in data['items'])
    print('LIVE',provider,'count',data['returned'],'item',scene['id'],'requests',data['search_budget']['requests'])
    with httpx.Client(timeout=20,follow_redirects=False) as c:
        canonical=c.get(scene['source_url'])
        assert canonical.status_code==200
        print('canonical',canonical.status_code)
        if scene['thumbnail']:
            preview=c.head(scene['thumbnail'])
            print('preview HEAD',preview.status_code,'type',preview.headers.get('content-type'))
        if provider=='copernicus':
            asset=next(a for a in scene['download_assets'] if a['key']=='Product')
        elif provider=='nasa-cmr':asset=scene['download_assets'][0]
        else:asset=next((a for a in scene['download_assets'] if a['direct_url']),None)
        if asset is None:
            print('file HEAD not performed: no anonymous HTTP asset; S3/requester-pays restriction preserved')
            return
        if asset['href'].startswith('https:'):
            head=c.head(asset['href'])
            print('file HEAD',head.status_code,'redirect_host',urlsplit(head.headers.get('location','')).hostname)
        if provider!='earth-search':
            assert all(a['authentication_required'] and not a['direct_url'] for a in scene['download_assets'])
