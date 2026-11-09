"""TEST ONLY public PC/USGS transfers; no credentials or live provider requests."""
import copy
import base64
import json
from datetime import datetime,timezone,timedelta
from urllib.parse import urlsplit
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import media_access as m,landsat_access as l,provider_transfer as t,planetary,operator_preview_cache as cache
from test_media_access import png,REAL_ASYNC_CLIENT

PID='LC09_L2SP_001001_20250101_20250103_02_T1'
REF={'provider_id':'earth-search','collection':'landsat-c2-l2','id':'LC09_L2SP_001001_20250101_02_T1'}


def samples():
    props={'platform':'landsat-9','datetime':'2025-01-01T02:00:00Z','landsat:scene_id':'TEST_ONLY_SCENE','landsat:correction':'L2SP','landsat:collection_number':'02'}
    raw={'id':REF['id'],'collection':'landsat-c2-l2','properties':props,'assets':{
      'thumbnail':{'href':f's3://usgs-landsat/{PID}/{PID}_thumb_small.jpeg','type':'image/jpeg','roles':['thumbnail'],'storage:requester_pays':True},
      'lwir11':{'href':f's3://usgs-landsat/{PID}/{PID}_ST_B10.TIF','type':'image/tiff','storage:requester_pays':True}}}
    usgs={'id':PID+'_ST','collection':'landsat-c2l2-st','properties':dict(props),'assets':{k:{**a,'href':f'https://landsatlook.usgs.gov/data/collection02/{PID}/'+a['href'].rsplit('/',1)[-1],'storage:requester_pays':False} for k,a in raw['assets'].items()}}
    pc={'id':REF['id'],'collection':'landsat-c2-l2','properties':dict(props),'assets':{
      'lwir11':{'href':f'https://landsateuwest.blob.core.windows.net/landsat-c2/{PID}/{PID}_ST_B10.TIF','type':'image/tiff'},
      'rendered_preview':{'href':'https://planetarycomputer.microsoft.com/api/data/v1/item/preview.png?collection=landsat-c2-l2&item='+REF['id'],'type':'image/png','roles':['overview']}}}
    return raw,usgs,pc


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    for provider in ('USGS','NASA','CDSE'):monkeypatch.setenv('OPERATOR_'+provider+'_ENABLED','0')
    monkeypatch.setenv('OPERATOR_ACCESS_ENABLED','0')
    m._clients.clear();m._tickets.clear();m._usage.clear();m._active=0
    cache.cache.clear();cache.pending.clear();planetary.tokens.clear();planetary.locks.clear()
    async def dns(host):pass
    monkeypatch.setattr(t,'public_dns',dns)


def configure(monkeypatch,mutation=None,status=200,missing=False,blob=False):
    raw,usgs,pc=samples();calls=[]
    if mutation:mutation(pc)
    if missing:pc['assets'].pop('rendered_preview')
    if blob:pc['assets']['rendered_preview']['href']=f'https://landsateuwest.blob.core.windows.net/landsat-c2/{PID}/{PID}_preview.png'
    async def canonical(ref):assert ref==REF;return copy.deepcopy(raw)
    async def metadata(url):
        if urlsplit(url).hostname=='landsatlook.usgs.gov':return copy.deepcopy(usgs)
        assert urlsplit(url).hostname=='planetarycomputer.microsoft.com'
        return copy.deepcopy(pc)
    def transfer(req):
        calls.append((req.url.host,req.headers.get('authorization'),req.headers.get('range')))
        if req.url.host=='landsatlook.usgs.gov':return httpx.Response(302,headers={'Location':'https://ers.cr.usgs.gov/login?return=TEST_ONLY'})
        return httpx.Response(status,content=png() if status==200 else b'TEST ONLY provider failure',headers={'Content-Type':'image/png' if status==200 else 'text/plain'})
    monkeypatch.setattr(m,'canonical',canonical);monkeypatch.setattr(l,'read_json',metadata)
    monkeypatch.setattr(t.httpx,'AsyncClient',lambda **kwargs:REAL_ASYNC_CLIENT(transport=httpx.MockTransport(transfer),**kwargs))
    return raw,pc,calls,transfer


def inspect(client,assets=None):
    sid=client.get('/media/session').cookies.get(m.COOKIE)
    headers={'Origin':'http://127.0.0.1:3000','Cookie':m.COOKIE+'='+sid}
    r=client.post('/media/inspect',json=REF|{'asset_keys':assets or [],'include_preview':True},headers=headers)
    return r.json(),headers


def test_exact_public_preview_keeps_reference_and_original_login_required(monkeypatch):
    _,_,calls,_=configure(monkeypatch);client=TestClient(app);d,headers=inspect(client,['lwir11'])
    assert d['reference']==REF and d['preview']['status']=='available'
    p=d['preview'];assert p['source_provider_id']=='planetary-computer' and p['product_match']['product_id']==PID
    assert p['original_access']['status']=='usgs_login_required' and p['original_access']['http_status']==302
    assert p['original_access']['redirect_host']=='ers.cr.usgs.gov'
    assert d['assets'][0]['status']=='usgs_login_required' and not d['assets'][0].get('download_url')
    image=client.get(p['url'][4:],headers=headers);assert image.content==png() and image.headers['content-type']=='image/png'
    assert client.get(p['url'][4:].replace('/previews/','/downloads/'),headers=headers).status_code==404
    assert TestClient(app).get(p['url'][4:]).status_code==404
    assert all(auth is None for _,auth,_ in calls)
    assert 'sig=' not in json.dumps(d) and 'return=TEST_ONLY' not in json.dumps(d)


@pytest.mark.parametrize('mutate',[
 lambda p:p['properties'].update(platform='landsat-8'),
 lambda p:p['properties'].update(datetime='2025-01-01T02:00:00.001Z'),
 lambda p:p['properties'].update(datetime='2025-01-01T02:00:00'),
 lambda p:p['properties'].update({'landsat:collection_number':'01'}),
 lambda p:p['properties'].update({'landsat:correction':'L2SR'}),
 lambda p:p['properties'].update({'landsat:scene_id':'OTHER_TEST_ONLY_SCENE'}),
 lambda p:p['assets']['lwir11'].update(href=p['assets']['lwir11']['href'].replace('20250103','20250104')),
 lambda p:p.update(id='LC09_L2SP_001002_20250101_02_T1'),
])
def test_exact_product_mismatches_never_use_pc_image(monkeypatch,mutate):
    _,_,calls,_=configure(monkeypatch,mutate);d,_=inspect(TestClient(app))
    assert d['preview']['status']=='usgs_login_required'
    assert d['preview']['alternate_preview']['status']=='product_mismatch'
    assert not any(host=='planetarycomputer.microsoft.com' for host,_,_ in calls)


@pytest.mark.parametrize('status',[401,403,404,429,503])
def test_partial_pc_outage_retains_actual_usgs_failure_and_original_assets(monkeypatch,status):
    configure(monkeypatch,status=status);d,_=inspect(TestClient(app),['lwir11'])
    assert d['preview']['status']=='usgs_login_required' and d['preview']['alternate_preview']['http_status']==status
    assert d['assets'][0]['status']=='usgs_login_required' and not d['preview'].get('url')


def test_missing_pc_preview_is_not_an_image_or_source_replacement(monkeypatch):
    configure(monkeypatch,missing=True);d,_=inspect(TestClient(app))
    assert d['preview']['alternate_preview']['status']=='missing_asset'
    assert d['reference']==REF and not d['preview'].get('url')


def test_missing_original_thumbnail_still_uses_exact_pc_product(monkeypatch):
    raw,_,_,_=configure(monkeypatch);raw['assets'].pop('thumbnail')
    d,_=inspect(TestClient(app));assert d['preview']['status']=='available'
    assert d['preview']['original_access']['status']=='missing_asset'


def test_sas_expiry_renews_once_without_exposing_signed_url(monkeypatch):
    _,_,_,base=configure(monkeypatch,blob=True);issued=[];reads=[]
    async def issue(account,container):
        issued.append(1);expiry=(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat().replace('+00:00','Z')
        return {'token':'sig=TEST_ONLY_'+str(len(issued))+'&sp=r&se='+expiry,'msft:expiry':expiry}
    def handler(req):
        if req.url.host=='landsateuwest.blob.core.windows.net':
            reads.append(1);assert 'authorization' not in req.headers
            return httpx.Response(403 if len(reads)==1 else 200,content=png())
        return base(req)
    monkeypatch.setattr(planetary,'issue',issue)
    monkeypatch.setattr(t.httpx,'AsyncClient',lambda **kwargs:REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler),**kwargs))
    d,_=inspect(TestClient(app));assert d['preview']['status']=='available' and len(issued)==2 and len(reads)==2
    assert 'sig=' not in json.dumps(d)


def test_safe_redirect_trace_records_host_without_location_query(monkeypatch):
    configure(monkeypatch);records=[]
    with t.diagnostics(records):d,_=inspect(TestClient(app))
    assert any(r['stage']=='redirect' and r['host']=='ers.cr.usgs.gov' for r in records)
    assert 'return=TEST_ONLY' not in json.dumps(records) and 'Cookie' not in json.dumps(records)


@pytest.mark.parametrize('url',['https://127.0.0.1/TEST_ONLY.png','https://planetarycomputer.microsoft.com/api/data/v1/item/preview.png?collection=landsat-c2-l2&item=OTHER_TEST_ONLY'])
def test_pc_preview_is_not_an_arbitrary_url_or_different_item_proxy(monkeypatch,url):
    _,_,calls,_=configure(monkeypatch,lambda p:p['assets']['rendered_preview'].update(href=url))
    d,_=inspect(TestClient(app));assert d['preview']['status']=='usgs_login_required'
    assert d['preview']['alternate_preview']['status']=='blocked_destination'
    assert not any(host!='landsatlook.usgs.gov' for host,_,_ in calls)


def test_html_is_not_a_successful_public_preview(monkeypatch):
    _,_,_,base=configure(monkeypatch)
    def handler(req):
        if req.url.host=='planetarycomputer.microsoft.com':return httpx.Response(200,content=b'<html>TEST ONLY login</html>',headers={'Content-Type':'text/html'})
        return base(req)
    monkeypatch.setattr(t.httpx,'AsyncClient',lambda **kwargs:REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler),**kwargs))
    d,_=inspect(TestClient(app));assert d['preview']['status']=='usgs_login_required'
    assert d['preview']['alternate_preview']['status']=='login_page' and not d['preview'].get('url')


def test_pc_metadata_not_found_preserves_original_failure(monkeypatch):
    _,usgs,_=samples();configure(monkeypatch)
    async def read(url):
        if urlsplit(url).hostname=='landsatlook.usgs.gov':return usgs
        raise t.TransferError('not_found',404)
    monkeypatch.setattr(l,'read_json',read)
    d,_=inspect(TestClient(app));assert d['preview']['status']=='usgs_login_required'
    assert d['preview']['alternate_preview']['status']=='not_found'


def test_same_short_id_and_render_url_cannot_reuse_another_processing_revision(monkeypatch):
    raw,pc,_,base=configure(monkeypatch);images=[]
    second=base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNoclu1BQAE5wIngLnp3wAAAABJRU5ErkJggg==')
    def handler(req):
        if req.url.host=='planetarycomputer.microsoft.com':
            images.append(1);return httpx.Response(200,content=png() if len(images)==1 else second)
        return base(req)
    monkeypatch.setattr(t.httpx,'AsyncClient',lambda **kwargs:REAL_ASYNC_CLIENT(transport=httpx.MockTransport(handler),**kwargs))
    client=TestClient(app);first,headers=inspect(client)
    assert client.get(first['preview']['url'][4:],headers=headers).content==png()
    for item in (raw,pc):
        for a in item['assets'].values():a['href']=a['href'].replace('20250103','20250104')
    latest,headers=inspect(client)
    assert latest['preview']['status']=='available' and '20250104' in latest['preview']['product_match']['product_id']
    assert client.get(latest['preview']['url'][4:],headers=headers).content==second and len(images)==2
