"""SYNTHETIC fixtures: never used by the running application."""
import copy
import json
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box, mapping
from app import main, stac
from app.models import SearchRequest
from app.purposes import classify
from app.recommendations import recommend
from app.metadata import normalize
from app.evaluation import overlap_percent, evaluate, rank_key
from app.assets import raster_assets

client = TestClient(main.app)
QUERY = {'purpose': '침수 분석', 'purpose_type':'flood', 'bbox': [126.5, 36.3, 127, 36.8], 'start_date': '2025-07-01', 'end_date': '2025-07-31', 'max_items': 25, 'collections':['sentinel-2-l2a']}
SYNTHETIC = {'id': 'TEST_ONLY_SYNTHETIC', 'collection': 'sentinel-2-l2a', 'geometry': mapping(box(126.5,36.3,127,36.8)),
             'properties': {'datetime': '2025-07-12T02:30:00Z', 'platform': 'test-platform', 'instruments': ['test-sensor'], 'eo:cloud_cover': 0, 's2:product_type': 'S2MSI2A'},
             'assets': {'red': {'href':'https://example.test/red.tif','type':'image/tiff','gsd': 10, 'eo:bands': [{'common_name': 'red'}]}, 'nir': {'href':'https://example.test/nir.tif','type':'image/tiff','gsd': 20, 'eo:bands': [{'common_name': 'nir'}]}}}


@pytest.mark.parametrize('patch', [
    {'bbox': None}, {'bbox': [127,36,126,37]}, {'bbox':[0,0,6,1]}, {'bbox':[0,-81,1,-79]},
    {'start_date':'2025-08-01'}, {'start_date':'2023-01-01'}, {'start_date':'bad'},
    {'collections':[]}, {'collections':['unregistered-product']}, {'max_items':101}, {'max_items':0},
])
def test_invalid_inputs(patch):
    r = client.post('/search', json=QUERY | patch)
    assert r.status_code == 422
    assert r.json()['error']['code'] == 'INVALID_INPUT'


def test_unknown_or_ambiguous_purpose():
    assert classify('알 수 없는 목적', None)[0] is None
    assert classify('식생과 열환경', None)[0] is None
    assert client.post('/search', json=QUERY | {'purpose':'알 수 없음','purpose_type':None}).json()['error']['code'] == 'PURPOSE_REQUIRED'
    assert recommend('알 수 없음','vegetation')['purpose_type'] == 'vegetation'


def test_recommendations():
    assert recommend('도시 변화')['collections'] == ['sentinel-2-l2a','landsat-c2-l2','pc-sentinel-2-l2a','pc-landsat-c2-l2','hls-l30-002','hls-s30-002']
    assert recommend('열환경')['collections'] == ['landsat-c2-l2','pc-landsat-c2-l2']
    assert '실제 검색 지원' in recommend('홍수')['future'][0]


def test_missing_and_zero_metadata():
    missing = normalize({'id':'TEST_MISSING','properties':{},'assets':{}})
    assert missing['scene_cloud_cover'] is None
    assert missing['resolution_m'] == []
    assert missing['processing_level'] is None
    assert missing['geometry'] is None
    full = normalize(SYNTHETIC)
    assert full['scene_cloud_cover'] == 0
    assert full['resolution_m'] == [10,20]
    assert full['thumbnail'] is None
    assert normalize({'id':'TEST_LANDSAT','properties':{'landsat:correction':'L2SP'}})['processing_level'] == 'L2SP'


def test_overlap_is_geometric():
    assert overlap_percent(mapping(box(126,36,128,38)), QUERY['bbox']) == 100
    assert overlap_percent(mapping(box(0,0,1,1)), QUERY['bbox']) == 0
    assert overlap_percent(None, QUERY['bbox']) is None
    assert overlap_percent(mapping(box(126.5,36.3,126.75,36.8)), QUERY['bbox']) == pytest.approx(50, abs=0.1)


def test_evaluation_and_order():
    q = SearchRequest(**QUERY)
    full = evaluate(normalize(SYNTHETIC),q,'vegetation')
    missing = evaluate(normalize({'id':'TEST_MISSING'}),q,'vegetation')
    assert full['evaluation']['status'] == '판정 보류'
    assert full['evaluation']['days_from_start'] == 11
    assert full['evaluation']['sensor_match'] is True
    assert sorted([missing, full],key=rank_key)[0] == full
    thermal = evaluate(normalize(SYNTHETIC),q,'thermal')
    assert thermal['evaluation']['sensor_match'] is False


def test_api_success_and_limit(monkeypatch):
    async def page(*args): return {'features':[copy.deepcopy(SYNTHETIC)],'links':[{'rel':'next','href':stac.STAC_URL+'/search','method':'POST','merge':True,'body':{'next':'test'}}]}
    monkeypatch.setattr(stac,'request_page',page)
    r = client.post('/search',json=QUERY)
    assert r.status_code == 200
    data = r.json()
    assert data['items'][0]['id'] == 'TEST_ONLY_SYNTHETIC'
    assert data['items'][0]['geometry'] == json.loads(json.dumps(SYNTHETIC['geometry']))
    assert data['truncated'] is True


def test_empty(monkeypatch):
    async def page(*args): return {'features':[], 'links':[]}
    monkeypatch.setattr(stac,'request_page',page)
    assert client.post('/search',json=QUERY).json()['returned'] == 0


@pytest.mark.parametrize('message,status',[('Read timed out',504),('Connection failed',502)])
def test_network_errors(monkeypatch,message,status):
    async def fail(*args,**kwargs):
        import httpx
        raise httpx.ReadTimeout(message) if status==504 else httpx.ConnectError(message)
    monkeypatch.setattr(stac,'request_page',fail)
    response = client.post('/search',json=QUERY)
    assert response.status_code == status
    assert response.json()['error']['code'] == 'STAC_ERROR'


def test_health():
    assert client.get('/health').json() == {'status':'ok','phase':1}


def test_raster_download_links_preserve_urls_and_restrictions():
    result = raster_assets({
        'red': {'href':'https://example.test/red.tif','type':'image/tiff; application=geotiff'},
        'thermal': {'href':'s3://example/thermal.tif','type':'image/tiff','storage:requester_pays':True},
        'paid-http': {'href':'https://example.test/paid.tif','type':'image/tiff','storage:requester_pays':True},
        'unsafe': {'href':'javascript:alert(1)','type':'image/tiff'},
        'thumbnail': {'href':'https://example.test/thumb.jpg','type':'image/jpeg'},
    })
    assert len(result) == 3
    assert result[0]['direct_url'] == 'https://example.test/red.tif'
    restricted = {a['key']:a for a in result[1:]}
    assert restricted['thermal']['href'] == 's3://example/thermal.tif'
    assert restricted['thermal']['direct_url'] is None
    assert restricted['paid-http']['direct_url'] is None
    assert raster_assets({}) == []
