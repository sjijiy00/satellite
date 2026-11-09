"""Explicit Korean administrative place lookup. Kakao key stays in a server header.

No provider data is persisted/cached. Local sourced camera references remain separate.
"""
import asyncio
from collections import deque
from datetime import datetime, timezone
import hashlib
import json
import math
import os
import re
import time

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .admin_boundaries import canonical_name, REGISTRY as BOUNDARIES
from .spatial_extent import radius_bbox
from typing import Literal

ENDPOINT='https://dapi.kakao.com/v2/local/search/address.json'
DOCS='https://developers.kakao.com/docs/ko/local/dev-guide'
TERMS='https://developers.kakao.com/terms/ko/site-policies'
lock=asyncio.Lock()
recent=deque()
calls=0


class PlaceRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text:str|None=Field(default=None,min_length=1,max_length=2000) # legacy clients only; never sent to Kakao
    place:str=Field(min_length=1,max_length=100)
    kind:Literal['administrative','place']='administrative'
    radius_m:float|None=Field(default=None,gt=0,le=100000,allow_inf_nan=False)

    @model_validator(mode='after')
    def grounded(self):
        if (self.text is not None and self.place not in self.text) or not re.fullmatch(r'[가-힣A-Za-z0-9·.() -]+',self.place):
            raise ValueError('지명 원문은 입력 문장에 포함돼야 합니다. URL·명령은 받지 않습니다.')
        return self


def config():
    missing=[]
    if os.getenv('GEOCODER_ENABLED')!='1':missing.append('GEOCODER_ENABLED')
    if not os.getenv('KAKAO_LOCAL_REST_API_KEY','').strip():missing.append('KAKAO_LOCAL_REST_API_KEY')
    return {'provider':'kakao','ready':not missing,'missing_settings':missing,
        'scope':'대한민국 REGION 행정 주소 또는 특정 장소 키워드 조회. 중심점은 행정경계가 아니며 검증된 경계/명시 거리만 별도 AOI에 사용.',
        'source_url':DOCS,'terms_url':TERMS,
        'message':'Kakao 위치 검색 준비됨. 실제 결과는 조회 후 확인합니다.' if not missing else 'Kakao 위치 검색 미설정. 서버 설정 후 위치 확인을 누르세요. 수동 지도·좌표 입력은 가능합니다.',
        'limits':{'timeout_seconds':8,'requests_per_minute':10,'requests_per_process':100,'pages':1,'results':30,'concurrency':1},
        'storage':'화면의 일시 상태만 사용. 제공처 결과의 서버 캐시·DB·로그 저장 없음.'}


def failure(status,place,message,http_status=None):
    return {'status':status,'mentioned_text':place,'provider':'kakao','message':message,
            'http_status':http_status,'candidates':[],'role':'camera_only'}


async def _request(place,kind='administrative'):
    # Fixed URL, no key in query strings, no redirects or raw error logging.
    async with httpx.AsyncClient(timeout=httpx.Timeout(7,connect=3),follow_redirects=False,trust_env=False) as client:
        endpoint=ENDPOINT if kind=='administrative' else 'https://dapi.kakao.com/v2/local/search/keyword.json'
        # Similar broadens candidates; our component-by-component check below
        # still refuses an unrelated parent or a fuzzy substitute.
        params={'query':canonical_name(place),'analyze_type':'similar','page':1,'size':30} if kind=='administrative' else {'query':place,'page':1,'size':15}
        async with client.stream('GET',endpoint,params=params,
                headers={'Authorization':'KakaoAK '+os.environ['KAKAO_LOCAL_REST_API_KEY']}) as response:
            raw=bytearray()
            async for chunk in response.aiter_bytes():
                raw.extend(chunk)
                if len(raw)>512*1024:raise ValueError('response size')
            if response.status_code!=200:return response.status_code,None
            return 200,json.loads(raw)


def candidate(document,query,checked):
    if document.get('address_type')!='REGION':return None
    a=document.get('address') or {}
    parts=[a.get(k,'') for k in ('region_1depth_name','region_2depth_name','region_3depth_name')]
    parts=[v for v in parts if isinstance(v,str) and v]
    name=document.get('address_name')
    if not isinstance(name,str) or not name or len(name)>200 or not parts:return None
    if canonical_name(query) in BOUNDARIES and canonical_name(name)!=canonical_name(query):return None
    # Never substitute a parent district or fuzzy near-name for the actual place.
    def components(s):
        return [re.sub(r'(특별자치도|특별자치시|특별시|광역시|시|군|구|읍|면|동|도)$','',v) for v in canonical_name(s).split()]
    requested=components(query);actual=components(' '.join(parts))
    # Every requested component must match, in hierarchy order. '수원' can
    # match '수원시'; '수원 매탄동' cannot silently become '경기도 수원시'.
    cursor=0
    for component in requested:
        try:cursor=actual.index(component,cursor)+1
        except ValueError:return None
    x,y=float(document['x']),float(document['y'])
    if not math.isfinite(x+y) or not (124<=x<=132 and 33<=y<=39):raise ValueError('invalid Korean location')
    code=a.get('b_code') or a.get('h_code')
    identity=hashlib.sha256((name+'\0'+str(code or '')).encode()).hexdigest()[:20]
    result={'id':'kakao-'+identity,'name':canonical_name(name),'official_name':name,'official_name_basis':'Kakao REGION 응답 명칭(정부 경계 검증 아님)',
        'admin_level':('읍·면·동' if len(parts)>=3 else '시·군·구' if len(parts)==2 else '시·도'),
        'parent': ' '.join(parts[:-1]),'region_code':code or None,'center':[x,y],'role':'camera_only',
        'source':'Kakao Local 주소 검색','source_url':DOCS,'terms_url':TERMS,'checked_at':checked,
        'note':'제공처 중심점으로 지도만 이동합니다. 행정경계는 제공되지 않았으며 분석 AOI를 만들지 않습니다.'}
    # A gazetteer result is only a camera point, never an automatic AOI.
    return result

def point_candidate(document,query,checked):
    name=document.get('place_name')
    if not isinstance(name,str) or not name or len(name)>200:return None
    x,y=float(document['x']),float(document['y'])
    if not math.isfinite(x+y) or not (124<=x<=132 and 33<=y<=39):raise ValueError('invalid point')
    return {'id':'kakao-poi-'+hashlib.sha256((str(document.get('id'))+'\0'+name).encode()).hexdigest()[:20],
        'name':name,'official_name':name,'admin_level':'특정 장소','parent':document.get('address_name',''),
        'center':[x,y],'role':'camera_only','source':'Kakao Local 키워드 검색','source_url':DOCS,'terms_url':TERMS,
        'checked_at':checked,'boundary':{'status':'unsupported','message':'점 위치는 행정경계가 아닙니다. 명시한 주변 거리가 필요합니다.'}}


async def search(query:PlaceRequest):
    global calls
    place=query.place
    # Fully qualified administrative names can be extracted as a generic place.
    # Route their lookup to address search; candidate() still requires every component.
    kind='administrative' if len(place.split())>=2 and re.search(r'(시|군|구|읍|면|동|리)$',place) else query.kind
    if not config()['ready']:return failure('not_configured',place,config()['message'])
    # '일대' is not a district boundary. Do not silently strip it and pick an AOI.
    if re.search(r'일대|근처|주변',place):return failure('needs_confirmation',place,'정확한 시·군·구 명칭을 확인하세요. 일대·주변의 범위는 자동 확정하지 않습니다.')
    now=time.monotonic()
    while recent and recent[0]<now-60:recent.popleft()
    if len(recent)>=10 or calls>=100:return failure('limited',place,'앱의 위치 조회 상한에 도달했습니다. 자동 재시도하지 않습니다.')
    if lock.locked():return failure('limited',place,'다른 위치 조회 중입니다. 완료 후 다시 확인하세요.')
    async with lock:
        recent.append(now);calls+=1
        try:
            async with asyncio.timeout(8):status,body=await _request(place) if kind=='administrative' else await _request(place,'place')
            if status in (401,403):return failure('authentication_failed',place,'Kakao 키·앱의 카카오맵 사용 권한을 확인하세요.',status)
            if status==429:return failure('limited',place,'Kakao 요청 한도에 도달했습니다. 쿼터를 확인하세요.',status)
            if status!=200:return failure('failed',place,'Kakao 위치 검색 서비스가 정상 응답하지 않았습니다. 기존 장소·AOI를 유지합니다.',status)
            docs=body['documents'];meta=body['meta']
            if not isinstance(docs,list) or len(docs)>30 or not isinstance(meta.get('is_end'),bool):raise ValueError('schema')
            checked=datetime.now(timezone.utc).isoformat()
            found={}
            for d in docs:
                c=candidate(d,place,checked) if kind=='administrative' else point_candidate(d,place,checked)
                if c and query.radius_m is not None:
                    c['extent']={'bbox':radius_bbox(c['center'],query.radius_m),'radius_m':query.radius_m,
                        'method':'WGS84 Geod 0.1도 간격 원주·1m 외측 여유','scope':'확인된 점과 사용자 거리의 외접 범위','polygon_clipping':False}
                if c:found[c['id']]=c
            values=list(found.values())
            if not values:return failure('no_results',place,'일치하는 행정 지명 결과가 없습니다. 존재하지 않는 지명이라는 판정은 아닙니다. 상위 지역을 포함해 확인하거나 지도를 직접 지정하세요.',200)
            incomplete=not meta['is_end']
            # A short ambiguous name cannot become certain because the provider ranked one result first.
            ambiguous=len(values)>1 or incomplete or place.strip() in ('광주','중구')
            result={'status':'ambiguous' if ambiguous else 'resolved','mentioned_text':place,'provider':'kakao',
                    'candidates':values,'http_status':200,'truncated':incomplete,'checked_at':checked,'role':'camera_only',
                    'message':'행정 지명 후보를 선택하세요. 첫 30개만 조회합니다.' if ambiguous else '위치 확인 완료. 중심점은 지도 이동에만 사용합니다.'}
            if not ambiguous:result.update(values[0])
            return result
        except (TimeoutError,httpx.TimeoutException):return failure('timeout',place,'Kakao 위치 검색 시간 상한 8초를 넘었습니다. 기존 장소·AOI를 유지합니다.')
        except httpx.HTTPError:return failure('failed',place,'Kakao 위치 검색 연결에 실패했습니다. 기존 장소·AOI를 유지합니다.')
        except (ValueError,KeyError,TypeError,AttributeError):return failure('invalid_response',place,'위치 응답의 명칭·좌표·형식을 검증하지 못했습니다. 기존 장소·AOI를 유지합니다.')
