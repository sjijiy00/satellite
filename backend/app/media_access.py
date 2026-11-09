"""Canonical per-asset diagnosis, session-bound preview receipts and bounded downloads."""
import asyncio
import json
import math
import os
import re
import secrets
import time
import warnings
from dataclasses import dataclass
from threading import Lock
from urllib.parse import urlsplit, urlencode

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse
from pydantic import BaseModel, Field, ConfigDict
from rasterio.io import MemoryFile
from rasterio.errors import NotGeoreferencedWarning

from .models import SearchItemReference
from . import cmr, earthdata_auth as auth, landsat_access as landsat, provider_transfer as transfer
from .safe_urls import safe_url
from . import operator_access as operator
from . import operator_preview_cache
from . import public_media,planetary,noaa_nodd
from .provider_registry import COLLECTION_REGISTRY

COOKIE='satellite_media_session'
TTL=120
MAX_TICKETS=100
MAX_MEMORY=32*1024**2
HOURLY_BYTES=512*1024**2
CDSE_HOURLY_BYTES=3*1024**3
INSPECT_SECONDS=60
DOWNLOAD_SECONDS=120
MESSAGES={
 'missing_asset':'미리보기 Asset이 없습니다. 자료 자체가 없다는 뜻은 아닙니다.',
 'unsupported_format':'선택 Asset은 이 미리보기/원본 전송에서 지원하지 않는 형식입니다.',
 'blocked_destination':'허용되지 않은 제공처 주소여서 요청하지 않았습니다.',
 'blocked_redirect':'안전하지 않은 리다이렉트를 차단했습니다.',
 'redirect_item_mismatch':'다른 파일로 이동하는 리다이렉트를 차단했습니다.',
 'redirect_limit':'리다이렉트 횟수 상한입니다.',
 'requester_pays':'AWS requester-pays 자료입니다. 비용 동의·AWS 인증 없이 접근하지 않습니다.',
 'usgs_login_required':'이 USGS 파일 경로는 별도 USGS 로그인이 필요합니다. 검색 결과와 공개 미리보기 접근은 별개입니다.',
 'login_required':'NASA Earthdata 계정 연결 또는 제공처 앱 승인이 필요합니다.',
 'earthdata_not_configured':'Earthdata 앱 등록·서버 연결 설정이 아직 준비되지 않았습니다. 개인 User Token을 공용 설정에 넣지 마세요.',
 'reconnection_required':'NASA 인증이 만료되거나 갱신이 거부됐습니다. Earthdata를 다시 연결하세요.',
 'unauthorized':'파일 인증에 실패했습니다. 계정 연결과 이 다운로드 서비스의 승인을 확인하세요.',
 'permission_required':'파일 접근이 거부됐습니다. 권한·앱 승인·EULA 중 원인은 확인되지 않았습니다.',
 'eula_required':'제공처가 EULA 동의를 요구했습니다.',
 'application_authorization_required':'제공처가 다운로드 앱 승인을 요구했습니다.',
 'provider_authentication_required':'이 제공처의 원본 인증은 앱에 연결되지 않았습니다. NASA 토큰으로 대신할 수 없습니다.',
 'not_found':'제공처가 파일/장면 없음(404/410)을 반환했습니다.',
 'product_mismatch':'제품 ID·플랫폼·수준·촬영일·컬렉션 버전이 일치하지 않아 대체 파일을 연결하지 않았습니다.',
 'size_limit':'파일 크기·전송량 상한을 넘습니다. 제공처에서 직접 받으세요.',
 'quota_limit':'시간당 전송량 상한입니다. 잠시 후 다시 시도하세요.',
 'busy':'다른 파일 전송 중입니다. 자동 재시도하지 않습니다.',
 'timeout':'제공처 요청 시간 상한을 넘었습니다.',
 'network_error':'제공처 연결에 실패했습니다.',
 'invalid_metadata':'원본 Item 응답을 확인할 수 없습니다.',
 'invalid_image':'실제 이미지 형식/무결성을 확인하지 못했습니다.',
 'invalid_file':'파일 응답의 헤더가 원본 형식과 일치하지 않습니다. 다운로드 가능으로 처리하지 않았습니다.',
 'login_page':'파일 대신 로그인 HTML이 반환됐습니다.',
 'empty_file':'빈 파일입니다.', 'incomplete_transfer':'전체 파일 수신이 완료되지 않았습니다.',
 'invalid_content_range':'제공처의 부분 파일 범위 응답이 유효하지 않아 원본 접근 확인을 보류했습니다.',
 'provider_error':'제공처 요청에 실패했습니다.', 'provider_busy':'제공처 요청 상한입니다.',
}
MESSAGES.update({'sas_unavailable':'공개 SAS 발급 서비스 응답을 확인하지 못했습니다. 계정 로그인으로 대체하지 않습니다.',
 'sas_invalid_response':'공개 SAS의 형식·유효 기간을 검증하지 못했습니다. 기존 파일로 대체하지 않습니다.'})
for _code in ('not_ready','not_initialized','reused_seed','storage_unavailable','configuration_changed','changed','multiworker_unsupported','disabled','revoked','expired','reconnection_required','mfa_required','permission_denied','provider_error','timeout','invalid_response','file_unavailable','preparing','busy','quota','renewing','product_not_enabled','policy_not_reviewed'):
    MESSAGES['operator_'+_code]='운영자 제공 자료 접근이 현재 제한됩니다. ('+_code+') 공개 미리보기와 검색 상태는 별도입니다.'
MESSAGES['operator_reconnection_required']='운영자 제공처 인증이 실패하거나 갱신되지 않았습니다. 서버의 계정 정보·2단계 인증 상태를 확인하고 운영자 접근을 다시 초기화해야 합니다.'
MESSAGES['operator_mfa_required']='제공처가 2단계 인증을 요구합니다. 공식 인증 절차로 얻은 갱신 토큰을 서버에 설정해야 합니다.'


class InspectRequest(SearchItemReference):
    model_config=ConfigDict(extra='forbid')
    provider_id: str
    asset_keys: list[str]=Field(default_factory=list,max_length=8)
    include_preview: bool=True


@dataclass(repr=False)
class Ticket:
    owner: str
    reference: dict
    key: str
    expires: float
    auth_sid: str | None=None
    image: bytes | None=None
    media_type: str | None=None
    filename: str | None=None
    completed: bool=False
    operator_provider: str | None=None
    operator_generation: int | None=None


_lock=Lock()
_clients={}
_tickets:dict[str,Ticket]={}
_usage={}
_active=0
_generation=secrets.token_urlsafe(16)


def cleanup():
    now=time.monotonic()
    for k in list(_tickets):
        if _tickets[k].expires<=now:_tickets.pop(k,None)
    for k in list(_clients):
        if _clients[k]<=now:_clients.pop(k,None)
    for k in list(_usage):
        if _usage[k][0]+3600<=now:_usage.pop(k,None)


def owner(request,create=False):
    with _lock:
        cleanup()
        value=request.cookies.get(COOKIE)
        if value in _clients:return value
        if not create:return None
        if len(_clients)>=1000:raise HTTPException(429,'미디어 세션 상한입니다.')
        value=secrets.token_urlsafe(32);_clients[value]=time.monotonic()+3600
        return value


def session_response(request):
    with _lock:
        cleanup()
        identity=request.cookies.get(COOKIE)
        if identity not in _clients:
            if len(_clients)>=1000:raise HTTPException(429,'미디어 세션 상한입니다.')
            identity=secrets.token_urlsafe(32)
            _clients[identity]=time.monotonic()+3600
        expires_at=int(time.time()+max(0,_clients[identity]-time.monotonic()))
    response=JSONResponse({'ready':True,'session_generation':_generation,'expires_at':expires_at},headers={'Cache-Control':'no-store'})
    response.set_cookie(COOKIE,identity,max_age=3600,httponly=True,samesite='strict',secure=request.url.scheme=='https',path='/api/media')
    return response


def issue(ticket):
    with _lock:
        cleanup()
        memory=sum(len(t.image or b'') for t in _tickets.values())
        if len(_tickets)>=MAX_TICKETS or memory+len(ticket.image or b'')>MAX_MEMORY:
            raise transfer.TransferError('busy')
        key=secrets.token_hex(16);_tickets[key]=ticket
        return key


def get_ticket(request,key):
    identity=owner(request)
    with _lock:
        cleanup();ticket=_tickets.get(key)
        if not ticket or not identity or ticket.owner!=identity:
            raise HTTPException(404,{'code':'MEDIA_RECEIPT_INVALID','message':'현재 사용자에게 유효한 파일 확인 결과가 없습니다.'})
        if ticket.auth_sid and ticket.auth_sid!=request.cookies.get(auth.SESSION_COOKIE):
            raise HTTPException(404,{'code':'MEDIA_RECEIPT_INVALID','message':'현재 사용자에게 유효한 파일 확인 결과가 없습니다.'})
        if ticket.auth_sid:
            _,session=auth._session(request)
            if not session or session.state!='connected' or (ticket.image is not None and session.expires_at<=time.monotonic()):
                raise HTTPException(401,'파일 접근을 다시 확인하거나 Earthdata를 재연결하세요.')
        if ticket.operator_provider:
            try:
                operator.require_product(ticket.reference)
                if not operator.enabled(ticket.operator_provider) or operator.current_generation(ticket.operator_provider)!=ticket.operator_generation:raise transfer.TransferError('operator_changed')
            except transfer.TransferError:raise HTTPException(409,'운영자 접근 상태가 바뀌었습니다. 파일 접근을 다시 확인하세요.') from None
        return ticket


def same_origin(request):
    if any(operator.enabled(p) for p in operator.FIELDS):
        origin=os.getenv('OPERATOR_PUBLIC_ORIGIN','http://127.0.0.1:3000')
        if request.headers.get('origin')!=origin:raise HTTPException(403,'사이트에서 다시 시도하세요.')
        return
    config=auth.settings()
    origin=request.headers.get('origin','')
    if config:
        valid=origin==config.origin
    else:
        # Without OAuth settings there are no private credentials; allow local dev
        # origins only (including isolated verification ports), never public sites.
        try:
            parsed=urlsplit(origin)
            valid=parsed.scheme in ('http','https') and parsed.hostname in ('127.0.0.1','localhost') and not parsed.username and not parsed.password
        except ValueError:valid=False
    if not valid:raise HTTPException(403,'사이트에서 다시 시도하세요.')


def enter():
    global _active
    with _lock:
        if _active>=2:raise transfer.TransferError('busy')
        _active+=1


async def enter_when_ready(seconds=0):
    deadline=time.monotonic()+seconds
    while True:
        try:return enter()
        except transfer.TransferError as error:
            if error.code!='busy' or time.monotonic()>=deadline:raise
            await asyncio.sleep(0.2)


def leave():
    global _active
    with _lock:_active-=1


def charge(identity,amount,limit=HOURLY_BYTES):
    charge_many((identity,),amount,limit)


def charge_many(identities,amount,limit=HOURLY_BYTES):
    """Reserve all applicable quotas atomically before a transfer starts."""
    with _lock:
        cleanup()
        now=time.monotonic()
        rows={identity:_usage.get(identity,(now,0)) for identity in identities}
        blocked=[started for started,used in rows.values() if used+amount>limit]
        if blocked:
            error=transfer.TransferError('quota_limit')
            error.retry_after_seconds=max(1,math.ceil(max(blocked)+3600-now))
            raise error
        _usage.update({identity:(started,used+amount) for identity,(started,used) in rows.items()})


async def canonical(reference):
    collection,identifier=reference['collection'],reference['id']
    if collection==noaa_nodd.COLLECTION:return await noaa_nodd.canonical(identifier)
    if collection in planetary.STORES:
        remote=COLLECTION_REGISTRY[collection]['remote_id']
        raw=await transfer.read_json(planetary.ENDPOINT+'/collections/'+remote+'/items/'+identifier)
        if raw.get('id')!=identifier or raw.get('collection')!=remote:raise transfer.TransferError('invalid_metadata')
        item=planetary.feature(raw)
        if item is None:raise transfer.TransferError('invalid_metadata')
        return item
    if collection in cmr.COLLECTIONS:
        data=await transfer.read_json(cmr.ENDPOINT+'/granules.json?'+urlencode({'concept_id':identifier,'page_size':1}))
        entries=data.get('feed',{}).get('entry',[])
        if len(entries)!=1 or entries[0].get('id')!=identifier:raise transfer.TransferError('not_found')
        return cmr.granule(entries[0], collection)
    if collection not in ('landsat-c2-l2','sentinel-2-l2a','sentinel-1-grd'):raise transfer.TransferError('invalid_metadata')
    endpoint='https://stac.dataspace.copernicus.eu/v1' if collection=='sentinel-1-grd' else 'https://earth-search.aws.element84.com/v1'
    raw=await transfer.read_json(endpoint+'/collections/'+collection+'/items/'+identifier)
    if raw.get('id')!=identifier or raw.get('collection')!=collection:raise transfer.TransferError('invalid_metadata')
    return raw


def preview_candidates(raw):
    return [(key,a) for key,a in raw.get('assets',{}).items() if
            any(r in a.get('roles',[]) for r in ('thumbnail','overview','browse','visual')) or
            any(word in key.lower() for word in ('thumbnail','browse'))]


async def resolve(raw,key,reference,preview=False):
    original=raw.get('assets',{}).get(key)
    if not isinstance(original,dict):raise transfer.TransferError('missing_asset' if preview else 'not_found')
    href=original.get('href')
    if not preview and original.get('type','').split(';')[0] not in ('image/tiff','image/vnd.stac.geotiff','image/geotiff','image/jp2','application/zip','application/x-hdf5','application/x-hdf','application/x-netcdf'):
        raise transfer.TransferError('unsupported_format')
    managed=operator.provider_for(reference)
    if preview and managed and operator.enabled(managed):original={**original,'_operator_raw':raw}
    if reference['provider_id']=='copernicus' and not preview:
        if not operator.enabled('cdse'):raise transfer.TransferError('provider_authentication_required')
        return operator.cdse_asset(raw,key),None
    if reference['collection']=='landsat-c2-l2':
        family='ST' if key in ('lwir11','qa','trad','urad','drad','emis','emsd','atran','cdist') else 'SR'
        if preview:family='ST' if landsat.product_id(raw) and '_L2SP_' in landsat.product_id(raw) else 'SR'
        other,source=await landsat.corresponding(raw,family)
        if other:
            alternative=other.get('assets',{}).get(key)
            if alternative and landsat.same_file(original,alternative):
                if operator.enabled('usgs'):alternative={**alternative,'_operator_raw':raw,'operator_provider':'usgs'}
                return alternative,{'product_id':landsat.product_id(raw),'usgs_item_url':source,'correspondence':'exact_product_and_filename'}
        if operator.enabled('usgs'):return {**original,'_operator_raw':raw,'operator_provider':'usgs'},None
        if original.get('storage:requester_pays'):raise transfer.TransferError('requester_pays')
    if original.get('storage:requester_pays'):raise transfer.TransferError('requester_pays')
    if not safe_url(href,('https',)):raise transfer.TransferError('blocked_destination')
    return original,None


async def fetch_asset(request,reference,asset,*,preview=False,probe=False,identity=None):
    if reference['provider_id'] in ('planetary-computer','noaa-nodd'):
        async def receive_public():
            return await public_media.fetch(reference,asset,preview=preview,probe=probe,
                on_bytes=lambda amount:(charge(identity or owner(request),amount),charge('provider:'+reference['provider_id'],amount)))
        if preview:
            async def receive_image():return await receive_public(),None
            # Reuse the bounded, decoded-image single-flight cache. Public-only
            # namespace never adopts an authenticated provider cache entry.
            payload,_=await operator_preview_cache.read(('public',reference['collection'],reference['id'],asset.get('href'),asset.get('_verified_product')),receive_image,image_bytes)
            return payload
        return await receive_public()
    managed=operator.provider_for(reference)
    if managed and operator.enabled(managed):
        if preview:
            try:
                operator.require_product(reference)
                generation=operator.current_generation(managed)
            except transfer.TransferError:generation=None
            # With incomplete settings public paths still work, without sharing
            # authenticated cache entries or adopting unverified credentials.
            if generation is not None:
                key=(managed,reference['collection'],reference['id'],asset.get('href'),generation)
                async def receive():
                    payload=await fetch_operator_asset(request,reference,asset,managed,preview=True,probe=False,identity=identity)
                    return payload,asset.get('_operator_generation')
                payload,used_generation=await operator_preview_cache.read(key,receive,image_bytes)
                if used_generation is not None:
                    if operator.current_generation(managed)!=used_generation:payload.close();raise transfer.TransferError('operator_changed')
                    asset['_operator_generation']=used_generation
                return payload
        return await fetch_operator_asset(request,reference,asset,managed,preview=preview,probe=probe,identity=identity)
    url=asset.get('href','')
    if not safe_url(url,('https',)):raise transfer.TransferError('blocked_destination')
    authenticated=reference['provider_id']=='nasa-cmr' and (not preview or '/lp-prod-protected/' in url)
    token=None
    if authenticated:
        try:token=await auth.access_token(request)
        except auth.AuthenticationRequired:
            _,session=auth._session(request)
            raise transfer.TransferError('earthdata_not_configured' if not auth.settings() else 'reconnection_required' if session else 'login_required') from None
    name=urlsplit(url).path.rsplit('/',1)[-1]
    async def read():
        return await transfer.read(url,max_bytes=transfer.PREVIEW_BYTES if preview else transfer.FILE_BYTES,
            token=token,probe=probe,expected_name=name,
            on_bytes=lambda amount:charge(identity or owner(request),amount))
    try:return await read()
    except transfer.TransferError as e:
        if e.code=='unauthorized' and authenticated:
            try:token=await auth.access_token(request,force_refresh=True,failed_token=token)
            except auth.AuthenticationRequired:raise transfer.TransferError('reconnection_required') from None
            return await read() # at most one renewal/retry; no loop
        raise


async def fetch_operator_asset(request,reference,asset,provider,*,preview,probe,identity):
    url=asset.get('href','');name=asset.get('filename') or urlsplit(url).path.rsplit('/',1)[-1]
    large_sar=provider=='cdse' and reference['collection']=='sentinel-1-grd' and not preview
    file_limit=transfer.CDSE_SAR_FILE_BYTES if large_sar else transfer.FILE_BYTES
    seconds=transfer.CDSE_SAR_SECONDS if large_sar and not probe else transfer.TOTAL_SECONDS
    hourly_limit=CDSE_HOURLY_BYTES if large_sar else HOURLY_BYTES
    async def read(url,token=None,kind='nasa'):
        return await transfer.read(url,max_bytes=transfer.PREVIEW_BYTES if preview else file_limit,token=token,
            probe=probe,expected_name=None if preview else name,credential_provider=kind,provider_scope=provider,
            total_seconds=seconds,on_bytes=lambda amount:(charge(identity or owner(request),amount,hourly_limit),charge('provider:'+provider,amount,hourly_limit)))
    # Authentication is never tried when the original public path already works.
    protected_nasa=provider=='nasa' and reference['collection'] in cmr.hls.COLLECTIONS and '/lp-prod-protected/' in url
    if not protected_nasa and not asset.get('storage:requester_pays') and safe_url(url,('https',)):
        try:return await read(url,kind=provider)
        except transfer.TransferError as error:
            if error.code not in ('unauthorized','permission_required','login_required','usgs_login_required','login_page'):raise
    operator.require_product(reference)
    access,generation=await operator.token(provider)
    async with operator.transfer_scope(provider,[reference['collection'],reference['id'],asset.get('href')]):
        if provider=='usgs':
            raw=asset.get('_operator_raw')
            if raw is None:raise transfer.TransferError('operator_file_unavailable')
            async def resolve_usgs():return await operator.adapters.usgs_preview(raw,access) if preview else await operator.adapters.usgs_file(raw,asset,access)
            try:resolved=await resolve_usgs()
            except transfer.TransferError as error:
                if error.code!='operator_reconnection_required':raise
                access,generation=await operator.token(provider,True,access)
                resolved=await resolve_usgs()
            url=resolved['href'];asset['filename']=resolved['filename'];name=resolved['filename']
            # A USGS M2M session key is NEVER an HTTP Bearer on download hosts.
            access=None
        if provider=='cdse' and preview:
            if not asset.get('_operator_raw'):raise transfer.TransferError('operator_file_unavailable')
            resolved=await operator.cdse_preview(asset['_operator_raw']);url=resolved['href'];name=resolved['filename']
        async def authenticated_read():
            return await transfer.read(url,max_bytes=transfer.PREVIEW_BYTES if preview else file_limit,
                token=access,probe=probe,expected_name=name if provider=='cdse' else None if preview else name,credential_provider=provider,provider_scope=provider,
                total_seconds=seconds,on_bytes=lambda amount:(charge(identity or owner(request),amount,hourly_limit),operator.store().charge(provider,amount)))
        try:payload=await authenticated_read()
        except transfer.TransferError as error:
            if error.code=='unauthorized' and provider!='usgs':
                access,generation=await operator.token(provider,True,access);payload=await authenticated_read()
            else:raise
        if operator.current_generation(provider)!=generation:payload.close();raise transfer.TransferError('operator_changed')
        asset['_operator_generation']=generation
        return payload


def image_bytes(payload):
    try:
        payload.file.seek(0);content=payload.file.read()
        media=('image/png' if content.startswith(b'\x89PNG\r\n\x1a\n') else
               'image/jpeg' if content.startswith(b'\xff\xd8\xff') else
               'image/webp' if content.startswith(b'RIFF') and content[8:12]==b'WEBP' else None)
        if not media:raise ValueError()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',NotGeoreferencedWarning)
            with MemoryFile(content) as memory, memory.open() as image:
                if image.width*image.height>16_000_000 or image.count>4 or image.driver not in ('JPEG','PNG','WEBP'):raise ValueError()
                image.read() # decode with existing rasterio/GDAL; no new image dependency
        return content,media
    except Exception:
        raise transfer.TransferError('invalid_image') from None


def original_header(payload,asset):
    sample=payload.file.read(16);payload.file.seek(0)
    media=asset.get('type','').split(';')[0]
    hdf=sample.startswith(b'\x89HDF\r\n\x1a\n')
    valid=(sample.startswith((b'II*\x00',b'MM\x00*',b'II+\x00',b'MM\x00+')) if media in ('image/tiff','image/vnd.stac.geotiff','image/geotiff') else
           sample.startswith(b'\x00\x00\x00\x0cjP  \r\n\x87\n') if media=='image/jp2' else
           hdf if media=='application/x-hdf5' else
           hdf or sample.startswith(b'\x0e\x03\x13\x01') if media=='application/x-hdf' else
           hdf or sample.startswith((b'CDF\x01',b'CDF\x02')) if media=='application/x-netcdf' else
           sample.startswith(b'PK\x03\x04') if media=='application/zip' else False)
    if not valid:raise transfer.TransferError('invalid_file',payload.status)


def failure(error):
    message=MESSAGES.get(error.code,MESSAGES['provider_error'])
    if error.code=='provider_error' and error.http_status==400:
        message='제공처 파일 서버가 HTTP 400을 반환했습니다. 인증 실패 여부는 확인되지 않았습니다. 미리보기/원본 수신에 성공하지 않았습니다.'
    result={'status':error.code,'message':message,
            'http_status':error.http_status,'access_verified':False}
    if getattr(error,'redirect_host',None):result['redirect_host']=error.redirect_host
    return result


async def pc_landsat_preview(request,reference,raw,identity,original):
    """Public preview only. Never change source selection, original assets or auth."""
    other,source=await landsat.corresponding_pc(raw)
    pc_ref={'provider_id':'planetary-computer','collection':'pc-landsat-c2-l2','id':other['id']}
    candidates=[(k,a) for k,a in preview_candidates(other) if a.get('type','').split(';')[0] in ('image/jpeg','image/png','image/webp')][:2]
    if not candidates:raise transfer.TransferError('missing_asset')
    last=None
    for key,asset in candidates:
        try:
            # Short Landsat Item IDs can survive a processing-date revision.
            # Do not share a rendered URL's cache with another full product.
            asset={**asset,'_verified_product':landsat.product_id(other)}
            payload=await fetch_asset(request,pc_ref,asset,preview=True,identity=identity)
            try:content,media=image_bytes(payload)
            finally:payload.close()
            expires=time.monotonic()+TTL
            ticket=issue(Ticket(identity,reference,key,expires,image=content,media_type=media,filename='planetary-computer-browse'+{'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}[media]))
            product=landsat.product_id(raw)
            return {'status':'available','message':'Planetary Computer 제공 미리보기 · 동일 제품 확인·이미지 전체 수신. 선택 원본의 다운로드 권한/픽셀 QA는 변경하지 않습니다.',
                'http_status':payload.status,'access_verified':True,
                'url':'/api/media/previews/'+ticket,'download_url':'/api/media/previews/'+ticket+'?download=1',
                'receipt_expires_at':int(time.time()+max(0,expires-time.monotonic())),
                'source_asset':key,'source_provider_id':'planetary-computer','source_label':'Planetary Computer 제공 미리보기',
                'source_reference':pc_ref,'source_item_url':source,
                'product_match':{'status':'exact','product_id':product,'platform':other['properties']['platform'],
                    'datetime':other['properties']['datetime'],'processing_level':product.split('_')[1],'collection_version':'02'},
                'original_access':original}
        except transfer.TransferError as error:last=error
    raise last


async def inspect(request:Request,query:InspectRequest):
    same_origin(request);identity=owner(request)
    if not identity:
        return JSONResponse({'error':{'code':'MEDIA_SESSION_REQUIRED','message':'미디어 세션을 다시 준비하세요.'}},status_code=409,headers={'Cache-Control':'no-store'})
    reference=query.model_dump(include={'provider_id','collection','id'})
    result={'reference':reference,'preview':None,'assets':[],
            'limits':{'preview_bytes':transfer.PREVIEW_BYTES,'file_bytes':transfer.CDSE_SAR_FILE_BYTES if reference['collection']=='sentinel-1-grd' else transfer.FILE_BYTES,'seconds':INSPECT_SECONDS,'per_asset_seconds':transfer.TOTAL_SECONDS,'concurrency':2,'ticket_seconds':TTL},
            'notice':'파일 접근 확인과 전체 다운로드 완료는 별개입니다. 미리보기는 픽셀 QA가 아닙니다.'}
    try:
        await enter_when_ready(12 if query.asset_keys else 0)
    except transfer.TransferError as e:
        return JSONResponse({'error':{'code':e.code,'message':MESSAGES[e.code]}},status_code=429,headers={'Cache-Control':'no-store'})
    preview_done=not query.include_preview
    async def process():
        nonlocal preview_done
        raw=await canonical(reference)
        if reference['collection']=='landsat-c2-l2':
            result['landsat']={'product_id':landsat.product_id(raw),'scene_id':raw.get('properties',{}).get('landsat:scene_id'),
                'portal_url':'https://earthexplorer.usgs.gov/',
                'instructions':'Data Sets → Landsat Collection 2 Level-2 → Landsat 8-9 OLI/TIRS. Additional Criteria의 Landsat Product Identifier에 표시된 전체 제품 ID를 입력하세요. USGS 계정은 NASA와 별개입니다.'}
        if query.include_preview:
            candidates=preview_candidates(raw)
            result['preview']=failure(transfer.TransferError('missing_asset'))
            supported=[(k,a) for k,a in candidates if a.get('type','').split(';')[0] in ('image/jpeg','image/png','image/webp')]
            if candidates and not supported:result['preview']=failure(transfer.TransferError('unsupported_format'))
            if supported:
                key,_=supported[0]
                correspondence=None
                try:
                    asset,correspondence=await resolve(raw,key,reference,True)
                    payload=await fetch_asset(request,reference,asset,preview=True,identity=identity)
                    try:content,media=image_bytes(payload)
                    finally:payload.close()
                    op=operator.provider_for(reference) if asset.get('_operator_generation') is not None else None
                    edl=request.cookies.get(auth.SESSION_COOKIE) if not op and reference['provider_id']=='nasa-cmr' and '/lp-prod-protected/' in asset['href'] else None
                    extension={'image/png':'.png','image/jpeg':'.jpg','image/webp':'.webp'}[media]
                    expires=time.monotonic()+TTL
                    ticket=issue(Ticket(identity,reference,key,expires,auth_sid=edl,image=content,media_type=media,filename='provider-browse'+extension,operator_provider=op,operator_generation=asset.get('_operator_generation')))
                    result['preview']={'status':'available','message':'제공처 이미지 전체 수신·형식 확인. 분석 원본/픽셀 QA가 아닙니다.',
                        'http_status':payload.status,
                        'access_verified':True,'url':'/api/media/previews/'+ticket,'download_url':'/api/media/previews/'+ticket+'?download=1',
                        'source_asset':key,'correspondence':correspondence,'receipt_expires_at':int(time.time()+max(0,expires-time.monotonic()))}
                except transfer.TransferError as e:result['preview']={**failure(e),'correspondence':correspondence,
                    'original_status':'requester_pays' if raw['assets'][key].get('storage:requester_pays') else 'metadata_link_present'}
        if query.include_preview and reference['provider_id']=='earth-search' and reference['collection']=='landsat-c2-l2' and result['preview']['status']!='available':
            original=result['preview']
            try:
                result['preview']=await asyncio.wait_for(pc_landsat_preview(request,reference,raw,identity,original),18)
            except (asyncio.TimeoutError,transfer.TransferError) as error:
                if isinstance(error,asyncio.TimeoutError):error=transfer.TransferError('timeout')
                # Preserve the actual original failure; a failed alternate is
                # additional evidence, not a fake success or replacement Item.
                result['preview']={**original,'alternate_preview':{'provider_id':'planetary-computer',**failure(error)}}
        preview_done=True
        for key in dict.fromkeys(query.asset_keys):
            correspondence=None
            try:
                asset,correspondence=await resolve(raw,key,reference)
                payload=await fetch_asset(request,reference,asset,probe=True,identity=identity)
                try:
                    original_header(payload,asset)
                finally:payload.close()
                op=operator.provider_for(reference) if asset.get('_operator_generation') is not None else None
                edl=request.cookies.get(auth.SESSION_COOKIE) if not op and reference['provider_id']=='nasa-cmr' else None
                ticket=issue(Ticket(identity,reference,key,time.monotonic()+TTL,auth_sid=edl,operator_provider=op,operator_generation=asset.get('_operator_generation')))
                result['assets'].append({'key':key,'status':'available','message':'GET 범위 접근 확인. 전체 파일 다운로드는 아직 실행하지 않았습니다.',
                    'size_bytes':payload.total_size,
                    'http_status':payload.status,
                    'access_verified':True,'download_completed':False,'ticket':ticket,'download_url':'/api/media/downloads/'+ticket,'correspondence':correspondence})
            except transfer.TransferError as e:result['assets'].append({'key':key,**failure(e),'correspondence':correspondence})
    try:
        await asyncio.wait_for(process(),INSPECT_SECONDS)
    except asyncio.TimeoutError:
        error=transfer.TransferError('timeout')
        if not preview_done:result['preview']=failure(error)
        done={a['key'] for a in result['assets']}
        result['assets'].extend({'key':key,**failure(error)} for key in query.asset_keys if key not in done)
    except (transfer.TransferError,ValueError,KeyError) as e:
        error=e if isinstance(e,transfer.TransferError) else transfer.TransferError('invalid_metadata')
        result['preview']=failure(error) if query.include_preview else None
        result['assets']=[{'key':key,**failure(error)} for key in query.asset_keys]
    finally:leave()
    response=JSONResponse(result,headers={'Cache-Control':'no-store'})
    response.set_cookie(COOKIE,identity,max_age=3600,httponly=True,samesite='strict',secure=request.url.scheme=='https',path='/api/media')
    return response


def preview_response(request,key,download=False):
    ticket=get_ticket(request,key)
    if ticket.image is None:raise HTTPException(404,'미리보기 자료가 없습니다.')
    headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}
    if download:headers['Content-Disposition']='attachment; filename="'+ticket.filename+'"'
    return Response(ticket.image,media_type=ticket.media_type,headers=headers)


class BoundedStream(StreamingResponse):
    def __init__(self,*args,on_close,seconds=DOWNLOAD_SECONDS,**kwargs):
        super().__init__(*args,**kwargs);self.on_close=on_close;self.seconds=seconds

    async def __call__(self,scope,receive,send):
        try:
            await asyncio.wait_for(super().__call__(scope,receive,send),self.seconds)
        except asyncio.TimeoutError:
            pass  # Client receives an incomplete body, never a successful completion.
        finally:
            try:await self.body_iterator.aclose()
            finally:self.on_close()


async def download(request,key):
    ticket=get_ticket(request,key)
    if ticket.image is not None:raise HTTPException(404,'분석 원본 ticket이 아닙니다.')
    large_sar=ticket.reference['provider_id']=='copernicus' and ticket.reference['collection']=='sentinel-1-grd'
    seconds=transfer.CDSE_SAR_SECONDS if large_sar else INSPECT_SECONDS
    try:await enter_when_ready(12)
    except transfer.TransferError:raise HTTPException(429,MESSAGES['busy']) from None
    handed_off=False
    try:
        async with asyncio.timeout(seconds):
            raw=await canonical(ticket.reference)
            asset,_=await resolve(raw,ticket.key,ticket.reference)
            payload=await fetch_asset(request,ticket.reference,asset,identity=ticket.owner)
        try:
            original_header(payload,asset)
        except BaseException:payload.close();raise
        # Spool the bounded complete upstream file first. Never call HEAD a download.
        ticket.filename=re.sub(r'[^A-Za-z0-9_.-]','_',asset.get('filename') or urlsplit(asset['href']).path.rsplit('/',1)[-1])[:180]
        closed=False
        def finish():
            nonlocal closed
            if not closed:
                closed=True;payload.close();leave()
        async def chunks():
            try:
                while chunk:=payload.file.read(65536):yield chunk
                ticket.completed=True
            finally:finish()
        response=BoundedStream(chunks(),on_close=finish,seconds=transfer.CDSE_SAR_CLIENT_SECONDS if large_sar else DOWNLOAD_SECONDS,media_type='application/octet-stream',headers={
            'Content-Disposition':'attachment; filename="'+ticket.filename+'"','Content-Length':str(payload.size),
            'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
        handed_off=True
        return response
    except asyncio.TimeoutError:
        return JSONResponse({'error':failure(transfer.TransferError('timeout'))},status_code=504,headers={'Cache-Control':'no-store'})
    except transfer.TransferError as e:
        return JSONResponse({'error':failure(e)},status_code=413 if e.code=='size_limit' else 401 if e.code in ('login_required','reconnection_required') else 502,headers={'Cache-Control':'no-store'})
    finally:
        if not handed_off:leave()


def download_status(request,key):
    ticket=get_ticket(request,key)
    return JSONResponse({'download_completed':ticket.completed,
        'scope':'서버 응답 스트림 완료 여부. 브라우저 파일 저장은 별도 확인하세요.'},headers={'Cache-Control':'no-store'})
