"""Read-only HTTP Range file adapter for Rasterio's Python opener; never full GET."""
import io
import re
from collections import OrderedDict
from time import monotonic
from contextlib import contextmanager
from urllib.parse import urlsplit
import httpx
from .pixel_policy import LIMITS,QualityError


def public_cog(url):
    try:
        p=urlsplit(url)
        return (p.scheme=='https' and p.hostname=='sentinel-cogs.s3.us-west-2.amazonaws.com'
                and p.port in (None,443) and not (p.query or p.fragment or p.username or p.password)
                and p.path.startswith('/sentinel-s2-l2a-cogs/') and p.path.endswith('.tif'))
    except (TypeError,ValueError):return False


class RangeStore:
    def __init__(self,urls,client=None,limits=None,*,validator=public_cog):
        if not all(validator(u) for u in urls.values()):raise QualityError('허용된 공개 Sentinel-2 COG URL이 아닙니다.')
        self.urls=urls;self.limits=limits or LIMITS;self.started=monotonic()
        self.bytes=0;self.requests=0;self.info={};self.cache=OrderedDict();self.cache_bytes=0
        self.client=client or httpx.Client(follow_redirects=False,headers={'Accept-Encoding':'identity'})
        self.failure=None
        self.tile_budget=None

    @contextmanager
    def tile_window(self):
        self.tile_budget=(self.bytes,self.requests,monotonic())
        if hasattr(self.client,'tile_start'):self.client.tile_start=self.client.requests
        try:yield
        finally:
            self.tile_budget=None
            if hasattr(self.client,'tile_start'):self.client.tile_start=None

    def close(self):self.client.close()

    def check(self):
        if self.failure:raise QualityError(self.failure)
        if self.tile_budget:
            b,r,t=self.tile_budget
            if self.bytes-b>64*1024**2 or self.requests-r>=128 or monotonic()-t>=60:
                raise QualityError('개별 타일의 전송/요청/시간 상한 초과')
        if monotonic()-self.started>=self.limits['worker_seconds']:raise QualityError('픽셀 처리 시간 상한 초과')
        if self.requests>=self.limits['range_requests']:raise QualityError('HTTP 범위 요청 횟수 상한 초과')

    def metadata(self,path):
        if path not in self.urls:raise FileNotFoundError(path)
        if path not in self.info:
            self.check();self.requests+=1
            r=self.client.head(self.urls[path],timeout=self.limits['request_seconds'])
            if r.status_code!=200:raise QualityError(f'파일 HEAD 접근 실패 (HTTP {r.status_code})')
            try:size=int(r.headers['content-length'])
            except (ValueError,KeyError):raise QualityError('원본 파일 크기 미확인: 읽기 중단')
            if not 0<size<=self.limits['file_bytes']:raise QualityError('원본 파일 크기 상한 초과/빈 파일')
            self.info[path]={'size':size,'etag':r.headers.get('etag'),'url':self.urls[path]}
        return self.info[path]

    def block(self,path,start,length):
        try:
            self.check();meta=self.metadata(path)
            if length<0 or length>8*1024*1024:raise QualityError('전체 파일 또는 과도한 단일 읽기 요청 중단')
            if start>=meta['size'] or length==0:return b''
            end=min(meta['size'],start+length)
            for (p,lo,hi),body in list(self.cache.items()):
                if p==path and lo<=start and end<=hi:return body[start-lo:end-lo]
            lo=(start//16384)*16384;hi=min(meta['size'],((end+16383)//16384)*16384)
            if self.tile_budget and self.bytes-self.tile_budget[0]+hi-lo>64*1024**2:raise QualityError('개별 타일 누적 전송량 상한 초과')
            if self.bytes+hi-lo>self.limits['transfer_bytes']:raise QualityError('누적 전송량 상한 초과')
            self.check();self.requests+=1
            headers={'Range':f'bytes={lo}-{hi-1}','Accept-Encoding':'identity'}
            if meta['etag']:headers['If-Match']=meta['etag']
            with self.client.stream('GET',self.urls[path],headers=headers,timeout=self.limits['request_seconds']) as r:
                expected=f'bytes {lo}-{hi-1}/{meta["size"]}'
                if r.status_code!=206 or r.headers.get('content-range')!=expected:
                    raise QualityError('서버가 정확한 HTTP 206 범위 읽기를 지원하지 않거나 파일이 변경되었습니다.')
                if r.headers.get('content-encoding','identity')!='identity':raise QualityError('압축된 HTTP 전송은 지원하지 않습니다.')
                body=bytearray()
                for chunk in r.iter_raw():
                    self.bytes+=len(chunk)
                    if self.bytes>self.limits['transfer_bytes'] or len(body)+len(chunk)>hi-lo:raise QualityError('전송량/범위 응답 크기 상한 초과')
                    body.extend(chunk)
                if len(body)!=hi-lo:raise QualityError('불완전한 범위 응답')
            body=bytes(body);self.cache[(path,lo,hi)]=body;self.cache_bytes+=len(body)
            while self.cache_bytes>16*1024*1024:
                _,old=self.cache.popitem(last=False);self.cache_bytes-=len(old)
            return body[start-lo:end-lo]
        except (httpx.HTTPError,QualityError) as e:
            self.failure=str(e) if isinstance(e,QualityError) else '범위 읽기 네트워크 오류/시간 초과'
            raise QualityError(self.failure) from None

    # fsspec-like protocol prevents probing auxiliary files or unrelated URLs.
    def isdir(self,path):return False
    def isfile(self,path):return path in self.urls
    def ls(self,path):return []
    def mtime(self,path):return 0
    def size(self,path):return self.metadata(path)['size']
    def open(self,path,mode='rb'):
        if mode not in ('r','rb'):raise QualityError('읽기 전용')
        return RangeFile(self,path)


class RangeFile(io.RawIOBase):
    def __init__(self,store,path):
        self.store=store;self.path=path;self.pos=0;self.length=store.metadata(path)['size']
    def readable(self):return True
    def seekable(self):return True
    def tell(self):return self.pos
    def seek(self,offset,whence=0):
        pos=offset if whence==0 else self.pos+offset if whence==1 else self.length+offset
        if pos<0:raise ValueError('negative position')
        self.pos=pos;return pos
    def read(self,size=-1):
        if size<0:raise QualityError('전체 파일 읽기는 금지되어 있습니다.')
        body=self.store.block(self.path,self.pos,size);self.pos+=len(body);return body
    def readinto(self,buffer):
        body=self.read(len(buffer));buffer[:len(body)]=body;return len(body)
