import httpx
import pytest
from app.range_reader import RangeStore,public_cog
from app.pixel_policy import LIMITS,QualityError

URL='https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/TEST_ONLY/a.tif'


def store(mode='ok',**limits):
    calls=[];data=b'0123456789'*10000
    def handler(r):
        calls.append(r)
        if r.method=='HEAD':return httpx.Response(200,headers={'Content-Length':str(len(data)),'ETag':'TEST'})
        start,end=map(int,r.headers['range'].split('=')[1].split('-'))
        if mode=='ignored':return httpx.Response(200,content=data)
        if mode=='redirect':return httpx.Response(302,headers={'Location':'http://127.0.0.1/private'})
        if mode=='timeout':raise httpx.ReadTimeout('TEST ONLY timeout')
        if mode=='malformed':return httpx.Response(206,headers={'Content-Range':'bytes 0-1/2'},stream=httpx.ByteStream(b'xx'))
        return httpx.Response(206,headers={'Content-Range':f'bytes {start}-{end}/{len(data)}'},stream=httpx.ByteStream(data[start:end+1]))
    return RangeStore({'a.tif':URL},httpx.Client(transport=httpx.MockTransport(handler)),LIMITS|limits),calls


def test_exact_range_cache_and_seek():
    s,calls=store()
    with s.open('a.tif') as f:
        f.seek(1);assert f.read(9)==b'123456789'
        f.seek(0);assert f.read(10)==b'0123456789'
        with pytest.raises(QualityError):f.read()
    assert s.bytes==16384 and len(calls)==2
    assert calls[-1].headers['if-match']=='TEST'
    assert all(r.method=='HEAD' or 'range' in r.headers for r in calls)


@pytest.mark.parametrize('mode',['ignored','redirect','timeout','malformed'])
def test_no_full_get_fallback(mode):
    s,_=store(mode)
    with pytest.raises(QualityError):s.open('a.tif').read(10)
    assert s.bytes==0


def test_byte_request_and_file_caps():
    for limits in ({'transfer_bytes':10},{'range_requests':1},{'file_bytes':100}):
        s,_=store(**limits)
        with pytest.raises(QualityError):s.open('a.tif').read(10)


def test_url_and_sidecar_restrictions():
    for u in ['http://127.0.0.1/a.tif',URL+'?secret=x',URL.replace('https://','https://user:pass@'),URL.replace('sentinel-cogs','other')]:
        assert not public_cog(u)
    s,calls=store()
    with pytest.raises(FileNotFoundError):s.open('a.tif.aux.xml')
    assert not calls


def test_elapsed_time_cap_stops_before_network(monkeypatch):
    from app import range_reader
    s,calls=store()
    monkeypatch.setattr(range_reader,'monotonic',lambda:s.started+61)
    with pytest.raises(QualityError,match='시간 상한'):s.open('a.tif')
    assert not calls
