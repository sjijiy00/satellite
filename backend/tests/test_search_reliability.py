"""Synthetic transport/pages, confined to tests. Never service fallbacks."""
import asyncio
import copy
import httpx
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box, mapping, Polygon
from app import stac
from app.main import app
from app.models import SearchRequest
from app.evaluation import evaluate, rank_key
from app.metadata import normalize
from test_core import SYNTHETIC, QUERY

C1,C2='sentinel-2-l2a','landsat-c2-l2'
client=TestClient(app)

def rows(c, count, offset=0):
    result=[]
    for i in range(offset,offset+count):
        raw=copy.deepcopy(SYNTHETIC)
        raw.update(id=f'TEST_{i}',collection=c)
        result.append(raw)
    return result

def page(items, next_page=None):
    return {'features':items,'links':[] if next_page is None else [{'rel':'next','href':stac.STAC_URL+'/search','method':'POST','merge':True,'body':{'next':next_page}}]}

def search(**kwargs):
    return client.post('/search',json=QUERY|{'collections':[C1,C2]}|kwargs)

def test_partial_failure_and_unused_capacity(monkeypatch):
    async def fake(client, req, seconds):
        c=req['body']['collections'][0]
        if c==C1: raise httpx.ConnectError('synthetic')
        return page(rows(c,20))
    monkeypatch.setattr(stac,'request_page',fake)
    r=search(max_items=11)
    assert r.status_code==200
    d=r.json()
    assert d['outcome']=='partial' and d['returned']==11
    assert all(i['collection']==C2 for i in d['items'])
    assert [s['status'] for s in d['collection_statuses']]==['failed','limited']

def test_empty_collection_capacity_reused_and_no_false_truncation(monkeypatch):
    async def fake(client,req,seconds):
        c=req['body']['collections'][0]
        return page([] if c==C1 else rows(c,7))
    monkeypatch.setattr(stac,'request_page',fake)
    d=search(max_items=7).json()
    assert d['returned']==7 and not d['truncated']
    assert [s['status'] for s in d['collection_statuses']]==['empty','success']

def test_later_page_timeout_keeps_first_page(monkeypatch):
    async def fake(client,req,seconds):
        c=req['body']['collections'][0]
        if req['body'].get('next'): raise httpx.ReadTimeout('synthetic')
        return page(rows(c,2), 'p2') if c==C1 else page([])
    monkeypatch.setattr(stac,'request_page',fake)
    d=search().json()
    assert d['returned']==2 and d['outcome']=='partial'
    assert d['collection_statuses'][0]['reason']=='timeout'

def test_duplicate_identity_and_page_following(monkeypatch):
    calls=[]
    async def fake(client,req,seconds):
        calls.append(req)
        c=req['body']['collections'][0]
        return page(rows(c,2)) if req['body'].get('next') else page(rows(c,1),'p2')
    monkeypatch.setattr(stac,'request_page',fake)
    d=search().json()
    assert d['returned']==4
    assert len({(i['collection'],i['id']) for i in d['items']})==4
    assert len({i['id'] for i in d['items']})==2
    assert [s['duplicates'] for s in d['collection_statuses']]==[1,1]
    assert len(calls)==4 and not d['truncated']

def test_request_limit_bounds_repeating_pages(monkeypatch):
    async def fake(*args): return page([], 'loop')
    monkeypatch.setattr(stac,'request_page',fake)
    monkeypatch.setattr(stac,'MAX_REQUESTS',3)
    d=search().json()
    assert d['search_budget']['requests']==3
    assert d['outcome']=='partial' and d['truncated']
    assert all(s['reason']=='request_limit' for s in d['collection_statuses'])

def test_deadline_and_unqueried_collection(monkeypatch):
    clock=[0]
    monkeypatch.setattr(stac,'monotonic',lambda:clock[0])
    async def fake(*args):
        clock[0]=stac.SEARCH_SECONDS+1
        return page(rows(C1,1),'more')
    monkeypatch.setattr(stac,'request_page',fake)
    d=search().json()
    assert d['returned']==1 and d['outcome']=='partial'
    assert d['collection_statuses'][1]['status']=='not_started'
    assert d['collection_statuses'][1]['reason']=='time_limit'

def test_all_failed_vs_all_empty(monkeypatch):
    async def fail(*args): raise httpx.ReadTimeout('synthetic')
    monkeypatch.setattr(stac,'request_page',fail)
    r=search()
    assert r.status_code==504 and r.json()['outcome']=='failed'
    async def empty(*args): return page([])
    monkeypatch.setattr(stac,'request_page',empty)
    r=search()
    assert r.status_code==200 and r.json()['outcome']=='empty'

def test_invalid_item_does_not_hide_valid_items(monkeypatch):
    async def fake(client,req,seconds):
        c=req['body']['collections'][0]
        return page(rows(c,1)+[{'id':'bad','collection':c,'assets':{'bad':None}}])
    monkeypatch.setattr(stac,'request_page',fake)
    d=search().json()
    assert d['returned']==2 and d['outcome']=='partial'
    assert all(s['invalid']==1 and not s['complete'] for s in d['collection_statuses'])

def test_rank_independent_of_sensor_group_and_missing_last():
    q=SearchRequest(**QUERY)
    a=evaluate(normalize(rows(C1,1)[0]),q,'vegetation')
    b=evaluate(normalize(rows(C2,1)[0]),q,'vegetation')
    a['scene_cloud_cover']=90
    assert a['purpose_plan']['group']=='primary' and b['purpose_plan']['group']=='other'
    assert sorted([a,b],key=rank_key)[0] is b
    b['scene_cloud_cover']=None
    assert sorted([a,b],key=rank_key)[0] is a

def test_next_link_semantics_and_origin():
    original={'url':stac.STAC_URL+'/search','method':'POST','body':{'collections':[C1],'limit':25}}
    merged=stac.next_request(page([], 'abc'),original,original)
    assert merged['body']==original['body']|{'next':'abc'}
    replaced=stac.next_request({'links':[{'rel':'next','href':'/v1/search','method':'POST','body':{'next':'x'}}]},original,original)
    assert replaced['body']=={'next':'x'}
    get=stac.next_request({'links':[{'rel':'next','href':'/v1/search?next=x'}]},original,original)
    assert get['method']=='GET'
    with pytest.raises(ValueError):
        stac.next_request({'links':[{'rel':'next','href':'https://example.test/search'}]},original,original)

def test_request_wall_timeout():
    async def slow(request):
        await asyncio.sleep(.05)
        return httpx.Response(200,json=page([]))
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as c:
            with pytest.raises(asyncio.TimeoutError):
                await stac.request_page(c,{'method':'POST','url':stac.STAC_URL+'/search','body':{}},.005)
    asyncio.run(run())

@pytest.mark.parametrize('a,b,expected',[
    (mapping(box(126.5,36.3,126.7,36.8)),mapping(box(126.8,36.3,127,36.8)),False),
    (mapping(box(126,36,128,38)),mapping(box(126.5,36.3,127,36.8)),True),
    (None,mapping(box(126,36,128,38)),None),
    (mapping(box(126.5,36.3,126.7,36.8)),mapping(box(126.7,36.3,127,36.8)),False),
    (mapping(box(0,0,1,1)),mapping(box(0,0,1,1)),False),
    (mapping(Polygon([(126,36),(128,36),(128,38),(126,38)],holes=[[(126.4,36.2),(127.1,36.2),(127.1,36.9),(126.4,36.9)]])),mapping(box(126.5,36.3,127,36.8)),False),
])
def test_selection_geometry_guard(a,b,expected):
    r=client.post('/selection-overlap',json={'bbox':QUERY['bbox'],'geometry_a':a,'geometry_b':b})
    assert r.status_code==200 and r.json()['common_geometry'] is expected
def test_total_cap_one_marks_other_collection_unqueried(monkeypatch):
    async def fake(client,req,seconds): return page(rows(req['body']['collections'][0],2))
    monkeypatch.setattr(stac,'request_page',fake)
    d=search(max_items=1).json()
    assert d['returned']==1 and d['search_budget']['requests']==1
    assert d['collection_statuses'][1]['status']=='not_started'
    assert d['collection_statuses'][1]['has_more'] is None
    assert d['collection_statuses'][1]['reason']=='total_limit'
