"""LIVE integration: performs real API search and compares the canonical item."""
import os
import pytest
import requests
from fastapi.testclient import TestClient
from app.main import app
from app.stac import STAC_URL

pytestmark = [pytest.mark.live, pytest.mark.skipif(os.getenv('LIVE_STAC') != '1', reason='LIVE_STAC=1 explicitly enables real network tests')]


@pytest.mark.parametrize('collection',['sentinel-2-l2a','landsat-c2-l2'])
def test_real_search_and_canonical_item(collection):
    collections = requests.get(f'{STAC_URL}/collections',timeout=30).json()
    assert collection in [c['id'] for c in collections['collections']]
    response = TestClient(app).post('/search',json={'purpose':'식생 분석','purpose_type':'vegetation','bbox':[126.5,36.3,127,36.8],
        'start_date':'2025-07-01','end_date':'2025-07-31','collections':[collection],'max_items':3})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['source'] == 'live-stac'
    assert data['returned'] == 3
    assert data['truncated'] is True
    for item in data['items']:
        raw_response = requests.get(item['source_url'],timeout=30)
        raw_response.raise_for_status()
        raw = raw_response.json()
        assert item['id'] == raw['id']
        assert item['geometry'] == raw['geometry']
        assert item['datetime'] == raw['properties']['datetime']
        assert item['instruments'] == raw['properties'].get('instruments',[])
        assert item['scene_cloud_cover'] == raw['properties'].get('eo:cloud_cover')
        assert item['resolution_m']
        assert item['processing_level'] is not None
        for asset in item['download_assets']:
            assert asset['href'] == raw['assets'][asset['key']]['href']
            if asset['direct_url']:
                assert asset['direct_url'] == asset['href']
                assert not asset['requester_pays']
        assert item['overlap_percent'] is not None
        print(f"LIVE {item['id']} | {item['datetime']} | {item['instruments']} | cloud={item['scene_cloud_cover']} | gsd={item['resolution_m']}")


def test_real_upstream_pagination():
    response = TestClient(app).post('/search',json={'purpose':'식생 분석','purpose_type':'vegetation','bbox':[126.5,36.3,127,36.8],
        'start_date':'2025-05-01','end_date':'2025-07-31','collections':['sentinel-2-l2a'],'max_items':30})
    assert response.status_code == 200, response.text
    data=response.json()
    assert data['returned'] == 30
    assert len({item['id'] for item in data['items']}) == 30
    assert data['truncated'] is True


def test_real_public_asset_access_without_downloading_file():
    raw = requests.get(f'{STAC_URL}/collections/sentinel-2-l2a/items/S2B_52SBF_20250725_0_L2A',timeout=30).json()
    response = requests.head(raw['assets']['green']['href'],timeout=30)
    assert response.status_code == 200
    assert int(response.headers['Content-Length']) > 0


@pytest.mark.parametrize('purpose,profile,collection',[
    ('식생 변화','s2_msi','sentinel-2-l2a'),
    ('열환경','landsat_tirs','landsat-c2-l2'),
])
def test_real_recommended_product_search(purpose,profile,collection):
    response=TestClient(app).post('/search',json={'purpose':purpose,'purpose_type':{'s2_msi':'vegetation','landsat_tirs':'thermal'}[profile],'recommendation_id':profile,
        'bbox':[126.5,36.3,127,36.8],'start_date':'2025-07-01','end_date':'2025-07-31','max_items':2})
    assert response.status_code==200,response.text
    data=response.json()
    assert data['returned']==2,data
    assert data['collections']==[collection]
    card=next(c for c in data['recommendation']['cards'] if c['id']==profile)
    assert card['availability']['status']=='searched'
    for item in data['items']:
        assert item['purpose_plan']['product_status']=='met'
        assert item['purpose_plan']['missing_bands']==[]
        assert item['pixel_quality']['status']=='not_checked'
        assert item['purpose_plan']['profile_id']==profile


def test_real_a2_conditions_and_asset_head():
    client=TestClient(app)
    query={'purpose':'식생 변화','purpose_type':'vegetation','recommendation_id':'s2_msi',
           'bbox':[126.5,36.3,127,36.8],'start_date':'2025-07-01','end_date':'2025-07-31','max_items':5}
    search=client.post('/search',json=query)
    assert search.status_code==200,search.text
    items=search.json()['items']
    a,b=sorted(items[:2],key=lambda s:s['datetime'])
    response=client.post('/analysis-conditions',json=query|{
        'scene_a':{'collection':a['collection'],'id':a['id']},'scene_b':{'collection':b['collection'],'id':b['id']},
        'reference_date':b['datetime'][:10]})
    assert response.status_code==200,response.text
    d=response.json();checks={c['id']:c for c in d['checks']}
    assert checks['item-0']['status']==checks['item-1']['status']=='pass'
    assert checks['bands-0']['status']==checks['quality-0']['status']=='pass'
    assert checks['access-0-red']['status']=='pass',checks['access-0-red']
    assert d['coverage']['common_area_m2'] is not None
    assert d['assets'][0]['grid']['crs'] is not None
    assert d['pixel_quality']=='not_checked' and not d['file_headers_read']
