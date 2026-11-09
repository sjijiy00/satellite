"""Canonical-only raster reads. No URL API, mixed credentials or full-file fallback."""
import asyncio
from contextlib import contextmanager
import httpx
from .range_reader import RangeStore,public_cog
from .pixel_policy import QualityError
from . import planetary,provider_transfer

class CheckedClient:
    def __init__(self,collection,maximum=128):
        self.collection=collection
        self.requests=0
        self.maximum=maximum
        self.tile_start=None
        self.runner=asyncio.Runner()
        self.client=httpx.Client(follow_redirects=False,trust_env=False,headers={'Accept-Encoding':'identity'})
    def target(self,url,force=False,failed=None):
        if self.collection in planetary.STORES:
            self.count() # conservatively reserve a potential SAS HTTP request
            target,token=self.runner.run(planetary.signed(self.collection,url,force,failed))
        elif self.collection=='sentinel-2-l2a' and public_cog(url):target,token=url,None
        else:raise QualityError('현재 제공처의 AOI 범위 읽기는 지원하지 않습니다. 원본 인증 경로를 우회하지 않습니다.')
        self.runner.run(provider_transfer.validate_destination(target))
        return target,token
    def count(self):
        if self.tile_start is not None and self.requests-self.tile_start>=128:raise QualityError('개별 타일 제공처·SAS 요청 상한 초과')
        if self.requests>=self.maximum:raise QualityError('제공처·SAS 요청 합계 상한 초과')
        self.requests+=1
    def head(self,url,**kwargs):
        target,token=self.target(url)
        try:self.count();r=self.client.head(target,**kwargs)
        except httpx.HTTPError:raise QualityError('제공처 헤더 접근 네트워크 오류/시간 초과') from None
        if r.status_code in (401,403) and self.collection in planetary.STORES:
            r.close();target,_=self.target(url,True,token)
            try:self.count();r=self.client.head(target,**kwargs)
            except httpx.HTTPError:raise QualityError('제공처 헤더 재확인 실패') from None
        return r
    @contextmanager
    def stream(self,method,url,**kwargs):
        target,token=self.target(url)
        for attempt in range(2):
            self.count()
            with self.client.stream(method,target,**kwargs) as response:
                if response.status_code in (401,403) and attempt==0 and self.collection in planetary.STORES:
                    target,_=self.target(url,True,token)
                    continue
                yield response
                return
    def close(self):
        self.client.close();self.runner.close()

def open_sources(payload):
    collections={s['collection'] for s in payload['scenes']}
    if len(collections)!=1:raise QualityError('서로 다른 제공처/제품 범위 읽기는 혼합하지 않습니다.')
    collection=next(iter(collections))
    urls={a['path']:a['url'] for s in payload['scenes'] for a in s['assets'].values()}
    def permitted(url):
        if collection=='sentinel-2-l2a':return public_cog(url)
        if collection in planetary.STORES:
            try:planetary.storage(collection,url);return True
            except provider_transfer.TransferError:return False
        return False
    # NASA/USGS/CDSE range processing has no validated engine yet. Their media
    # authentication remains in media_access; never attach its grants here.
    if not all(permitted(u) for u in urls.values()):raise QualityError('검증된 제공처의 canonical 범위 읽기 경로가 아닙니다.')
    from .pixel_policy import LIMITS
    large=payload.get('bounded_tiling',False)
    limits={**LIMITS,'worker_seconds':240,'transfer_bytes':256*1024**2,'range_requests':512} if large else LIMITS
    return RangeStore(urls,client=CheckedClient(collection,512 if large else 128),validator=permitted,limits=limits)
