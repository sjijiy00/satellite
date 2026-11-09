"""TEST ONLY anonymous transports; never real SAS, credentials or provider fallbacks."""
import asyncio
import copy
import json
import time
from datetime import datetime,timezone,timedelta
from urllib.parse import urlencode

import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import planetary as pc,noaa_nodd as noaa,public_media as public
from app import media_access as media,provider_transfer as transfer,operator_preview_cache as cache,stac
from app.access_paths import identity,group_paths
from app.metadata import normalize
from app.models import SearchRequest
from test_core import QUERY,SYNTHETIC
from test_media_access import png

URL='https://landsateuwest.blob.core.windows.net/landsat-c2/TEST_ONLY/QA_PIXEL.TIF'
REF={'provider_id':'planetary-computer','collection':'pc-landsat-c2-l2','id':'TEST_ONLY_PC'}
REAL_CLIENT=httpx.AsyncClient
NAME='VIIRS-Land_v001_JP113C1_NOAA-20_20250720_c20250722153011.nc'


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    pc.tokens.clear();pc.locks.clear();public.active_files.clear()
    cache.cache.clear();cache.pending.clear()
    media._tickets.clear();media._clients.clear();media._usage.clear();media._active=0
    async def dns(host):pass
    monkeypatch.setattr(transfer,'public_dns',dns)


def token(number=1,seconds=3600):
    end=(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat()
    return {'msft:expiry':end,'token':urlencode({'sig':'TEST_ONLY_'+str(number),'sp':'r','se':end})}


def xml(names,truncated=False,cursor='TEST_ONLY_CURSOR'):
    return '<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Name>noaa-cdr-ndvi-pds</Name><IsTruncated>'+str(truncated).lower()+'</IsTruncated><NextContinuationToken>'+cursor+'</NextContinuationToken>'+''.join('<Contents><Key>data/2025/'+n+'</Key><Size>64000</Size></Contents>' for n in names)+'</ListBucketResult>'


def mock(monkeypatch,handler):
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:REAL_CLIENT(transport=httpx.MockTransport(handler),**kw))


def test_pc_sas_cache_expiry_and_concurrent_renewal(monkeypatch):
    calls=[]
    async def issue(*args):
        calls.append(args);await asyncio.sleep(.01);return token(len(calls))
    monkeypatch.setattr(pc,'issue',issue)
    async def run():
        first=await asyncio.gather(*(pc.signed(REF['collection'],URL) for _ in range(4)))
        assert len(calls)==1 and len({a[1] for a in first})==1
        refreshed=await asyncio.gather(*(pc.signed(REF['collection'],URL,True,first[0][1]) for _ in range(4)))
        assert len(calls)==2 and len({a[1] for a in refreshed})==1 and first[0][1]!=refreshed[0][1]
        pc.tokens[('landsateuwest','landsat-c2')]=(time.time()-1,refreshed[0][1])
        await pc.signed(REF['collection'],URL);assert len(calls)==3
        pc.tokens.clear() # restart reacquires a public short-lived SAS, no seed credential
        await pc.signed(REF['collection'],URL);assert len(calls)==4
    asyncio.run(run())


@pytest.mark.parametrize('change',[{'token':'TEST_ONLY_INVALID'},{'msft:expiry':'not-a-date'}, {'token':urlencode({'sig':'TEST_ONLY','sp':'w','se':'2099-01-01T00:00:00Z'})}])
def test_invalid_sas_closed(monkeypatch,change):
    async def issue(*args):return token()|change
    monkeypatch.setattr(pc,'issue',issue)
    with pytest.raises(transfer.TransferError) as e:asyncio.run(pc.signed(REF['collection'],URL))
    assert e.value.code=='sas_invalid_response' and not pc.tokens


@pytest.mark.parametrize('url',[URL+'?sig=TEST_ONLY',URL.replace('landsateuwest','evil'),URL.replace('/landsat-c2/','/other/'),URL.replace('https:','http:')])
def test_signing_never_accepts_arbitrary_destinations(url):
    with pytest.raises(transfer.TransferError):pc.storage(REF['collection'],url)


def test_sas_retry_only_once_and_no_bearer_or_browser_signature(monkeypatch,caplog):
    issued=[];requests=[]
    async def issue(*args):issued.append(1);return token(len(issued))
    monkeypatch.setattr(pc,'issue',issue)
    def handler(req):
        requests.append(req)
        assert 'authorization' not in req.headers
        return httpx.Response(403) if len(requests)==1 else httpx.Response(200,content=b'II*\x00'+b'TEST_ONLY'*200)
    mock(monkeypatch,handler)
    async def canonical(ref):return {'assets':{'qa_pixel':{'href':URL,'type':'image/tiff'}}}
    monkeypatch.setattr(media,'canonical',canonical)
    client=TestClient(app);sid=client.get('/media/session').cookies.get(media.COOKIE)
    headers={'Origin':'http://127.0.0.1:3000','Cookie':media.COOKIE+'='+sid}
    with caplog.at_level('INFO'):
        r=client.post('/media/inspect',json=REF|{'include_preview':False,'asset_keys':['qa_pixel']},headers=headers)
    assert r.json()['assets'][0]['status']=='available' and len(issued)==2 and len(requests)==2
    assert 'sig=' not in r.text and 'TEST_ONLY_2' not in r.text and 'sig=' not in caplog.text
    receipt=r.json()['assets'][0]['download_url'].removeprefix('/api')
    response=client.get(receipt,headers=headers)
    assert response.status_code==200 and response.content.startswith(b'II*\x00')
    assert client.get(receipt+'/status',headers=headers).json()['download_completed']
    assert TestClient(app).get(receipt).status_code==404
    mock(monkeypatch,lambda req:httpx.Response(403))
    with pytest.raises(transfer.TransferError) as e:asyncio.run(public.fetch(REF,{'href':URL},probe=True))
    assert e.value.code=='permission_required' # two attempts, never an infinite renewal loop


def test_public_redirect_size_and_duplicate_limits(monkeypatch):
    async def issue(*args):return token()
    monkeypatch.setattr(pc,'issue',issue)
    mock(monkeypatch,lambda req:httpx.Response(302,headers={'Location':URL.replace('landsateuwest','sentinel2l2a01').replace('landsat-c2','sentinel2-l2')}))
    with pytest.raises(transfer.TransferError) as e:asyncio.run(public.fetch(REF,{'href':URL},probe=True))
    assert e.value.code=='blocked_redirect'
    with pytest.raises(transfer.TransferError) as e:asyncio.run(public.fetch(REF,{'href':URL,'file:size':transfer.FILE_BYTES+1}))
    assert e.value.code=='size_limit'
    async def slow(*args,**kw):await asyncio.sleep(.02);raise transfer.TransferError('timeout')
    monkeypatch.setattr(transfer,'read',slow)
    async def run():
        result=await asyncio.gather(public.fetch(REF,{'href':URL}),public.fetch(REF,{'href':URL}),return_exceptions=True)
        assert {e.code for e in result}=={'busy','timeout'} and not public.active_files
    asyncio.run(run())


def test_public_preview_decoded_cache_singleflight(monkeypatch):
    calls=[]
    preview='https://planetarycomputer.microsoft.com/api/data/v1/item/preview.png?'+urlencode({'collection':'landsat-c2-l2','item':REF['id']})
    mock(monkeypatch,lambda req:(calls.append(req) or httpx.Response(200,content=png(),headers={'Content-Type':'image/png'})))
    async def canonical(ref):return {'assets':{'rendered_preview':{'href':preview,'type':'image/png','roles':['overview']}}}
    monkeypatch.setattr(media,'canonical',canonical)
    client=TestClient(app);sid=client.get('/media/session').cookies.get(media.COOKIE)
    headers={'Origin':'http://127.0.0.1:3000','Cookie':media.COOKIE+'='+sid}
    for _ in range(2):
        r=client.post('/media/inspect',json=REF,headers=headers)
        assert r.json()['preview']['status']=='available'
    assert len(calls)==1 and len(cache.cache)==1


def test_noaa_netCDF_is_download_not_browser_preview(monkeypatch):
    raw=noaa.feature('data/2025/'+NAME,64000);n=normalize(raw)
    assert n['platform']=='noaa-20' and n['geometry_role']=='product_grid_extent'
    assert n['preview_diagnostic']['status']=='missing_asset' and n['scene_cloud_cover'] is None
    assert n['download_assets'][0]['size_bytes']==64000 and n['download_assets'][0]['direct_url']
    assert n['download_assets'][0]['media_type']=='application/x-netcdf'
    async def canonical(ref):return copy.deepcopy(raw)
    monkeypatch.setattr(media,'canonical',canonical)
    mock(monkeypatch,lambda req:httpx.Response(200,content=b'CDF\x02'+b'TEST_ONLY_DATA'*100))
    client=TestClient(app);sid=client.get('/media/session').cookies.get(media.COOKIE)
    headers={'Origin':'http://127.0.0.1:3000','Cookie':media.COOKIE+'='+sid}
    ref={'provider_id':'noaa-nodd','collection':noaa.COLLECTION,'id':raw['id']}
    r=client.post('/media/inspect',json=ref|{'asset_keys':['ndvi']},headers=headers)
    assert r.json()['preview']['status']=='missing_asset' and r.json()['assets'][0]['status']=='available'
    url=r.json()['assets'][0]['download_url'].removeprefix('/api')
    assert client.get(url,headers=headers).content.startswith(b'CDF\x02')
    assert 'pixel_quality' not in r.json() # file access is not a pixel-quality result


def test_noaa_page_range_cursor_and_no_fabricated_scene():
    calls=[]
    async def handler(req):
        calls.append(req)
        return httpx.Response(200,text=xml([NAME],True) if len(calls)==1 else xml([NAME.replace('20250720','20250722')]))
    async def run():
        q=SearchRequest(**(QUERY|{'start_date':'2025-07-20','end_date':'2025-07-21'}))
        async with REAL_CLIENT(transport=httpx.MockTransport(handler)) as c:
            first=noaa.initial(q,noaa.COLLECTION);a=await noaa.request_page(c,first,1)
            assert len(a['features'])==1
            next_req=stac.next_request(a,first,first)
            b=await noaa.request_page(c,next_req,1)
            assert not b['features'] and not b['links']
        assert calls[0].url.params['start-after'].endswith('20250720')
        assert calls[1].url.params['continuation-token']=='TEST_ONLY_CURSOR'
    asyncio.run(run())
    with pytest.raises(ValueError):noaa.feature('data/2022/'+NAME.replace('20250720','20220720'),100)
    with pytest.raises(ValueError):noaa.feature('data/2025/'+NAME.replace('NOAA-20','NOAA-21'),100)


def test_partial_outside_empty_duplicate_and_date_filters(monkeypatch):
    raw=copy.deepcopy(SYNTHETIC);raw['collection']='sentinel-2-l2a'
    async def earth(*args):return {'features':[raw],'links':[]}
    async def failed(*args):raise httpx.ReadTimeout('TEST ONLY')
    monkeypatch.setattr(stac,'request_page',earth);monkeypatch.setattr(pc,'request_page',failed)
    client=TestClient(app)
    r=client.post('/search',json=QUERY|{'collections':['sentinel-2-l2a','pc-sentinel-2-l2a']}).json()
    assert r['outcome']=='partial' and r['returned']==1
    assert r['collection_statuses'][1]['reason']=='timeout'
    r=client.post('/search',json=QUERY|{'collections':[noaa.COLLECTION],'purpose_type':'thermal'}).json()
    assert r['outcome']=='outside_scope' and r['search_budget']['requests']==0
    r=client.post('/search',json=QUERY|{'purpose':'지표면 온도','purpose_type':None,'collections':[noaa.COLLECTION]}).json()
    assert r['error']['code']=='PURPOSE_REQUIRED' # text is not a keyword fallback
    r=client.post('/search',json=QUERY|{'purpose_type':'vegetation','collections':[noaa.COLLECTION],'start_date':'2022-07-01','end_date':'2022-07-10'}).json()
    assert r['collection_statuses'][0]['reason']=='outside_supported_period'
    async def pcpage(*args):
        a=copy.deepcopy(raw);a['collection']='pc-sentinel-2-l2a'
        b=copy.deepcopy(a);b['id']='TEST_ONLY_OUT';b['properties']['datetime']='2026-01-01T00:00:00Z'
        return {'features':[a,a,b],'links':[]}
    monkeypatch.setattr(pc,'request_page',pcpage)
    r=client.post('/search',json=QUERY|{'collections':['pc-sentinel-2-l2a']}).json()
    assert r['returned']==1 and r['collection_statuses'][0]['duplicates']==1 and r['collection_statuses'][0]['filtered']==1
    assert r['items'][0]['support']['processing'].endswith('미지원')


def test_access_group_requires_exact_product_and_version():
    raw={'collection':'sentinel-2-l2a','properties':{'datetime':'2025-07-25T02:15:39Z','platform':'sentinel-2b',
        's2:product_uri':'S2B_MSIL2A_20250725T021539_N0511_R003_T52SBF_20250725T041758.SAFE','s2:processing_baseline':'05.11'}}
    source=identity(raw);assert source
    rows=[{'id':'TEST_ONLY_A','provider_id':'earth-search','platform':'sentinel-2b','source_product':source},
          {'id':'TEST_ONLY_B','provider_id':'planetary-computer','platform':'sentinel-2b','source_product':source}]
    group_paths(rows);assert len(rows)==2 and rows[0]['access_group']==rows[1]['access_group'] and len(rows[0]['access_paths'])==2
    raw['properties']['s2:processing_baseline']='05.12';assert identity(raw) is None
    rows[1]['source_product']={**source,'version':'different'}
    for row in rows:row.pop('access_paths');row.pop('access_group')
    group_paths(rows);assert 'access_paths' not in rows[0]


def test_pc_platform_spelling_is_normalized_without_inventing_identity():
    raw=copy.deepcopy(SYNTHETIC);raw['collection']='sentinel-2-l2a'
    raw['properties']['platform']='Sentinel-2B'
    mapped=pc.feature(raw)
    assert mapped['properties']['platform']=='sentinel-2b' and mapped['properties']['app:source_platform']=='Sentinel-2B'
    assert raw['properties']['platform']=='Sentinel-2B' and raw['collection']=='sentinel-2-l2a'
    raw['collection']='landsat-c2-l2';raw['properties']['platform']='landsat-7'
    assert pc.feature(raw) is None
