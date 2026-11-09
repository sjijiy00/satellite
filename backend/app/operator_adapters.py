"""Issuer-specific protocols. No arbitrary auth URL, raw error or token logging."""
import asyncio
from datetime import datetime,timezone
import json
import time
from urllib.parse import urlsplit,unquote,parse_qs
import httpx
from .provider_transfer import TransferError

M2M='https://m2m.cr.usgs.gov/api/api/json/stable/'
CDSE='https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token'
NASA='https://urs.earthdata.nasa.gov/api/users/renew_token'


async def request(url,*,body=None,form=None,headers=None):
    from . import operator_access as operator
    provider='usgs' if url.startswith(M2M) else 'cdse' if url==CDSE else 'nasa' if url==NASA else None
    if provider is None:raise TransferError('blocked_destination')
    if operator.enabled(provider):operator.store().count_request(provider)
    try:
        async with asyncio.timeout(12),httpx.AsyncClient(follow_redirects=False,trust_env=False,timeout=8) as client:
            async with client.stream('POST',url,json=body,data=form,headers=headers or {}) as response:
                # USGS can return an HTML 403 for a missing M2M role. Classify
                # the HTTP refusal before attempting to decode a JSON body.
                if response.status_code==401:raise TransferError('operator_reconnection_required')
                if response.status_code==403:raise TransferError('operator_permission_denied')
                if response.status_code==429:raise TransferError('operator_quota')
                if response.status_code>=500:raise TransferError('operator_provider_error')
                raw=bytearray()
                async for chunk in response.aiter_bytes():
                    raw.extend(chunk)
                    if len(raw)>2*1024**2:raise TransferError('operator_invalid_response')
                try:data=json.loads(raw)
                except ValueError:raise TransferError('operator_invalid_response') from None
                if not isinstance(data,dict):raise TransferError('operator_invalid_response')
                code=str(data.get('error') or data.get('errorCode') or '').lower()
                description=str(data.get('error_description') or '').lower()
                if 'totp' in description or '2fa' in description or code in ('mfa_required','interaction_required'):raise TransferError('operator_mfa_required')
                if response.status_code==401 or code in ('invalid_grant','authentication_failed','auth_invalid','api_key_invalid'):raise TransferError('operator_reconnection_required')
                if response.status_code==403:raise TransferError('operator_permission_denied')
                if response.status_code==429:raise TransferError('operator_quota')
                if response.status_code!=200 or code:raise TransferError('operator_provider_error')
                return data
    except (httpx.TimeoutException,TimeoutError):raise TransferError('operator_timeout') from None
    except httpx.HTTPError:raise TransferError('operator_provider_error') from None


def secret(value):
    if not isinstance(value,str) or not 8<=len(value)<=16384 or any(c.isspace() for c in value):raise TransferError('operator_invalid_response')
    return value


def nasa_grant(data):
    try:expires=datetime.strptime(data['expiration_date'],'%m/%d/%Y').replace(tzinfo=timezone.utc).timestamp()
    except (KeyError,TypeError,ValueError):raise TransferError('operator_invalid_response') from None
    if expires<=time.time()+60 or expires>time.time()+61*86400:raise TransferError('operator_expired')
    return {'access':secret(data.get('access_token')),'expires':expires}


async def renew(provider,current,config):
    if provider=='nasa':
        # A User Token renewal is NOT an OAuth refresh-token grant.
        return nasa_grant(await request(NASA,headers={'Authorization':'Bearer '+secret(current['access'])}))
    if provider=='cdse':
        if current.get('refresh'):
            form={'client_id':'cdse-public','grant_type':'refresh_token','refresh_token':current['refresh']}
        else:form={'client_id':'cdse-public','grant_type':'password','username':config['username'],'password':config['password']}
        data=await request(CDSE,form=form)
        try:seconds=int(data['expires_in'])
        except (KeyError,TypeError,ValueError):raise TransferError('operator_invalid_response') from None
        if not 60<=seconds<=86400:raise TransferError('operator_invalid_response')
        return {'access':secret(data.get('access_token')),'refresh':secret(data.get('refresh_token')),'expires':time.time()+seconds}
    data=await request(M2M+'login-token',body={'username':config['username'],'token':config['application_token']})
    return {'access':secret(data.get('data')),'expires':time.time()+900}


async def m2m(method,body,token):
    return (await request(M2M+method,body=body,headers={'X-Auth-Token':token})).get('data')


async def usgs_file(raw,asset,token):
    """Exact C2 L2 individual file only; never substitute a bundle or a new version."""
    from .landsat_access import product_id
    product=product_id(raw);filename=unquote(urlsplit(asset.get('href','')).path).rsplit('/',1)[-1]
    if not product or not filename.startswith(product+'_') or not filename.lower().endswith(('.tif','.tiff')):raise TransferError('product_mismatch')
    # No guessed dataset filter IDs; resolve the exact display ID via a bounded list.
    return await exact_display_scene(product,filename,token)


async def exact_usgs_scene(product,token):
    # scene-list-get returns entityId without displayId. The official
    # scene-metadata endpoint accepts one displayId and returns the exact pair.
    row=await m2m('scene-metadata',{'datasetName':'landsat_ot_c2_l2','entityId':product,
                                  'idType':'displayId','metadataType':'full','useCustomization':False},token)
    if not isinstance(row,dict) or row.get('displayId')!=product or not isinstance(row.get('entityId'),str):
        raise TransferError('product_mismatch')
    return row


async def exact_display_scene(product,filename,token):
    import secrets
    label='satellite-'+secrets.token_hex(8)
    row=await exact_usgs_scene(product,token)
    options=await m2m('download-options',{'datasetName':'landsat_ot_c2_l2','entityIds':[row['entityId']]},token)
    if not isinstance(options,list):raise TransferError('operator_invalid_response')
    candidates={}
    for option in options or []:
        if not isinstance(option,dict) or not isinstance(option.get('secondaryDownloads',[]),list):raise TransferError('operator_invalid_response')
        for item in option.get('secondaryDownloads',[]):
            if not isinstance(item,dict):raise TransferError('operator_invalid_response')
            if item.get('available') is True and item.get('displayId') in (filename,filename.rsplit('.',1)[0]):
                # The same band is repeated under bundle and band-file options.
                # Deduplicate only the exact provider identity, never filenames alone.
                identity=(item.get('entityId'),item.get('id'))
                if not all(isinstance(v,str) and v for v in identity):raise TransferError('operator_invalid_response')
                previous=candidates.get(identity)
                if previous and any(previous.get(k) is not None and item.get(k) is not None and previous[k]!=item[k] for k in ('checksum','filesize')):
                    raise TransferError('product_mismatch')
                candidates[identity]={**(previous or {}),**{k:v for k,v in item.items() if v is not None}}
    if len(candidates)!=1:raise TransferError('operator_file_unavailable')
    item=next(iter(candidates.values()))
    response=await m2m('download-request',{'downloads':[{'entityId':item['entityId'],'productId':item['id']}],'label':label},token)
    ready=response.get('availableDownloads',[]) if isinstance(response,dict) else []
    if not isinstance(ready,list) or any(not isinstance(item,dict) for item in ready):raise TransferError('operator_invalid_response')
    if not ready:raise TransferError('operator_preparing') # bounded, no polling loop
    if len(ready)!=1:raise TransferError('product_mismatch')
    url=ready[0].get('url','')
    if urlsplit(url).scheme!='https' or urlsplit(url).hostname not in ('landsatlook.usgs.gov','landsatdownload.usgs.gov','landsat.usgs.gov'):raise TransferError('blocked_destination')
    if filename!=unquote(urlsplit(url).path).rsplit('/',1)[-1]:raise TransferError('product_mismatch')
    return {**item,'href':url,'type':'image/tiff','filename':filename}


async def usgs_preview(raw,token):
    """Only a browse explicitly returned for the exact M2M product; no fake RGB."""
    from .landsat_access import product_id
    product=product_id(raw)
    if not product:raise TransferError('product_mismatch')
    row=await exact_usgs_scene(product,token)
    if not isinstance(row.get('browse',[]),list):raise TransferError('operator_invalid_response')
    for browse in row.get('browse',[]):
        if not isinstance(browse,dict):raise TransferError('operator_invalid_response')
        url=browse.get('browsePath') or browse.get('browseUrl')
        if not isinstance(url,str):continue
        u=urlsplit(url);query=parse_qs(u.query);path=unquote(u.path)
        linked=product in path.split('/') or path.rsplit('/',1)[-1].startswith(product+'_') or query.get('product_id')==[product]
        if u.scheme=='https' and u.hostname in ('landsatlook.usgs.gov','landsat.usgs.gov') and linked:
            return {'href':url,'type':'image/jpeg','filename':product+'_browse.jpg'}
    raise TransferError('operator_file_unavailable')
