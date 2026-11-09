"""TEST ONLY: diagnostics may retain public identity, never credentials/Location/body."""
import asyncio
import json
import httpx
import pytest
from app import provider_transfer as transfer
from test_media_access import mock_transport
from test_hls import entry


def test_400_is_not_reported_as_authentication_or_download_success():
    from app.media_access import failure
    result=failure(transfer.TransferError('provider_error',400))
    assert result['status']=='provider_error' and result['http_status']==400
    assert not result['access_verified'] and 'HTTP 400' in result['message']
    assert '인증 실패 여부는 확인되지' in result['message']


@pytest.fixture(autouse=True)
def dns(monkeypatch):
    async def safe(host): pass
    monkeypatch.setattr(transfer,'public_dns',safe)


def test_empty_400_records_stage_without_auth_or_body(monkeypatch):
    url=entry()['links'][-1]['href'];records=[]
    mock_transport(monkeypatch,lambda r:httpx.Response(400,headers={'Content-Type':'application/json','Content-Length':'0'}))
    with transfer.diagnostics(records),pytest.raises(transfer.TransferError,match='provider_error'):
        asyncio.run(transfer.read(url,max_bytes=1024))
    response=next(r for r in records if r['stage']=='response')
    assert response['status']==400 and response['declared_bytes']==0
    assert not response['authorization_present'] and not response['range_requested']
    assert response['path']==url.split('.gov',1)[1]
    assert next(r for r in records if r['stage']=='error_body')['sampled_bytes']==0


def test_redirect_trace_never_retains_signed_query_headers_or_error_body(monkeypatch):
    first=entry()['links'][0]['href'];name=first.rsplit('/',1)[1];calls=[];records=[]
    destination='https://d1nklfio7vscoe.cloudfront.net/s3-protected/lp-prod-protected.s3.us-west-2.amazonaws.com/HLSL30.020/'+entry()['title']+'/'+name+'?X-Amz-Signature=TEST_ONLY_SIGNATURE'
    def handle(r):
        calls.append(r)
        if len(calls)==1:return httpx.Response(302,headers={'Location':destination,'Set-Cookie':'TEST_ONLY_COOKIE'})
        assert 'authorization' not in r.headers
        return httpx.Response(403,json={'error':'TEST_ONLY_BODY','token':'TEST_ONLY_SECRET'})
    mock_transport(monkeypatch,handle)
    with transfer.diagnostics(records),pytest.raises(transfer.TransferError,match='permission_required'):
        asyncio.run(transfer.read(first,max_bytes=1024,token='TEST_ONLY_BEARER',probe=True,expected_name=name,provider_scope='nasa'))
    text=json.dumps(records)
    assert all(s not in text for s in ('TEST_ONLY_SIGNATURE','TEST_ONLY_COOKIE','TEST_ONLY_SECRET','TEST_ONLY_BEARER','TEST_ONLY_BODY','?','Location'))
    responses=[r for r in records if r['stage']=='response']
    assert [r['status'] for r in responses]==[302,403]
    assert [r['authorization_present'] for r in responses]==[True,False]
    assert responses[1]['host']=='d1nklfio7vscoe.cloudfront.net'


@pytest.mark.parametrize('value',[None,'bytes 5-8/100','bytes 0-8/8','bytes 0-9/*'])
def test_probe_requires_valid_content_range(monkeypatch,value):
    mock_transport(monkeypatch,lambda r:httpx.Response(206,content=b'123456789',headers={'Content-Range':value} if value else {}))
    with pytest.raises(transfer.TransferError,match='invalid_content_range'):
        asyncio.run(transfer.read(entry()['links'][0]['href'],max_bytes=1000,probe=True))


def test_range_ignored_is_bounded_and_not_a_complete_download(monkeypatch):
    mock_transport(monkeypatch,lambda r:httpx.Response(200,content=b'x'*4096))
    result=asyncio.run(transfer.read(entry()['links'][0]['href'],max_bytes=8192,probe=True))
    try:assert result.size==1024 and not result.complete and result.total_size==4096
    finally:result.close()
    with pytest.raises(transfer.TransferError,match='size_limit'):
        asyncio.run(transfer.read(entry()['links'][0]['href'],max_bytes=1000,probe=True))


def test_diagnostics_are_bounded_scoped_and_blocked_target_redacted():
    records=[]
    with transfer.diagnostics(records):
        for _ in range(100):transfer.diagnostic_event('https://evil.test/TEST_ONLY_SECRET?token=TEST_ONLY',stage='validate')
    transfer.diagnostic_event('https://evil.test/',stage='outside')
    assert len(records)==64 and 'TEST_ONLY' not in json.dumps(records)
    assert records[0]['host']=='[blocked]' and records[0]['path']=='[redacted]'


def test_diagnostics_are_isolated_between_concurrent_tasks(monkeypatch):
    mock_transport(monkeypatch,lambda r:httpx.Response(400,content=b''))
    async def one(family):
        records=[]
        with transfer.diagnostics(records):
            with pytest.raises(transfer.TransferError):await transfer.read(entry(family)['links'][0]['href'],max_bytes=1000)
        return records
    async def run():return await asyncio.gather(one('L30'),one('S30'))
    left,right=asyncio.run(run())
    assert all('HLSL30' in r['path'] for r in left)
    assert all('HLSS30' in r['path'] for r in right)
