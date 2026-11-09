"""TEST ONLY provider bytes/OAuth transport. No user secrets or live credentials."""
import asyncio
import copy
import json
import logging
import struct
import time
import zlib
from io import BytesIO
from urllib.parse import urlsplit

import httpx
import pytest
from fastapi import Request
from fastapi.testclient import TestClient
from app.main import app
from app import earthdata_auth as auth, media_access as media, provider_transfer as transfer, landsat_access as landsat
from test_core import SYNTHETIC
from test_earthdata_auth import configured
from app.log_safety import AccessFilter

ORIGIN={'Origin':'http://127.0.0.1:3000'}
REF={'provider_id':'nasa-cmr','collection':'viirs-vnp09ga-002','id':'G_TEST_ONLY-LPCLOUD'}
DATA='https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-protected/VNP09GA.002/TEST_ONLY/TEST_ONLY.h5'
BROWSE='https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-public/VNP09GA.002/TEST_ONLY/TEST_ONLY.png'
REAL_ASYNC_CLIENT=httpx.AsyncClient
REAL_PUBLIC_DNS=transfer.public_dns


def png():
    def chunk(kind,data):return struct.pack('!I',len(data))+kind+data+struct.pack('!I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('!2I5B',1,1,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b'\x00\x00\x80\x00'))+chunk(b'IEND',b'')


def raw():
    return {'id':REF['id'],'collection':REF['collection'],'properties':{},'assets':{
      'browse':{'href':BROWSE,'type':'image/png','roles':['thumbnail']},
      'granule':{'href':DATA,'type':'application/x-hdf5','roles':['data']}}}


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    media._tickets.clear();media._clients.clear();media._usage.clear();media._active=0
    auth._sessions.clear();auth._pending.clear()
    async def dns(host):pass
    monkeypatch.setattr(transfer,'public_dns',dns)


def mock_transport(monkeypatch,handler):
    monkeypatch.setattr(transfer.httpx,'AsyncClient',lambda **kwargs:REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler),**kwargs))


def canonical(monkeypatch,value=None):
    async def fake(reference):
        assert reference==REF
        return copy.deepcopy(value if value is not None else raw())
    monkeypatch.setattr(media,'canonical',fake)


def inspect(client,body=None,cookies=''):
    if media.COOKIE+'=' not in cookies:
        session=client.get('/media/session')
        sid=session.cookies.get(media.COOKIE)
        cookies='; '.join(filter(None,[cookies,f'{media.COOKIE}={sid}']))
    r=client.post('/media/inspect',json=REF|(body or {}),headers=ORIGIN|({'Cookie':cookies} if cookies else {}))
    sid=r.cookies.get(media.COOKIE)
    return r, f'{media.COOKIE}={sid}' if sid else cookies


def test_session_required_before_any_provider_access_and_restart(monkeypatch):
    calls=[]
    async def never(reference):
        calls.append(reference)
        raise AssertionError('provider must not be contacted')
    monkeypatch.setattr(media,'canonical',never)
    client=TestClient(app)
    for _ in range(2):
        response=client.post('/media/inspect',json=REF,headers=ORIGIN)
        assert response.status_code==409 and response.json()['error']['code']=='MEDIA_SESSION_REQUIRED'
    assert not calls
    request=Request({'type':'http','scheme':'http','path':'/media/session','headers':[]})
    session=media.session_response(request)
    payload=json.loads(session.body)
    assert payload['ready'] and payload['session_generation'] and payload['expires_at']>time.time()
    assert 'HttpOnly' in session.headers['set-cookie']
    identity=next(iter(media._clients))
    media._clients[identity]=0
    expired=client.post('/media/inspect',json=REF,headers=ORIGIN|{'Cookie':f'{media.COOKIE}={identity}'})
    assert expired.status_code==409 and not calls
    media._clients.clear()
    assert client.post('/media/inspect',json=REF,headers=ORIGIN).status_code==409


def local_path(url):return url.removeprefix('/api')


def test_preview_public_success_and_cross_user_receipt_block(monkeypatch):
    canonical(monkeypatch)
    calls=[]
    def browse(request):
        calls.append(str(request.url))
        assert 'authorization' not in request.headers
        return httpx.Response(200,content=png(),headers={'Content-Type':'application/octet-stream'})
    mock_transport(monkeypatch,browse)
    first,second=TestClient(app),TestClient(app)
    r,cookie=inspect(first);p=r.json()['preview']
    assert p['status']=='available' and p['access_verified'] and p['source_asset']=='browse'
    assert time.time() < p['receipt_expires_at'] <= time.time()+media.TTL
    assert DATA not in r.text and BROWSE not in r.text
    assert calls==[BROWSE]
    own=first.get(local_path(p['url']),headers={'Cookie':cookie})
    assert own.status_code==200 and own.content==png() and own.headers['content-type']=='image/png'
    assert second.get(local_path(p['url'])).status_code==404
    image=first.get(local_path(p['download_url']),headers={'Cookie':cookie})
    assert 'attachment' in image.headers['content-disposition']
    media._tickets[p['url'].rsplit('/',1)[-1]].expires=0
    assert first.get(local_path(p['url']),headers={'Cookie':cookie}).status_code==404


@pytest.mark.parametrize('assets,expected',[
 ({},'missing_asset'),({'visual':{'type':'image/tiff','roles':['visual'],'href':BROWSE}},'unsupported_format'),
 ({'browse':{'type':'image/png','roles':['thumbnail'],'href':BROWSE,'storage:requester_pays':True}},'requester_pays')])
def test_missing_unsupported_requester_pays_distinct(monkeypatch,assets,expected):
    value=raw();value['assets']=assets;canonical(monkeypatch,value)
    r,_=inspect(TestClient(app));assert r.json()['preview']['status']==expected


@pytest.mark.parametrize('code,expected',[(401,'unauthorized'),(403,'permission_required'),(404,'not_found')])
def test_http_failures_not_reported_as_missing(monkeypatch,code,expected):
    canonical(monkeypatch);mock_transport(monkeypatch,lambda r:httpx.Response(code,json={'error':'TEST_ONLY'}))
    response,_=inspect(TestClient(app))
    assert response.json()['preview']['status']==expected


@pytest.mark.parametrize('code', ['eula_required','application_authorization_required'])
def test_explicit_permission_reason_only_when_provider_reports_it(monkeypatch,code):
    canonical(monkeypatch);mock_transport(monkeypatch,lambda r:httpx.Response(403,json={'error':code}))
    response,_=inspect(TestClient(app));assert response.json()['preview']['status']==code


def test_login_and_authentication_are_separate_from_original_access(monkeypatch):
    canonical(monkeypatch)
    r,_=inspect(TestClient(app),{'include_preview':False,'asset_keys':['granule']})
    assert r.json()['assets'][0]['status']=='earthdata_not_configured'
    configured(monkeypatch)
    r,_=inspect(TestClient(app),{'include_preview':False,'asset_keys':['granule']})
    assert r.json()['assets'][0]['status']=='login_required'


def test_authenticated_original_probe_and_complete_receive_owner_binding(monkeypatch):
    configured(monkeypatch);canonical(monkeypatch)
    auth._sessions['TEST_ONLY_SESSION_A']=auth.Session(auth.Grant('TEST_ONLY_ACCESS_A',900),time.monotonic()+900,time.monotonic()+3600)
    requests=[];file=b'\x89HDF\r\n\x1a\n'+b'TEST_ONLY_DATA'*100
    def handler(request):
        requests.append(request)
        assert request.headers.get('authorization')=='Bearer TEST_ONLY_ACCESS_A'
        return httpx.Response(200,content=file,headers={'Content-Type':'application/octet-stream'})
    mock_transport(monkeypatch,handler)
    first=TestClient(app)
    r,cookie=inspect(first,{'include_preview':False,'asset_keys':['granule']},f'{auth.SESSION_COOKIE}=TEST_ONLY_SESSION_A')
    asset=r.json()['assets'][0];assert asset['status']=='available' and asset['download_completed'] is False
    cookie+='; '+auth.SESSION_COOKIE+'=TEST_ONLY_SESSION_A'
    assert first.get(local_path(asset['download_url'])).status_code==404
    received=first.get(local_path(asset['download_url']),headers={'Cookie':cookie})
    assert received.status_code==200 and received.content==file
    assert first.get(local_path(asset['download_url'])+'/status',headers={'Cookie':cookie}).json()['download_completed']
    assert first.get(local_path(asset['download_url']),headers={'Cookie':cookie.replace('SESSION_A','SESSION_B')}).status_code==404
    assert all(str(req.url)==DATA for req in requests)
    assert media._active==0


@pytest.mark.parametrize('destination,expected',[
 ('https://example.test/file.png','blocked_destination'),
 ('http://127.0.0.1/file.png','blocked_destination'),
 ('https://user:TEST_ONLY@data.lpdaac.earthdatacloud.nasa.gov/file.png','blocked_destination'),
 ('https://urs.earthdata.nasa.gov/oauth/authorize','login_required'),
 (BROWSE.replace('TEST_ONLY.png','OTHER_SCENE.png'),'redirect_item_mismatch')])
def test_redirect_allowlist_and_identity(monkeypatch,destination,expected):
    mock_transport(monkeypatch,lambda r:httpx.Response(302,headers={'Location':destination}))
    with pytest.raises(transfer.TransferError) as e:
        asyncio.run(transfer.read(BROWSE,max_bytes=1000,expected_name='TEST_ONLY.png'))
    assert e.value.code==expected


def test_cross_host_redirect_strips_auth_header_and_never_returns_signed_url(monkeypatch):
    redirected='https://d1nklfio7vscoe.cloudfront.net/s3-TEST_ONLY/lp-prod-protected.s3.us-west-2.amazonaws.com/VNP09GA.002/TEST_ONLY/TEST_ONLY.h5?Signature=TEST_ONLY'
    calls=[]
    def handler(req):
        calls.append(req)
        return httpx.Response(302,headers={'Location':redirected}) if len(calls)==1 else httpx.Response(200,content=b'TEST_ONLY')
    mock_transport(monkeypatch,handler)
    p=asyncio.run(transfer.read(DATA,max_bytes=1000,token='TEST_ONLY_ACCESS',expected_name='TEST_ONLY.h5'))
    assert p.file.read()==b'TEST_ONLY';p.close()
    assert calls[0].headers['authorization']=='Bearer TEST_ONLY_ACCESS'
    assert 'authorization' not in calls[1].headers and not hasattr(p,'url')


def test_large_file_and_unknown_length_overflow(monkeypatch):
    mock_transport(monkeypatch,lambda r:httpx.Response(200,content=b'0123456789'))
    with pytest.raises(transfer.TransferError) as e:asyncio.run(transfer.read(BROWSE,max_bytes=5))
    assert e.value.code=='size_limit'
    mock_transport(monkeypatch,lambda r:httpx.Response(206,content=b'x',headers={'Content-Range':'bytes 0-0/9999999999'}))
    with pytest.raises(transfer.TransferError) as e:asyncio.run(transfer.read(BROWSE,max_bytes=100,probe=True))
    assert e.value.code=='size_limit'


def test_grouped_quota_rejection_does_not_consume_other_budget(monkeypatch):
    monkeypatch.setattr(media, '_usage', {})
    media.charge('TEST_ONLY_GLOBAL', 90, limit=100)
    media.charge('TEST_ONLY_OWNER', 10, limit=100)
    before = dict(media._usage)
    with pytest.raises(transfer.TransferError) as error:
        media.charge_many(('TEST_ONLY_OWNER', 'TEST_ONLY_GLOBAL'), 20, limit=100)
    assert error.value.code == 'quota_limit'
    assert media._usage == before
    media.charge_many(('TEST_ONLY_OWNER', 'TEST_ONLY_GLOBAL'), 10, limit=100)
    assert media._usage['TEST_ONLY_OWNER'][1] == 20
    assert media._usage['TEST_ONLY_GLOBAL'][1] == 100


def test_grouped_quota_blocks_concurrent_over_admission(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    monkeypatch.setattr(media, '_usage', {})
    def reserve(index):
        try:
            media.charge_many((f'TEST_ONLY_OWNER_{index}', 'TEST_ONLY_GLOBAL'), 60, limit=100)
            return True
        except transfer.TransferError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(reserve, range(2))) == 1
    assert media._usage['TEST_ONLY_GLOBAL'][1] == 60
    assert len(media._usage) == 2


def test_global_concurrency_and_hourly_quota(monkeypatch):
    media._active=2
    r,_=inspect(TestClient(app));assert r.status_code==429
    media._active=0;media.charge('TEST_ONLY',media.HOURLY_BYTES)
    with pytest.raises(transfer.TransferError) as e:media.charge('TEST_ONLY',1)
    assert e.value.code=='quota_limit'


def test_refresh_race_atomic_rotation_and_refusal(monkeypatch):
    configured(monkeypatch)
    req=Request({'type':'http','headers':[(b'cookie',f'{auth.SESSION_COOKIE}=TEST_ONLY_A'.encode())]})
    calls=[]
    async def refresh(config,token):
        calls.append(token);await asyncio.sleep(.01)
        return auth.Grant('TEST_ONLY_NEW_ACCESS',900,'TEST_ONLY_NEW_REFRESH')
    monkeypatch.setattr(auth,'exchange_refresh',refresh)
    async def run():
        auth._sessions['TEST_ONLY_A']=auth.Session(auth.Grant('TEST_ONLY_OLD',900,'TEST_ONLY_REFRESH'),0,time.monotonic()+3600)
        result=await asyncio.gather(auth.access_token(req),auth.access_token(req),auth.access_token(req))
        assert result==['TEST_ONLY_NEW_ACCESS']*3 and calls==['TEST_ONLY_REFRESH']
        assert auth._sessions['TEST_ONLY_A'].grant.refresh_token=='TEST_ONLY_NEW_REFRESH'
        assert 'TEST_ONLY_NEW' not in auth.status(req).body.decode()
        async def denied(*args):raise ValueError('TEST_ONLY_SECRET_NOT_EXPOSED')
        monkeypatch.setattr(auth,'exchange_refresh',denied)
        auth._sessions['TEST_ONLY_A'].expires_at=0
        with pytest.raises(auth.AuthenticationRequired):await auth.access_token(req)
        assert auth.status(req).body and json.loads(auth.status(req).body)['reauthorization_required']
        with pytest.raises(auth.AuthenticationRequired):await auth.access_token(req)
    asyncio.run(run())


def test_oauth_refresh_transport_schema_and_no_user_token_api(monkeypatch):
    configured(monkeypatch);calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'access_token':'TEST_ONLY_NEW','refresh_token':'TEST_ONLY_ROTATED','expires_in':900,'token_type':'Bearer'})
    mock_transport(monkeypatch,handler)
    grant=asyncio.run(auth.exchange_refresh(auth.settings(),'TEST_ONLY_REFRESH'))
    assert grant.refresh_token=='TEST_ONLY_ROTATED' and len(calls)==1
    assert calls[0].url.path=='/oauth/token' and b'grant_type=refresh_token' in calls[0].content
    assert '/api/users/renew_token' not in str(calls[0].url)
    with pytest.raises(ValueError):auth.parse_grant({'access_token':'TEST_ONLY'})


def test_nonlocal_oauth_memory_sessions_disabled(monkeypatch):
    configured(monkeypatch);monkeypatch.setenv('EARTHDATA_REDIRECT_URI','https://example.org/api/auth/earthdata/callback')
    assert auth.settings() is None


def test_exact_landsat_mapping_rejects_different_processing_product(monkeypatch):
    original=copy.deepcopy(SYNTHETIC)
    product='LC09_L2SP_116035_20250723_20250726_02_T1'
    original.update(id='LC09_L2SP_116035_20250723_02_T1',collection='landsat-c2-l2')
    original['properties']={'platform':'landsat-9','datetime':'2025-07-23T02:00:00Z','landsat:scene_id':'TEST_ONLY_SCENE','landsat:collection_number':'02','landsat:correction':'L2SP'}
    original['assets']={'thumbnail':{'href':'s3://usgs-landsat/'+product+'/'+product+'_thumb_small.jpeg'}}
    usgs={'id':product+'_ST','collection':'landsat-c2l2-st','properties':original['properties']|{'platform':'LANDSAT_9'}}
    assert landsat.product_id(original)==product
    assert landsat.matching(original,usgs,product,'ST')
    for mutation in [{'platform':'LANDSAT_8'},{'landsat:correction':'L2SR'},{'datetime':'2025-07-24T02:00:00Z'},{'landsat:collection_number':'01'}]:
        other=copy.deepcopy(usgs);other['properties'].update(mutation)
        assert not landsat.matching(original,other,product,'ST')
    other=copy.deepcopy(usgs);other['id']=product.replace('20250726','20250727')+'_ST'
    assert not landsat.matching(original,other,product,'ST')


def test_dns_private_address_and_oauth_code_logs_blocked(monkeypatch):
    monkeypatch.setattr(transfer.socket,'getaddrinfo',lambda *a,**kw:[(2,1,6,'',('127.0.0.1',443))])
    with pytest.raises(transfer.TransferError) as e:asyncio.run(REAL_PUBLIC_DNS('data.lpdaac.earthdatacloud.nasa.gov'))
    assert e.value.code=='blocked_destination'
    for target in ['/auth/earthdata/callback?code=TEST_ONLY_CODE&state=TEST_ONLY_STATE','/media/downloads/TEST_ONLY_RECEIPT']:
        record=logging.LogRecord('uvicorn.access',20,'test',1,'%s - "%s %s HTTP/%s" %d',('test','GET',target,'1.1',200),None)
        assert AccessFilter().filter(record)
        assert 'TEST_ONLY' not in record.getMessage()


def test_request_rejects_caller_url_and_bad_origin():
    client=TestClient(app)
    assert client.post('/media/inspect',json=REF|{'url':'https://example.test/'},headers=ORIGIN).status_code==422
    assert client.post('/media/inspect',json=REF,headers={'Origin':'https://example.test'}).status_code==403


def test_timeout_and_full_body_incomplete_are_failures(monkeypatch):
    async def slow(request):await asyncio.sleep(.1);return httpx.Response(200,content=b'TEST_ONLY')
    mock_transport(monkeypatch,slow);monkeypatch.setattr(transfer,'TOTAL_SECONDS',.005)
    with pytest.raises(transfer.TransferError) as e:asyncio.run(transfer.read(BROWSE,max_bytes=100))
    assert e.value.code=='timeout'
    monkeypatch.setattr(transfer,'TOTAL_SECONDS',5)
    mock_transport(monkeypatch,lambda r:httpx.Response(206,content=b'TEST_ONLY',headers={'Content-Range':'bytes 0-8/900'}))
    with pytest.raises(transfer.TransferError) as e:asyncio.run(transfer.read(BROWSE,max_bytes=1000))
    assert e.value.code=='incomplete_transfer'


def test_expired_without_refresh_and_logout_during_refresh(monkeypatch):
    configured(monkeypatch)
    req=Request({'type':'http','headers':[(b'cookie',f'{auth.SESSION_COOKIE}=TEST_ONLY_A'.encode())]})
    async def run():
        auth._sessions['TEST_ONLY_A']=auth.Session(auth.Grant('TEST_ONLY',900),0,time.monotonic()+3600)
        with pytest.raises(auth.AuthenticationRequired):await auth.access_token(req)
        assert json.loads(auth.status(req).body)['reauthorization_required']
        auth._sessions['TEST_ONLY_A']=auth.Session(auth.Grant('TEST_ONLY',900,'TEST_ONLY_REFRESH'),0,time.monotonic()+3600)
        async def refresh(*args):
            auth._sessions.pop('TEST_ONLY_A',None)
            return auth.Grant('TEST_ONLY_ROTATED',900,'TEST_ONLY_ROTATED_REFRESH')
        monkeypatch.setattr(auth,'exchange_refresh',refresh)
        with pytest.raises(auth.AuthenticationRequired):await auth.access_token(req)
        assert 'TEST_ONLY_A' not in auth._sessions
    asyncio.run(run())


def test_http_200_error_json_is_not_an_original_file():
    payload=transfer.Payload(BytesIO(b'{"error":"TEST_ONLY"}'),21,'application/json',True,200)
    for mime in ('image/tiff','application/x-hdf5'):
        with pytest.raises(transfer.TransferError) as e:media.original_header(payload,{'type':mime})
        assert e.value.code=='invalid_file'
    payload.close()
