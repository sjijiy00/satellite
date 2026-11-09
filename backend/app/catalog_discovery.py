"""Bounded official collection discovery. Read only: never mutates reviewed registrations."""
import asyncio
from urllib.parse import urljoin, urlsplit
import httpx
from fastapi import HTTPException
from .provider_registry import PROVIDERS, COLLECTION_REGISTRY


async def discover(provider_id):
    if provider_id not in PROVIDERS:
        raise HTTPException(404, '등록된 제공처가 아닙니다.')
    endpoint = PROVIDERS[provider_id]['endpoint']
    known = {v['remote_id'] for v in COLLECTION_REGISTRY.values() if v['provider_id']==provider_id}
    if provider_id=='noaa-nodd':
        return {'provider_id':provider_id,'collections':[{'id':v['remote_id'],'title':v['version'],'registered':True,'review_required':False} for v in COLLECTION_REGISTRY.values() if v['provider_id']==provider_id],
            'complete':False,'requests':0,'truncated':True,'error':None,'scope':'검토 등록한 공개 NODD 제품만. STAC 발견 API가 아니며 NOAA 전체 목록을 조회한 것이 아닙니다.'}
    collections, requests, complete, error = [], 0, False, None
    url = endpoint + ('/collections.json?instrument=VIIRS&page_size=25&page_num=1' if provider_id=='nasa-cmr' else '/collections?limit=25')
    async def run():
        nonlocal url, requests, complete
        async with httpx.AsyncClient(follow_redirects=False, timeout=5) as client:
            while url and requests < 3:
                requests += 1
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                rows = data['feed']['entry'] if provider_id=='nasa-cmr' else data['collections']
                for row in rows[:25]:
                    collections.append({'id':row['id'], 'title':row.get('dataset_id') or row.get('title'),
                                        'registered':row['id'] in known, 'review_required':row['id'] not in known})
                if provider_id=='nasa-cmr':
                    page = requests + 1
                    url = endpoint+f'/collections.json?instrument=VIIRS&page_size=25&page_num={page}' if len(rows)==25 else None
                else:
                    link = next((l for l in data.get('links',[]) if l.get('rel')=='next'), None)
                    url = urljoin(url,link['href']) if link else None
                    if url and (urlsplit(url).scheme!='https' or urlsplit(url).netloc!=urlsplit(endpoint).netloc):
                        raise ValueError('Invalid next origin')
                complete = url is None
                if len(rows)>25:
                    complete = False  # Provider ignored page size; omitted scope stays explicit.
                    break
    try:
        await asyncio.wait_for(run(), 15)
    except (httpx.HTTPError, asyncio.TimeoutError, ValueError, KeyError, TypeError):
        error = '공식 제공처 컬렉션 조회 실패·시간 초과. 등록부를 변경하지 않았습니다.'
    return {'provider_id':provider_id, 'collections':collections, 'complete':complete, 'requests':requests,
            'truncated':not complete, 'error':error, 'limits':{'requests':3,'seconds':15,'page_size':25,'results':75},
            'scope':'CMR VIIRS 컬렉션만' if provider_id=='nasa-cmr' else '공식 STAC collections 페이지',
            'notice':'발견·재조회만 수행합니다. 미검토 제품의 사양·추천·검색 연결은 자동 생성하지 않습니다.'}
