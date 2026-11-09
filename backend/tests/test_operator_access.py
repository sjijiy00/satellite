"""TEST ONLY operator credentials, issuers and file transport. No real tokens."""
import asyncio
import copy
import json
import multiprocessing
import subprocess
import sys
import os
import time
from contextlib import asynccontextmanager
import pytest
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app import operator_access as op,operator_adapters as adapters,operator_store as storage
from app import operator_preview_cache as cache,media_access as media,provider_transfer as transfer
from test_media_access import png,raw,REF,ORIGIN,inspect,canonical,mock_transport

FAKE='TEST_ONLY_NOT_A_REAL_TOKEN'
REAL_RESTRICT_DIRECTORY=storage.crypto._restrict_directory

@pytest.fixture(autouse=True)
def isolated(tmp_path,monkeypatch):
    for key in list(os.environ):
        if key.startswith('OPERATOR_'):monkeypatch.delenv(key)
    monkeypatch.delenv('WEB_CONCURRENCY',raising=False)
    monkeypatch.setenv('OPERATOR_ACCESS_ENABLED','1')
    monkeypatch.setenv('OPERATOR_NASA_ENABLED','1')
    monkeypatch.setenv('OPERATOR_NASA_USER_TOKEN',FAKE)
    monkeypatch.setenv('OPERATOR_NASA_TOKEN_EXPIRES_AT',str(time.time()+86400))
    monkeypatch.setenv('OPERATOR_NASA_REDISTRIBUTION_REVIEWED','1')
    monkeypatch.setattr(storage.crypto,'_restrict_directory',lambda *_:None)
    # Actual DPAPI is used; no cleartext fake store masquerades as encryption.
    monkeypatch.setattr(op,'_store',storage.Store(tmp_path/'operator.sqlite3'))
    op._locks.clear();cache.cache.clear();cache.pending.clear()
    media._tickets.clear();media._clients.clear();media._usage.clear();media._active=0
    async def dns(host):pass
    monkeypatch.setattr(transfer,'public_dns',dns)
    yield


def test_no_settings_policy_and_public_status_do_not_authenticate(monkeypatch):
    monkeypatch.delenv('OPERATOR_NASA_USER_TOKEN')
    status=TestClient(app).get('/auth/providers/status').json()['providers'][2]
    assert status['operator_mode'] and status['access_state']=='not_ready'
    assert 'OPERATOR_' not in json.dumps(status) and FAKE not in json.dumps(status)
    assert TestClient(app).get('/auth/earthdata/start').status_code==409


def test_dpapi_ciphertext_restart_revocation_and_revision_rollback(monkeypatch):
    first=asyncio.run(op.token('nasa'));assert first[0]==FAKE
    assert FAKE.encode() not in op.store().path.read_bytes()
    path=op.store().path;op._store=storage.Store(path)
    assert asyncio.run(op.token('nasa'))==first
    op.store().revoke('nasa');op._store=storage.Store(path)
    with pytest.raises(transfer.TransferError,match='operator_revoked'):asyncio.run(op.token('nasa'))
    monkeypatch.setenv('OPERATOR_NASA_REVISION','2')
    with pytest.raises(transfer.TransferError,match='reused_seed'):asyncio.run(op.token('nasa'))
    monkeypatch.setenv('OPERATOR_NASA_USER_TOKEN','TEST_ONLY_REPLACEMENT');assert asyncio.run(op.token('nasa'))[0]=='TEST_ONLY_REPLACEMENT'
    monkeypatch.setenv('OPERATOR_NASA_REVISION','1')
    with pytest.raises(transfer.TransferError,match='configuration_changed'):asyncio.run(op.token('nasa'))
    monkeypatch.setenv('OPERATOR_NASA_REVISION','3');monkeypatch.setenv('OPERATOR_NASA_USER_TOKEN',FAKE)
    with pytest.raises(transfer.TransferError,match='reused_seed'):asyncio.run(op.token('nasa'))


def test_nasa_stored_grant_restart_requires_opt_in_and_exact_revision(monkeypatch):
    first=asyncio.run(op.token('nasa'))
    path=op.store().path
    op.store().change('nasa',first[1],'active',{'access':'TEST_ONLY_ROTATED','expires':time.time()+3600})
    monkeypatch.delenv('OPERATOR_NASA_USER_TOKEN')
    monkeypatch.delenv('OPERATOR_NASA_TOKEN_EXPIRES_AT')
    op._store=storage.Store(path)
    with pytest.raises(transfer.TransferError,match='operator_not_ready'):asyncio.run(op.token('nasa'))
    monkeypatch.setenv('OPERATOR_NASA_RESUME_STORED_GRANT','1')
    assert asyncio.run(op.token('nasa'))[0]=='TEST_ONLY_ROTATED'
    assert FAKE.encode() not in path.read_bytes() and b'TEST_ONLY_ROTATED' not in path.read_bytes()
    monkeypatch.setenv('OPERATOR_NASA_REVISION','2')
    with pytest.raises(transfer.TransferError,match='operator_configuration_changed'):asyncio.run(op.token('nasa'))
    monkeypatch.setenv('OPERATOR_NASA_REVISION','1')
    op.store().revoke('nasa')
    with pytest.raises(transfer.TransferError,match='operator_revoked'):asyncio.run(op.token('nasa'))


def test_refresh_singleflight_rotated_token_is_authoritative(monkeypatch):
    monkeypatch.setenv('OPERATOR_NASA_TOKEN_EXPIRES_AT',str(time.time()+120));count=[]
    async def renew(provider,current,config):
        count.append(current['access']);await asyncio.sleep(.02)
        return {'access':'TEST_ONLY_ROTATED','expires':time.time()+3600}
    monkeypatch.setattr(adapters,'renew',renew)
    async def run():return await asyncio.gather(*(op.token('nasa') for _ in range(8)))
    result=asyncio.run(run());assert len(count)==1 and all(r[0]=='TEST_ONLY_ROTATED' for r in result)
    op._store=storage.Store(op.store().path)
    assert asyncio.run(op.token('nasa'))[0]=='TEST_ONLY_ROTATED'


@pytest.mark.parametrize('code',['operator_reconnection_required','operator_mfa_required','operator_permission_denied','operator_timeout'])
def test_denial_or_indeterminate_refresh_never_restores_seed(monkeypatch,code):
    monkeypatch.setenv('OPERATOR_NASA_TOKEN_EXPIRES_AT',str(time.time()+120));calls=[]
    async def fail(*args):calls.append(1);raise transfer.TransferError(code)
    monkeypatch.setattr(adapters,'renew',fail)
    with pytest.raises(transfer.TransferError):asyncio.run(op.token('nasa'))
    op._store=storage.Store(op.store().path)
    with pytest.raises(transfer.TransferError):asyncio.run(op.token('nasa'))
    assert calls==[1]


def test_renewal_crash_and_atomic_generation_conflict():
    values,rev,fp=op.config('nasa');s=op.store();r=s.load('nasa',rev,fp,op.seed('nasa',values))
    s.change('nasa',r['generation'],'renewing')
    with pytest.raises(transfer.TransferError,match='operator_changed'):s.change('nasa',r['generation'],'active',{})
    with pytest.raises(transfer.TransferError,match='reconnection_required'):asyncio.run(op.token('nasa'))


def test_shared_sqlite_limits_and_unsupported_multiworker(monkeypatch):
    s=op.store();other=storage.Store(s.path)
    s.enter('nasa','a');other.enter('nasa','b')
    with pytest.raises(transfer.TransferError,match='busy'):s.enter('nasa','c')
    other.leave('b');s.enter('nasa','c');s.leave('a');s.leave('c')
    s.charge('nasa',storage.LIMIT_BYTES)
    with pytest.raises(transfer.TransferError,match='quota'):other.charge('nasa',1)
    monkeypatch.setenv('WEB_CONCURRENCY','2')
    with pytest.raises(transfer.TransferError,match='multiworker'):asyncio.run(op.token('nasa'))


def test_nasa_no_visitor_oauth_public_first_and_explicit_file_receipt(monkeypatch):
    canonical(monkeypatch);calls=[]
    def handler(request):
        calls.append((request.url.path,request.headers.get('authorization')))
        if '/lp-prod-public/' in request.url.path:return httpx.Response(200,content=png(),headers={'Content-Type':'image/png'})
        if request.headers.get('authorization')!='Bearer '+FAKE:return httpx.Response(401,json={})
        return httpx.Response(200,content=b'\x89HDF\r\n\x1a\n'+b'TEST ONLY',headers={'Content-Type':'application/x-hdf5'})
    mock_transport(monkeypatch,handler);client=TestClient(app)
    response,cookie=inspect(client,{'asset_keys':['granule']});body=response.json()
    assert body['preview']['status']=='available' and body['assets'][0]['status']=='available'
    assert calls[0][1] is None and all(header is None for path,header in calls if '/lp-prod-public/' in path)
    assert FAKE not in response.text and 'refresh_token' not in response.text
    download=client.get(body['assets'][0]['download_url'].removeprefix('/api'),headers={'Cookie':cookie})
    assert download.status_code==200 and download.content.startswith(b'\x89HDF')
    assert media._tickets[body['assets'][0]['ticket']].completed
    op.store().revoke('nasa')
    assert client.get(body['assets'][0]['download_url'].removeprefix('/api'),headers={'Cookie':cookie}).status_code==409


def test_public_browse_still_works_with_missing_operator_key(monkeypatch):
    monkeypatch.delenv('OPERATOR_NASA_USER_TOKEN');canonical(monkeypatch)
    def handler(request):return httpx.Response(200,content=png(),headers={'Content-Type':'image/png'})
    mock_transport(monkeypatch,handler)
    response,_=inspect(TestClient(app),{'asset_keys':[]});assert response.json()['preview']['status']=='available'


def test_foreign_origin_urls_and_cdse_canonical_band_mapping(monkeypatch):
    client=TestClient(app);client.get('/media/session')
    assert client.post('/media/inspect',json=REF,headers={'Origin':'https://evil.test'}).status_code==403
    assert client.post('/media/inspect',json={**REF,'url':'http://127.0.0.1/private'},headers=ORIGIN).status_code==422
    root={'id':'S1_TEST_ONLY','assets':{'Product':{'href':'https://download.dataspace.copernicus.eu/odata/v1/Products(1333e31f-c63d-44d1-a99f-427435264d00)/$value','type':'application/zip'},'vv':{'href':'s3://eodata/Sentinel-1/S1_TEST_ONLY.SAFE/measurement/TEST_ONLY.tiff','type':'image/tiff'}}}
    assert '/Nodes(S1_TEST_ONLY.SAFE)/Nodes(measurement)/Nodes(TEST_ONLY.tiff)/$value' in op.cdse_asset(root,'vv')['href']
    root['assets']['vv']['href']='s3://eodata/OTHER.SAFE/measurement/TEST_ONLY.tiff'
    with pytest.raises(transfer.TransferError,match='product_mismatch'):op.cdse_asset(root,'vv')


def test_issuer_headers_rotation_and_no_redirect_credential_forwarding(monkeypatch):
    seen=[]
    def handler(request):
        seen.append(request)
        if request.url.host=='urs.earthdata.nasa.gov':
            from datetime import datetime,timezone,timedelta
            return httpx.Response(200,json={'access_token':'TEST_ONLY_NEW','expiration_date':(datetime.now(timezone.utc)+timedelta(days=60)).strftime('%m/%d/%Y')})
        if request.url.host=='identity.dataspace.copernicus.eu':return httpx.Response(200,json={'access_token':'TEST_ONLY_CDSE','refresh_token':'TEST_ONLY_REFRESH','expires_in':600})
        return httpx.Response(200,json={'errorCode':None,'data':'TEST_ONLY_M2M_SESSION'})
    mock_transport(monkeypatch,handler)
    assert asyncio.run(adapters.renew('nasa',{'access':FAKE},{}))['access']=='TEST_ONLY_NEW'
    assert asyncio.run(adapters.renew('cdse',{'refresh':'TEST_ONLY_R'},{}))['refresh']=='TEST_ONLY_REFRESH'
    assert asyncio.run(adapters.renew('usgs',{}, {'username':'TEST_ONLY_USER','application_token':FAKE}))['access']=='TEST_ONLY_M2M_SESSION'
    assert seen[0].headers['authorization']=='Bearer '+FAKE
    assert b'grant_type=refresh_token' in seen[1].content and 'authorization' not in seen[2].headers


def test_preview_cache_deduplicates_and_copies_buffers():
    from io import BytesIO
    calls=[]
    async def factory():calls.append(1);await asyncio.sleep(.01);return transfer.Payload(BytesIO(png()),len(png()),'image/png',True,200),1
    async def run():return await asyncio.gather(*(cache.read(('TEST',1),factory,media.image_bytes) for _ in range(5)))
    results=asyncio.run(run());assert len(calls)==1
    for payload,generation in results:assert payload.file.read()==png() and generation==1;payload.close()


def test_cdse_header_and_cross_provider_redirect_block(monkeypatch):
    seen=[]
    def handler(request):
        seen.append(request)
        return httpx.Response(302,headers={'Location':'https://data.lpdaac.earthdatacloud.nasa.gov/lp-prod-public/VNP09GA.002/TEST_ONLY/file.zip'})
    mock_transport(monkeypatch,handler)
    async def run():return await transfer.read('https://download.dataspace.copernicus.eu/odata/v1/Products(1333e31f-c63d-44d1-a99f-427435264d00)/$value',max_bytes=1024,token=FAKE,credential_provider='cdse',provider_scope='cdse',expected_name='file.zip')
    with pytest.raises(transfer.TransferError,match='blocked_destination'):asyncio.run(run())
    assert len(seen)==1 and seen[0].headers['authorization']=='Bearer '+FAKE


def test_cdse_sentinel1_large_product_probe_enables_receipt_without_full_download(monkeypatch):
    monkeypatch.setenv('OPERATOR_CDSE_ENABLED','1')
    monkeypatch.setenv('OPERATOR_CDSE_REDISTRIBUTION_REVIEWED','1')
    reference={'provider_id':'copernicus','collection':'sentinel-1-grd','id':'S1_TEST_ONLY'}
    product='https://download.dataspace.copernicus.eu/odata/v1/Products(1333e31f-c63d-44d1-a99f-427435264d00)/$value'
    raw_item={'id':reference['id'],'collection':reference['collection'],'assets':{'Product':{'href':product,'type':'application/zip'}}}
    async def item(_):return raw_item
    async def token(*_):return FAKE,1
    @asynccontextmanager
    async def scope(*_):yield
    monkeypatch.setattr(media,'canonical',item)
    monkeypatch.setattr(op,'token',token)
    monkeypatch.setattr(op,'current_generation',lambda *_:1)
    monkeypatch.setattr(op,'transfer_scope',scope)
    monkeypatch.setattr(op,'store',lambda: type('StoreStub',(),{'charge':lambda *args:None})())
    seen=[]
    def handler(request):
        seen.append(request)
        if 'authorization' not in request.headers:return httpx.Response(401)
        assert request.headers['authorization']=='Bearer '+FAKE
        assert request.headers['range']=='bytes=0-1023'
        body=b'PK\x03\x04'+bytes(1020)
        return httpx.Response(206,content=body,headers={'Content-Range':'bytes 0-1023/1177053605','Content-Length':'1024','Content-Type':'application/octet-stream'})
    mock_transport(monkeypatch,handler)
    client=TestClient(app)
    session=client.get('/media/session')
    response=client.post('/media/inspect',json=reference|{'asset_keys':['Product'],'include_preview':False},headers=ORIGIN|{'Cookie':f'{media.COOKIE}={session.cookies.get(media.COOKIE)}'})
    assert response.status_code==200
    asset=response.json()['assets'][0]
    assert asset['status']=='available' and asset['size_bytes']==1177053605 and asset['download_url'].startswith('/api/media/downloads/')
    assert not asset['download_completed'] and len(seen)==2


def test_usgs_exact_secondary_file_and_no_bearer_on_file_host(monkeypatch):
    from test_core import SYNTHETIC
    from app import landsat_access as landsat
    product='LC09_L2SP_116035_20250723_20250726_02_T1';filename=product+'_SR_B4.TIF';calls=[]
    raw={'assets':{'red':{'href':'s3://TEST_ONLY/'+product+'/'+filename}}}
    async def fake(method,body,token):
        calls.append((method,body,token))
        if method=='scene-metadata':return {'displayId':product,'entityId':'TEST_ONLY_SCENE'}
        if method=='download-options':return [{'secondaryDownloads':[{'displayId':filename[:-4],'entityId':'TEST_ONLY_FILE','id':'TEST_ONLY_PRODUCT','available':True}]}]
        if method=='download-request':return {'availableDownloads':[{'url':'https://landsatlook.usgs.gov/data/collection02/'+filename+'?signature=TEST_ONLY'}]}
        return None
    monkeypatch.setattr(adapters,'m2m',fake)
    asset=asyncio.run(adapters.usgs_file(raw,raw['assets']['red'],FAKE))
    assert asset['filename']==filename and [c[0] for c in calls]==['scene-metadata','download-options','download-request']
    assert calls[0][1]['entityId']==product and calls[0][1]['idType']=='displayId'
    assert calls[2][1]['downloads']==[{'entityId':'TEST_ONLY_FILE','productId':'TEST_ONLY_PRODUCT'}]
    raw['assets']['red']['href']='s3://TEST_ONLY/'+product+'/OTHER.TIF'
    with pytest.raises(transfer.TransferError,match='product_mismatch'):asyncio.run(adapters.usgs_file(raw,raw['assets']['red'],FAKE))


def test_persistence_failure_after_issuer_rotation_is_closed(monkeypatch):
    monkeypatch.setenv('OPERATOR_NASA_TOKEN_EXPIRES_AT',str(time.time()+120));s=op.store();original=s.change
    async def renew(*args):return {'access':'TEST_ONLY_NEW_ROTATION','expires':time.time()+3600}
    monkeypatch.setattr(adapters,'renew',renew)
    def fail(provider,generation,state,value=None):
        if state=='active':raise transfer.TransferError('operator_storage_unavailable')
        return original(provider,generation,state,value)
    monkeypatch.setattr(s,'change',fail)
    with pytest.raises(transfer.TransferError):asyncio.run(op.token('nasa'))
    op._store=storage.Store(s.path)
    with pytest.raises(transfer.TransferError):asyncio.run(op.token('nasa'))


def test_two_real_processes_only_one_can_claim_renewal():
    values,revision,fp=op.config('nasa');s=op.store();row=s.load('nasa',revision,fp,op.seed('nasa',values))
    script='''import json,sys
from app.operator_store import Store,crypto
from app.provider_transfer import TransferError
crypto._restrict_directory=lambda *_:None
data=json.load(sys.stdin)
try:
 Store(data['path']).change('nasa',data['generation'],'renewing')
 print(json.dumps({'claimed':True}))
except TransferError:
 print(json.dumps({'claimed':False}))
'''
    processes=[subprocess.Popen([sys.executable,'-c',script],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(2)]
    for child in processes:child.stdin.write(json.dumps({'path':str(s.path),'generation':row['generation']}));child.stdin.close()
    results=[]
    for child in processes:
        child.wait(timeout=20);assert child.returncode==0;results.append(json.loads(child.stdout.read())['claimed'])
    assert sorted(results)==[False,True] and s.inspect('nasa')['state']=='renewing'


@pytest.mark.parametrize('expiry',['nan','inf','-1',str(time.time()+100*86400)])
def test_invalid_or_unbounded_nasa_seed_expiration_is_not_used(monkeypatch,expiry):
    monkeypatch.setenv('OPERATOR_NASA_TOKEN_EXPIRES_AT',expiry)
    with pytest.raises(transfer.TransferError,match='not_ready'):asyncio.run(op.token('nasa'))


def test_usgs_browse_must_be_returned_for_exact_product(monkeypatch):
    product='LC09_L2SP_116035_20250723_20250726_02_T1'
    raw={'assets':{'red':{'href':'s3://TEST_ONLY/'+product+'/'+product+'_SR_B4.TIF'}}}
    async def fake(method,body,token):
        if method=='scene-metadata':return {'displayId':product,'entityId':'TEST_ONLY_SCENE','browse':[{'browsePath':'https://landsatlook.usgs.gov/browse/'+product+'_browse.jpg'}]}
        return None
    monkeypatch.setattr(adapters,'m2m',fake)
    assert asyncio.run(adapters.usgs_preview(raw,FAKE))['href'].endswith(product+'_browse.jpg')


def test_usgs_scene_metadata_mismatch_blocks_file_and_preview(monkeypatch):
    product='LC09_L2SP_116035_20250723_20250726_02_T1'
    raw={'assets':{'red':{'href':'s3://TEST_ONLY/'+product+'/'+product+'_SR_B4.TIF'}}}
    async def wrong(*_):return {'displayId':'TEST_ONLY_OTHER','entityId':'TEST_ONLY_SCENE'}
    monkeypatch.setattr(adapters,'m2m',wrong)
    with pytest.raises(transfer.TransferError,match='product_mismatch'):
        asyncio.run(adapters.usgs_file(raw,raw['assets']['red'],FAKE))
    with pytest.raises(transfer.TransferError,match='product_mismatch'):
        asyncio.run(adapters.usgs_preview(raw,FAKE))


def test_usgs_html_permission_denial_is_not_invalid_json(monkeypatch):
    def denied(_):return httpx.Response(403,content=b'<html>Access denied</html>',headers={'content-type':'text/html'})
    mock_transport(monkeypatch,denied)
    with pytest.raises(transfer.TransferError,match='operator_permission_denied'):
        asyncio.run(adapters.m2m('download-options',{'datasetName':'landsat_ot_c2_l2','entityIds':['TEST_ONLY_SCENE']},FAKE))


def test_cdse_browse_requires_every_official_node(monkeypatch):
    raw={'id':'S1_TEST_ONLY','assets':{'Product':{'href':'https://download.dataspace.copernicus.eu/odata/v1/Products(1333e31f-c63d-44d1-a99f-427435264d00)/$value'}}}
    calls=[]
    async def fake(url):
        calls.append(url)
        return {'result':[{'Name':('S1_TEST_ONLY.SAFE','preview','quick-look.png')[len(calls)-1]}]}
    monkeypatch.setattr(transfer,'read_json',fake)
    assert asyncio.run(op.cdse_preview(raw))['href'].endswith('/Nodes(preview)/Nodes(quick-look.png)/$value')
    async def absent(url):return {'result':[]}
    monkeypatch.setattr(transfer,'read_json',absent)
    with pytest.raises(transfer.TransferError,match='file_unavailable'):asyncio.run(op.cdse_preview(raw))


def test_cdse_static_password_whitespace_is_preserved(monkeypatch):
    monkeypatch.setenv('OPERATOR_CDSE_USERNAME','TEST_ONLY_USER')
    monkeypatch.setenv('OPERATOR_CDSE_PASSWORD',' TEST ONLY password ')
    monkeypatch.setenv('OPERATOR_CDSE_REDISTRIBUTION_REVIEWED','1')
    assert op.config('cdse')[0]['password']==' TEST ONLY password '


@pytest.mark.skipif(os.name!='nt',reason='Windows DPAPI and directory ACL integration')
def test_native_directory_acl_and_encrypted_operator_store(tmp_path,monkeypatch):
    monkeypatch.setattr(storage.crypto,'_restrict_directory',REAL_RESTRICT_DIRECTORY)
    s=storage.Store(tmp_path/'real-acl'/'operator.sqlite3')
    row=s.load('nasa',1,'TEST_ONLY_FINGERPRINT',{'access':FAKE,'expires':time.time()+3600})
    assert row['access']==FAKE and FAKE.encode() not in s.path.read_bytes()
    assert storage.Store(s.path).load('nasa',1,'TEST_ONLY_FINGERPRINT',{})['access']==FAKE
