"""Reviewed PC collections only. Anonymous SAS never enters normalized Item JSON."""
import asyncio
from datetime import datetime,timezone
import time
from urllib.parse import urlsplit,parse_qs
import httpx
from . import stac
from .provider_registry import COLLECTION_REGISTRY
from .provider_transfer import TransferError

ENDPOINT='https://planetarycomputer.microsoft.com/api/stac/v1'
AUTH='https://planetarycomputer.microsoft.com/api/sas/v1/token/'
STORES={'pc-landsat-c2-l2':{'landsateuwest.blob.core.windows.net':'landsat-c2'},
 'pc-sentinel-2-l2a':{'sentinel2l2a01.blob.core.windows.net':'sentinel2-l2','sentinel2l2a02.blob.core.windows.net':'sentinel2-l2','sentinel2l2a03.blob.core.windows.net':'sentinel2-l2','sentinel2l2a04.blob.core.windows.net':'sentinel2-l2','sentinel2l2a05.blob.core.windows.net':'sentinel2-l2'} }
tokens={}
locks={}


def initial(query,collection):
    body={'collections':[COLLECTION_REGISTRY[collection]['remote_id']],'bbox':list(query.bbox),
        'datetime':f'{query.start_date}T00:00:00Z/{query.end_date}T23:59:59.999999Z','limit':25,'sortby':[{'field':'datetime','direction':'desc'}]}
    if collection=='pc-landsat-c2-l2':body['query']={'platform':{'in':['landsat-8','landsat-9']}}
    return {'method':'POST','url':ENDPOINT+'/search','body':body}


def feature(raw):
    remote=raw.get('collection');collection='pc-'+str(remote)
    if collection not in STORES:raise ValueError('Unregistered PC collection')
    if collection=='pc-landsat-c2-l2' and raw.get('properties',{}).get('platform') not in ('landsat-8','landsat-9'):return None
    properties=dict(raw.get('properties') or {})
    # PC's S2 platform values use Sentinel-2B; registry uses the official STAC
    # lower-case identity. Normalize only this reviewed mapping, retain source.
    platforms={f'Sentinel-2{x.upper()}':f'sentinel-2{x}' for x in 'abc'}
    if collection=='pc-sentinel-2-l2a' and properties.get('platform') in platforms:
        properties['app:source_platform']=properties['platform']
        properties['platform']=platforms[properties['platform']]
    if collection=='pc-sentinel-2-l2a':
        properties.update({'app:native_resolution':'MSI 밴드별 10 / 20 / 60 m',
            'app:output_grid':'L2A 밴드별 10 / 20 / 60 m; 개별 Asset 격자·SCL 별도 확인'})
    else:
        properties.update({'app:native_resolution':'OLI/OLI-2 다중분광 30 m; TIRS/TIRS-2 열관측 100 m',
            'app:output_grid':'C2 L2 반사도·지표온도 30 m 출력; 열관측 원해상도 30 m 아님'})
    return {**raw,'collection':collection,'properties':properties}


async def request_page(client,request,seconds):
    data=await stac.request_page(client,request,seconds)
    data['features']=[value for raw in data['features'] if (value:=feature(raw)) is not None]
    return data


def storage(collection,url):
    u=urlsplit(url)
    if u.scheme!='https' or u.port not in (None,443) or u.query or u.username or u.password or u.fragment:raise TransferError('blocked_destination')
    container=STORES.get(collection,{}).get(u.hostname)
    if not container or not u.path.startswith('/'+container+'/') or '/..' in u.path or '%2f' in u.path.lower():raise TransferError('blocked_destination')
    return u.hostname.split('.')[0],container


async def issue(account,container):
    # No subscription key/account login, optional write/duration are never requested.
    try:
        async with httpx.AsyncClient(timeout=8,follow_redirects=False,trust_env=False) as client:
            async with client.stream('GET',AUTH+account+'/'+container,headers={'Cache-Control':'no-cache'}) as r:
                raw=bytearray()
                async for chunk in r.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw)>32768:raise TransferError('sas_invalid_response')
                if r.status_code==429:raise TransferError('provider_busy')
                if r.status_code!=200:raise TransferError('sas_unavailable',r.status_code)
                import json
                return json.loads(raw)
    except (httpx.TimeoutException,TimeoutError):raise TransferError('timeout') from None
    except (httpx.HTTPError,ValueError):raise TransferError('sas_unavailable') from None


async def signed(collection,url,force=False,failed=None):
    account,container=storage(collection,url);key=(account,container)
    lock=locks.setdefault(key,asyncio.Lock())
    async with lock:
        cached=tokens.get(key)
        if cached and cached[0]>time.time()+60 and (not force or failed and cached[1]!=failed):return url+'?'+cached[1],cached[1]
        data=await issue(account,container)
        try:
            token=data['token'];expiry=datetime.fromisoformat(data['msft:expiry'].replace('Z','+00:00'))
            values=parse_qs(token);se=datetime.fromisoformat(values['se'][0].replace('Z','+00:00'))
            # The official service currently omits spr; transport still enforces
            # HTTPS. Its absence does not grant our proxy permission to use HTTP.
            if expiry.tzinfo is None or se.tzinfo is None or not 0<len(token)<16384 or not values.get('sig') or values.get('spr') not in (None,['https']) or values.get('sp') not in (['r'],['rl']):raise ValueError()
            expires=min(expiry.timestamp(),se.timestamp(),time.time()+24*3600)
            if expires<=time.time()+30:raise ValueError()
        except (KeyError,ValueError,TypeError,AttributeError):raise TransferError('sas_invalid_response') from None
        tokens[key]=(expires,token)
        return url+'?'+token,token
