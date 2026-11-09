"""Synthetic provider transports only. No fixtures are imported by the application."""
import asyncio
import copy
from urllib.parse import urlsplit, parse_qs
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import stac, cmr, copernicus, catalog_discovery
from app.models import SearchRequest
from app.metadata import normalize
from app.provider_registry import COLLECTION_REGISTRY
from app.recommendations import recommend
from app.safe_urls import safe_url
from test_core import QUERY, SYNTHETIC

client=TestClient(app)


def s1(id='TEST_ONLY_SAR', day='2025-07-05'):
    raw=copy.deepcopy(SYNTHETIC)
    raw.update(id=id,collection='sentinel-1-grd')
    raw['properties']={'datetime':day+'T04:00:00Z','platform':'sentinel-1a','instruments':['sar'],
       'processing:level':'L1','product:type':'IW_GRDH_1S','sar:instrument_mode':'IW',
       'sar:polarizations':['VV','VH'],'sat:orbit_state':'descending','sar:pixel_spacing_range':10}
    raw['assets']={'vv':{'href':'s3://eodata/TEST/vv.tiff','type':'image/tiff','roles':['data']},
                   'Product':{'href':'https://download.dataspace.copernicus.eu/odata/v1/Products(TEST)/$value','type':'application/zip','roles':['data']}}
    return raw


def entry(id='G_TEST_ONLY-LPCLOUD', day='2025-07-05'):
    return {'id':id,'collection_concept_id':'C2631841556-LPCLOUD','time_start':day+'T00:00:00Z',
      'time_end':day+'T23:59:59Z','polygons':[['36 126 36 127 37 127 37 126 36 126']],
      'links':[{'rel':'http://esipfed.org/ns/fedsearch/1.1/data#','href':'https://example.test/TEST.h5'},
               {'rel':'http://esipfed.org/ns/fedsearch/1.1/browse#','href':'https://example.test/TEST.jpg'}]}


def page(rows,links=None):return {'features':rows,'links':links or []}


def test_mult_provider_partial_identity_dates_and_global_cap(monkeypatch):
    calls=[]
    async def fake(c,req,seconds):
        calls.append(req)
        if 'dataspace' in req['url']:
            raise httpx.ReadTimeout('TEST ONLY')
        return page([copy.deepcopy(SYNTHETIC)])
    async def nasa(*args):return page([cmr.granule(entry()),cmr.granule(entry(id='G_TEST_OUT',day='2025-08-01'))])
    monkeypatch.setattr(stac,'request_page',fake)
    monkeypatch.setattr(cmr,'request_page',nasa)
    q=QUERY|{'purpose':'식생','purpose_type':'vegetation','collections':['sentinel-2-l2a','landsat-c2-l2','sentinel-1-grd','viirs-vnp09ga-002'],'max_items':2}
    d=client.post('/search',json=q).json()
    assert d['outcome']=='partial' and d['returned']==2
    assert {i['provider_id'] for i in d['items']}=={'earth-search','nasa-cmr'}
    statuses={s['collection']:s for s in d['collection_statuses']}
    assert statuses['sentinel-1-grd']['reason']=='timeout'
    assert statuses['viirs-vnp09ga-002']['filtered']==1
    assert d['query']['bbox']==q['bbox'] and d['query']['end_date']==q['end_date']
    assert all(req.get('body',{}).get('bbox',q['bbox'])==q['bbox'] for req in calls)
    assert statuses['landsat-c2-l2']['invalid']==1  # wrong upstream collection rejected


def test_cdse_paging_duplicates_and_rejected_out_of_period(monkeypatch):
    requests=[]
    async def fake(c,req,seconds):
        requests.append(req)
        if len(requests)==1:
            return page([s1(),s1(day='2025-08-01',id='TEST_OUT')],
                        [{'rel':'next','href':copernicus.ENDPOINT+'/search?page=2'}])
        return page([s1(),s1('TEST_ONLY_SECOND')])
    monkeypatch.setattr(stac,'request_page',fake)
    d=client.post('/search',json=QUERY|{'recommendation_id':'s1_csar','max_items':10}).json()
    assert d['returned']==2 and d['collections']==['sentinel-1-grd']
    status=d['collection_statuses'][0]
    assert status['duplicates']==1 and status['filtered']==1 and status['complete']
    assert parse_qs(urlsplit(requests[0]['url']).query)['bbox']==['126.5,36.3,127.0,36.8']
    for item in d['items']:
        assert item['sar']['sar:polarizations']==['VV','VH']
        assert item['sar']['sat:orbit_state']=='descending'
        assert item['purpose_plan']['profile_id']=='s1_csar' and item['purpose_plan']['group']=='primary'
        assert item['pixel_quality']['status']=='not_checked' and item['scene_cloud_cover'] is None
        assert all(a['authentication_required'] and a['direct_url'] is None for a in item['download_assets'])
        assert item['support']['file_access']=='authentication_required'


def test_cmr_json_paging_and_normalization():
    calls=[]
    async def transport(req):
        calls.append(str(req.url))
        return httpx.Response(200,json={'feed':{'entry':[entry()]}},headers={'CMR-Hits':'26'})
    async def run():
        query=SearchRequest(**QUERY)
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as c:
            first=cmr.initial(query,cmr.COLLECTION)
            result=await cmr.request_page(c,first,1)
            assert result['links'][0]['href'].endswith('sort_key=-start_date')
            assert parse_qs(urlsplit(result['links'][0]['href']).query)['page_num']==['2']
            assert stac.next_request(result,first,first)['url']==result['links'][0]['href']
            await cmr.request_page(c,{'url':result['links'][0]['href']},1)
            normalized=normalize(result['features'][0])
            assert normalized['platform']=='suomi-npp' and normalized['instruments']==['viirs']
            assert normalized['geometry']['coordinates'][0][0][0]==[126,36] # CMR lat lon conversion
            assert normalized['scene_cloud_cover'] is None and normalized['resolution_m']==[]
            assert normalized['download_assets'][0]['direct_url'] is None
            assert normalized['download_assets'][0]['media_type']=='application/x-hdf5'
            assert normalized['thumbnail']=='https://example.test/TEST.jpg'
            assert normalized['remote_collection']=='C2631841556-LPCLOUD'
    asyncio.run(run())
    assert len(calls)==2


@pytest.mark.parametrize('mode',['empty','failed','limited'])
def test_cmr_statuses_and_request_cap(monkeypatch,mode):
    async def fake(*args):
        if mode=='failed':raise httpx.ConnectError('TEST ONLY')
        return page([], [{'rel':'next','href':cmr.ENDPOINT+'/granules.json?page_num=2'}] if mode=='limited' else [])
    monkeypatch.setattr(cmr,'request_page',fake)
    r=client.post('/search',json=QUERY|{'purpose':'식생','purpose_type':'vegetation','recommendation_id':'viirs_sr'})
    d=r.json();status=d['collection_statuses'][0]
    assert status['status']==mode
    assert next(c for c in d['recommendation']['cards'] if c['id']=='viirs_sr')['availability']['status']=={'empty':'none','failed':'failed','limited':'unsearched'}[mode]
    assert status['requests']<=4


def test_each_provider_searched_even_when_total_limit_one(monkeypatch):
    calls=[]
    async def fake(c,req,*args):
        calls.append(req)
        return page([s1()] if 'dataspace' in req['url'] else [copy.deepcopy(SYNTHETIC)])
    monkeypatch.setattr(stac,'request_page',fake)
    d=client.post('/search',json=QUERY|{'collections':['sentinel-2-l2a','sentinel-1-grd'],'max_items':1}).json()
    assert len(calls)==2 and d['returned']==1 and d['truncated']
    assert d['collection_statuses'][1]['returned']==0 and d['collection_statuses'][1]['buffered_not_returned']==1
    assert not d['collection_statuses'][1]['complete']


@pytest.mark.parametrize('url',[
 'https://example.test/a?X-Amz-Signature=TEST_ONLY', 'https://example.test/a?token=TEST_ONLY',
 'https://example.test/a?authKey=TEST_ONLY', 'https://example.test/a?sig=TEST_ONLY',
 'https://user:TEST_ONLY@example.test/a','javascript:alert(1)',
])
def test_sensitive_links_never_exposed(url):
    assert safe_url(url) is None
    raw=s1();raw['assets']['vv']['href']=url;raw['links']=[{'rel':'self','href':url}]
    n=normalize(raw)
    assert n['source_url'] is None
    assert not any(a['href']==url for a in n['download_assets'])


def test_processing_guards_and_interpret_context():
    q=QUERY|{'purpose_type':'vegetation','scene_a':{'collection':'sentinel-1-grd','id':'TEST_S1'},
            'scene_b':{'collection':'viirs-vnp09ga-002','id':'TEST_VIIRS'}}
    for route in ['analysis-conditions','pixel-quality','change-analysis']:
        assert client.post('/'+route,json=q).status_code==422
    r=client.post('/request/interpret',json={'purpose':'침수','followup':'두 날짜 비교',
       'selected_scene':{'provider_id':'copernicus','collection':'sentinel-1-grd','id':'TEST_S1'}})
    assert r.status_code==200
    r=client.post('/request/interpret',json=QUERY|{'purpose_type':'vegetation','followup':'이 영상은 구름이 많아',
       'selected_scene':{'provider_id':'nasa-cmr','collection':'viirs-vnp09ga-002','id':'TEST_VIIRS'}})
    assert 'cloud_plan' not in r.json()['available_actions']
    assert 'unsupported_cloud_processing' in r.json()['available_actions']


def test_registry_discovery_is_bounded_read_only(monkeypatch):
    original=httpx.AsyncClient
    async def transport(req):
        return httpx.Response(200,json={'collections':[{'id':'UNREVIEWED_TEST','title':'TEST ONLY'}],
          'links':[{'rel':'next','href':copernicus.ENDPOINT+'/collections?page=2'}]})
    monkeypatch.setattr(catalog_discovery.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(transport),**kwargs))
    before=copy.deepcopy(COLLECTION_REGISTRY)
    d=client.get('/catalog/discover/copernicus').json()
    assert d['requests']==3 and d['truncated'] and d['collections'][0]['review_required']
    assert COLLECTION_REGISTRY==before
    assert client.get('/catalog/discover/unknown').status_code==404
    assert all(not c['search_supported'] for c in client.get('/catalog').json()['unconnected_candidates'])


def test_recommendation_scales_and_variables_stay_distinct():
    v=next(c for c in recommend('식생')['cards'] if c['id']=='viirs_sr')
    assert v['id']=='viirs_sr' and v['fit']['status']=='conditional'
    assert '10 m' in ' '.join(v['constraints']) and '1 km' in v['output_grid']
    assert recommend('열환경')['collections']==['landsat-c2-l2','pc-landsat-c2-l2']
    assert recommend('도시')['collections']==['sentinel-2-l2a','landsat-c2-l2','pc-sentinel-2-l2a','pc-landsat-c2-l2','hls-l30-002','hls-s30-002']
    assert recommend('홍수',observation_need='all_weather')['collections']==['sentinel-1-grd']
