"""TEST ONLY HLS catalog/granule/file transports. Never reads real credentials."""
import asyncio
import copy
from contextlib import asynccontextmanager
import json
from io import BytesIO
from urllib.parse import parse_qs,urlsplit
import httpx
import numpy as np
import pytest
import rasterio
from rasterio.io import MemoryFile
from fastapi.testclient import TestClient
from app.main import app
from app import cmr,hls,stac,media_access as media,provider_transfer as transfer,operator_access as op
from app.metadata import normalize
from app.purpose_plan import purpose_plan
from app.recommendations import recommend
from app.models import SearchRequest
from test_media_access import mock_transport,png,ORIGIN


def entry(family='L30',browse=True):
    collection='hls-'+family.lower()+'-002';spec=hls.COLLECTIONS[collection]
    title='HLS.'+family+'.T99ZZZ.2025204T021054.v2.0' # synthetic tile, TEST ONLY
    root='https://data.lpdaac.earthdatacloud.nasa.gov/'
    keys=['B02','B03','B04','B05','B06','B07','Fmask'] if family=='L30' else ['B02','B03','B04','B08','B8A','B11','B12','Fmask']
    links=[{'rel':'http://esipfed.org/ns/fedsearch/1.1/data#','href':root+'lp-prod-protected/'+spec['short_name']+'.020/'+title+'/'+title+'.'+key+'.tif'} for key in keys]
    if browse:links.append({'rel':'http://esipfed.org/ns/fedsearch/1.1/browse#','href':root+'lp-prod-public/'+spec['short_name']+'.020/'+title+'/'+title+'.jpg'})
    return {'id':'G_TEST_ONLY_'+family+'-LPCLOUD','collection_concept_id':spec['concept'],'title':title,
        'time_start':'2025-07-23T02:10:54Z','time_end':'2025-07-23T02:11:18Z','cloud_cover':'42',
        'polygons':[['36 126 36 127 37 127 37 126 36 126']],'links':links}


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.delenv('OPERATOR_ACCESS_ENABLED',raising=False)
    media._tickets.clear();media._clients.clear();media._usage.clear();media._active=0
    async def dns(host):pass
    monkeypatch.setattr(transfer,'public_dns',dns)


@pytest.mark.parametrize('family,nir,swir',[('L30','B05','B06'),('S30','B8A','B11')])
def test_normalize_and_real_band_selection(family,nir,swir):
    raw=cmr.granule(entry(family));scene=normalize(raw)
    assert scene['platform'] is None and scene['resolution_m']==[30.0]
    assert scene['scene_cloud_cover']==42 and scene['hls']['version']=='2.0'
    assert scene['support']['processing'].endswith('픽셀 처리 미지원')
    assert scene['remote_collection']==hls.COLLECTIONS[scene['collection']]['concept']
    veg=purpose_plan(scene,'vegetation');flood=purpose_plan(scene,'flood')
    assert veg['product_status']=='met' and set(veg['analysis_keys'])=={'B04',nir,'Fmask'}
    assert set(flood['analysis_keys'])=={'B03',swir,'Fmask'}
    assert all(a['direct_url'] is None and a['authentication_required'] for a in scene['download_assets'])
    assert purpose_plan(scene,'thermal')['missing_bands']==['thermal']
    ids={c['id'] for c in recommend('', 'thermal')['cards']}
    assert not ids & {'hls_l30','hls_s30'}


def test_missing_fields_no_invention_and_exact_asset_match():
    e=entry(browse=False);e.pop('cloud_cover');e['links'] += [
       {'rel':'http://esipfed.org/ns/fedsearch/1.1/browse#','href':'https://evil.test/image.jpg'},
       {'rel':'http://esipfed.org/ns/fedsearch/1.1/data#','href':entry()['links'][0]['href'].replace('.020/','.999/')},
       {'rel':'http://esipfed.org/ns/fedsearch/1.1/data#','href':entry()['links'][0]['href']+'?token=TEST_ONLY'}]
    scene=normalize(cmr.granule(e));assert scene['scene_cloud_cover'] is None
    assert scene['preview_diagnostic']['status']=='missing_asset'
    assert len(scene['download_assets'])==7
    with pytest.raises(ValueError):cmr.granule(e,'hls-s30-002')
    e['title']=e['title'].replace('v2.0','v1.5')
    with pytest.raises(ValueError):cmr.granule(e)


def test_cmr_paging_collection_isolation_and_duplicates(monkeypatch):
    async def run():
        calls=[]
        def transport(r):
            p=parse_qs(r.url.query.decode());calls.append(p)
            family='L30' if p['collection_concept_id']==[hls.COLLECTIONS['hls-l30-002']['concept']] else 'S30'
            return httpx.Response(200,json={'feed':{'entry':[entry(family),entry(family)]}},headers={'CMR-Hits':'26'})
        q=SearchRequest(bbox=[126.7,36.4,126.71,36.41],start_date='2025-07-20',end_date='2025-07-26')
        async with httpx.AsyncClient(transport=httpx.MockTransport(transport)) as client:
            for collection in hls.COLLECTIONS:
                first=cmr.initial(q,collection);page=await cmr.request_page(client,first,2)
                assert all(i['collection']==collection for i in page['features'])
                next_page=await cmr.request_page(client,{'url':page['links'][0]['href']},2)
                assert calls[-1]['page_num']==['2'] and calls[-1]['bounding_box']==['126.7,36.4,126.71,36.41']
    asyncio.run(run())


def test_hls_partial_failure_preserves_other_provider_and_period(monkeypatch):
    async def nasa(client,request,seconds):
        if hls.COLLECTIONS['hls-s30-002']['concept'] in request['url']:raise httpx.ReadTimeout('TEST ONLY')
        old=entry();old['id']='G_TEST_OLD-LPCLOUD';old['time_start']='2024-01-01T00:00:00Z'
        return {'features':[cmr.granule(entry()),cmr.granule(entry()),cmr.granule(old)],'links':[]}
    monkeypatch.setattr(cmr,'request_page',nasa)
    r=TestClient(app).post('/search',json={'purpose_type':'vegetation','bbox':[126.7,36.4,126.71,36.41],
      'start_date':'2025-07-20','end_date':'2025-07-26','collections':list(hls.COLLECTIONS),'max_items':25})
    assert r.status_code==200;r=r.json();assert len(r['items'])==1 and r['outcome']=='partial'
    states={s['collection']:s for s in r['collection_statuses']}
    assert states['hls-l30-002']['duplicates']==1 and states['hls-l30-002']['filtered']==1
    assert states['hls-s30-002']['reason']=='timeout'


def test_canonical_hls_checks_requested_collection(monkeypatch):
    async def fake(url):return {'feed':{'entry':[entry('S30')]}}
    monkeypatch.setattr(transfer,'read_json',fake)
    ref={'provider_id':'nasa-cmr','collection':'hls-l30-002','id':entry('S30')['id']}
    with pytest.raises(ValueError):asyncio.run(media.canonical(ref))


def tiff():
    with MemoryFile() as mem:
        with mem.open(driver='GTiff',width=2,height=2,count=1,dtype='int16',crs='EPSG:32652',transform=rasterio.transform.from_origin(300000,4000000,30,30)) as f:
            f.write(np.array([[100,200],[300,-9999]],dtype='int16'),1)
        return mem.read()


def test_hls_public_preview_and_server_original_full_download(monkeypatch):
    raw=cmr.granule(entry());ref={'provider_id':'nasa-cmr','collection':raw['collection'],'id':raw['id']}
    async def canonical(r):assert r==ref;return copy.deepcopy(raw)
    async def access(request,**kw):return 'TEST_ONLY_NOT_REAL'
    monkeypatch.setattr(media,'canonical',canonical);monkeypatch.setattr(media.auth,'access_token',access)
    content=tiff();calls=[]
    def handler(r):
        calls.append(r)
        if r.url.path.endswith('.jpg'):
            assert 'authorization' not in r.headers
            return httpx.Response(200,content=png(),headers={'content-type':'image/png'})
        assert r.headers.get('authorization')=='Bearer TEST_ONLY_NOT_REAL'
        return httpx.Response(206 if 'range' in r.headers else 200,content=content,
            headers={'content-type':'image/tiff','content-length':str(len(content)),'content-range':f'bytes 0-{len(content)-1}/{len(content)}'})
    mock_transport(monkeypatch,handler)
    client=TestClient(app);session=client.get('/media/session');cookies={media.COOKIE:session.cookies[media.COOKIE]}
    r=client.post('/media/inspect',json=ref|{'asset_keys':['B04'],'include_preview':True},headers=ORIGIN,cookies=cookies)
    d=r.json();assert d['preview']['status']=='available' and d['assets'][0]['status']=='available'
    assert not d['assets'][0]['download_completed'] and d['assets'][0]['size_bytes']==len(content)
    file=client.get(d['assets'][0]['download_url'].replace('/api','',1),headers=ORIGIN,cookies=cookies)
    assert file.status_code==200 and file.content==content
    with MemoryFile(file.content) as m,m.open() as f:assert f.read(1)[0,0]==100 and f.driver=='GTiff'
    assert 'TEST_ONLY_NOT_REAL' not in r.text and all('token=' not in str(c.url) for c in calls)


@pytest.mark.parametrize('code,body,expected',[(401,b'', 'unauthorized'),(403,b'','permission_required'),(404,b'','not_found'),(200,b'<html>denied</html>','login_page')])
def test_hls_error_html_and_auth_not_success(monkeypatch,code,body,expected):
    mock_transport(monkeypatch,lambda r:httpx.Response(code,content=body or b'TEST ONLY',headers={'content-type':'text/html' if code==200 else 'text/plain'}))
    url=entry()['links'][0]['href']
    with pytest.raises(transfer.TransferError,match=expected):asyncio.run(transfer.read(url,max_bytes=10000))


def test_hls_operator_requires_product_review_before_seed_or_credential(monkeypatch):
    ref={'provider_id':'nasa-cmr','collection':'hls-l30-002','id':'G_TEST-LPCLOUD'}
    monkeypatch.delenv('OPERATOR_NASA_COLLECTIONS',raising=False)
    with pytest.raises(transfer.TransferError,match='operator_product_not_enabled'):op.require_product(ref)
    monkeypatch.setenv('OPERATOR_NASA_COLLECTIONS','hls-l30-002,hls-s30-002')
    monkeypatch.delenv('OPERATOR_NASA_HLS_REDISTRIBUTION_REVIEWED',raising=False)
    with pytest.raises(transfer.TransferError,match='operator_policy_not_reviewed'):op.require_product(ref)
    monkeypatch.setenv('OPERATOR_NASA_HLS_REDISTRIBUTION_REVIEWED','1');op.require_product(ref)
    with pytest.raises(transfer.TransferError,match='operator_product_not_enabled'):
        op.require_product(ref|{'collection':'viirs-vnp09ga-002'})


def test_hls_crosshost_auth_header_stripped_and_size_limit(monkeypatch):
    calls=[];first=entry()['links'][0]['href'];name=first.rsplit('/',1)[1]
    def handler(r):
        calls.append(r)
        if len(calls)==1:return httpx.Response(302,headers={'location':'https://d1nklfio7vscoe.cloudfront.net/s3-protected/lp-prod-protected.s3.us-west-2.amazonaws.com/HLSL30.020/'+entry()['title']+'/'+name})
        assert 'authorization' not in r.headers
        return httpx.Response(200,content=b'TEST',headers={'content-length':'99999'})
    mock_transport(monkeypatch,handler)
    with pytest.raises(transfer.TransferError,match='size_limit'):
        asyncio.run(transfer.read(first,max_bytes=1000,token='TEST_ONLY',expected_name=name,provider_scope='nasa'))
    assert len(calls)==2


@pytest.mark.parametrize('expired',[False,True])
def test_hls_operator_protected_asset_and_expiry_are_separate(monkeypatch,expired):
    raw=cmr.granule(entry());ref={'provider_id':'nasa-cmr','collection':raw['collection'],'id':raw['id']}
    async def canonical(r):return copy.deepcopy(raw)
    monkeypatch.setattr(media,'canonical',canonical)
    monkeypatch.setenv('OPERATOR_ACCESS_ENABLED','1');monkeypatch.setenv('OPERATOR_NASA_ENABLED','1')
    monkeypatch.setenv('OPERATOR_NASA_COLLECTIONS','hls-l30-002')
    monkeypatch.setenv('OPERATOR_NASA_HLS_REDISTRIBUTION_REVIEWED','1')
    async def token(*args):
        if expired:raise transfer.TransferError('operator_expired')
        return 'TEST_ONLY_OPERATOR',1
    @asynccontextmanager
    async def scope(*args):yield
    class FakeStore:
        def charge(self,*args):pass
    monkeypatch.setattr(op,'token',token);monkeypatch.setattr(op,'transfer_scope',scope)
    monkeypatch.setattr(op,'current_generation',lambda *_:1);monkeypatch.setattr(op,'store',lambda:FakeStore())
    content=tiff();calls=[]
    def handler(r):
        calls.append(r);assert r.headers.get('authorization')=='Bearer TEST_ONLY_OPERATOR'
        return httpx.Response(206,content=content,headers={'content-type':'image/tiff','content-range':f'bytes 0-{len(content)-1}/{len(content)}'})
    mock_transport(monkeypatch,handler)
    client=TestClient(app);session=client.get('/media/session');cookies={media.COOKIE:session.cookies[media.COOKIE]}
    response=client.post('/media/inspect',json=ref|{'asset_keys':['B04'],'include_preview':False},headers=ORIGIN,cookies=cookies)
    row=response.json()['assets'][0]
    assert row['status']==('operator_expired' if expired else 'available')
    assert len(calls)==(0 if expired else 1)
