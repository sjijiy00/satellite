"""Bounded, allowlisted provider reads. No caller supplied URL and no redirect credentials."""
import asyncio
import ipaddress
import json
import socket
import time
import re
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from tempfile import SpooledTemporaryFile
from urllib.parse import urlsplit, urljoin, unquote

import httpx

MAX_REDIRECTS = 4
TOTAL_SECONDS = 35
PREVIEW_BYTES = 8 * 1024**2
FILE_BYTES = 256 * 1024**2
CDSE_SAR_FILE_BYTES = 2 * 1024**3
CDSE_SAR_SECONDS = 20 * 60
CDSE_SAR_CLIENT_SECONDS = 5 * 60
JSON_BYTES = 2 * 1024**2
ALLOWED = {
 'earth-search.aws.element84.com': ('/v1/collections/',),
 'cmr.earthdata.nasa.gov': ('/search/granules.json',),
 'landsatlook.usgs.gov': ('/stac-server/collections/','/data/collection02/','/gen-browse','/browse/'),
 'data.lpdaac.earthdatacloud.nasa.gov': ('/lp-prod-public/VNP09GA.002/','/lp-prod-protected/VNP09GA.002/'),
 'd1nklfio7vscoe.cloudfront.net': ('/s3-',),
 'sentinel-cogs.s3.us-west-2.amazonaws.com': ('/sentinel-s2-l2a-cogs/',),
 'roda.sentinel-hub.com': ('/sentinel-s2-l2a/',),
 'datahub.creodias.eu': ('/odata/v1/Assets(',),
 'zipper.creodias.eu': ('/odata/v1/Assets(',),
 'stac.dataspace.copernicus.eu': ('/v1/collections/sentinel-1-grd/items/',),
 'download.dataspace.copernicus.eu': ('/odata/v1/Products(',),
 'landsat.usgs.gov': ('/','/landsat/'),
 'landsatdownload.usgs.gov': ('/',),
}
ALLOWED.update({
 'planetarycomputer.microsoft.com':('/api/stac/v1/collections/','/api/data/v1/item/preview.png'),
 'landsateuwest.blob.core.windows.net':('/landsat-c2/',),
 **{f'sentinel2l2a{i:02}.blob.core.windows.net':('/sentinel2-l2/',) for i in range(1,6)},
 'noaa-cdr-ndvi-pds.s3.amazonaws.com':('/data/',),
})
AUTH_HOST = 'data.lpdaac.earthdatacloud.nasa.gov'
AUTH_REQUIRED_HOSTS = {'ers.cr.usgs.gov':'usgs_login_required', 'urs.earthdata.nasa.gov':'login_required'}
OPERATOR_HOSTS={
 'nasa':{'data.lpdaac.earthdatacloud.nasa.gov','d1nklfio7vscoe.cloudfront.net'},
 'cdse':{'download.dataspace.copernicus.eu','datahub.creodias.eu','zipper.creodias.eu'},
 'usgs':{'landsatlook.usgs.gov','landsatdownload.usgs.gov','landsat.usgs.gov'},
}
OPERATOR_HOSTS['planetary-computer']={'planetarycomputer.microsoft.com','landsateuwest.blob.core.windows.net',*(f'sentinel2l2a{i:02}.blob.core.windows.net' for i in range(1,6))}
OPERATOR_HOSTS['noaa-nodd']={'noaa-cdr-ndvi-pds.s3.amazonaws.com'}
NASA_PRODUCTS=('VNP09GA.002','HLSL30.020','HLSS30.020')
ALLOWED[AUTH_HOST]=tuple('/'+bucket+'/'+product+'/' for bucket in ('lp-prod-public','lp-prod-protected') for product in NASA_PRODUCTS)

# Explicit local diagnostics only: never emitted to HTTP responses or loggers.
# ContextVar isolates concurrent requests, including TestClient worker threads.
_diagnostics = ContextVar('provider_transfer_diagnostics', default=None)


@contextmanager
def diagnostics(records):
    marker = _diagnostics.set(records)
    try: yield
    finally: _diagnostics.reset(marker)


def diagnostic_target(url):
    """Never include a query, userinfo, Location header or arbitrary URL path."""
    try:
        u = urlsplit(url)
        host = u.hostname if u.hostname in ALLOWED or u.hostname in AUTH_REQUIRED_HOSTS else '[blocked]'
        path = '[redacted]'
        # These product identifiers/filenames are public CMR metadata. All other
        # paths (especially login/redirect paths) are deliberately hidden.
        if host == AUTH_HOST and re.fullmatch(
            r'/lp-prod-(?:public|protected)/HLS[LS]30\.020/'
            r'HLS\.[LS]30\.T[0-9A-Z]{5}\.\d{7}T\d{6}\.v2\.0/'
            r'HLS\.[LS]30\.T[0-9A-Z]{5}\.\d{7}T\d{6}\.v2\.0\.(?:jpg|(?:B\d{2}|B8A|Fmask|SAA|SZA|VAA|VZA)\.tif)', u.path):
            path = u.path
        return {'host': host, 'path': path}
    except ValueError:
        return {'host': '[blocked]', 'path': '[redacted]'}


def diagnostic_event(url, **fields):
    records = _diagnostics.get()
    if records is not None and len(records) < 64:
        records.append({**diagnostic_target(url), **fields})


def response_facts(response):
    media = response.headers.get('content-type', '').split(';')[0].strip().lower()
    if media not in ('application/json','application/xml','text/xml','text/html','application/xhtml+xml',
                     'image/tiff','image/jpeg','image/png','image/webp','application/octet-stream','text/plain'):
        media = 'other' if media else None
    length = response.headers.get('content-length', '')
    content_range = response.headers.get('content-range', '')
    return {'status': response.status_code, 'content_type': media,
            'declared_bytes': int(length) if length.isdigit() and len(length)<20 else None,
            'content_range': content_range if re.fullmatch(r'bytes \d+-\d+/\d+',content_range) else None}


class TransferError(Exception):
    def __init__(self, code, http_status=None, redirect_host=None):
        self.code, self.http_status = code, http_status
        self.redirect_host=redirect_host if redirect_host in AUTH_REQUIRED_HOSTS else None


async def public_dns(host):
    records = await asyncio.wait_for(asyncio.to_thread(socket.getaddrinfo, host, 443, type=socket.SOCK_STREAM), 3)
    if not records or any(not ipaddress.ip_address(r[4][0]).is_global for r in records):
        raise TransferError('blocked_destination')


async def validate_destination(url, expected_name=None):
    try:
        u = urlsplit(url)
        if u.scheme!='https' or u.port not in (None,443) or u.username or u.password or u.fragment:
            raise TransferError('blocked_destination')
        if u.hostname in AUTH_REQUIRED_HOSTS:
            raise TransferError(AUTH_REQUIRED_HOSTS[u.hostname])
        path = unquote(u.path)
        if u.hostname not in ALLOWED or not any(path.startswith(p) for p in ALLOWED[u.hostname]) or '/..' in path or '\\' in path:
            raise TransferError('blocked_destination')
        if u.hostname=='d1nklfio7vscoe.cloudfront.net':
            parts=path.split('/')
            if len(parts)<6 or parts[2] not in ('lp-prod-public.s3.us-west-2.amazonaws.com','lp-prod-protected.s3.us-west-2.amazonaws.com') or parts[3] not in NASA_PRODUCTS:
                raise TransferError('blocked_destination')
        if expected_name and path.rsplit('/',1)[-1] != expected_name:
            raise TransferError('redirect_item_mismatch')
        await public_dns(u.hostname)
        return u
    except (ValueError, OSError):
        raise TransferError('blocked_destination') from None


@dataclass(repr=False)
class Payload:
    file: object
    size: int
    media_type: str
    complete: bool
    status: int
    total_size: int | None = None

    def close(self): self.file.close()


def response_error(response, sample):
    if response.status_code==401: return 'unauthorized'
    if response.status_code==403:
        # Generic 403 cannot prove whether the cause is EULA, app approval or ACL.
        try: code = json.loads(sample).get('error','')
        except (ValueError, AttributeError): code = ''
        if code in ('eula_required','application_authorization_required'): return code
        return 'permission_required'
    if response.status_code in (404,410):return 'not_found'
    if response.status_code==429:return 'provider_busy'
    return 'provider_error'


async def read(url, *, max_bytes, token=None, probe=False, expected_name=None, on_bytes=None, credential_provider='nasa',provider_scope=None,allowed_origin=None,total_seconds=None):
    """Return bytes/file only. Never return or log final/signed Location URLs."""
    if total_seconds is None:total_seconds=TOTAL_SECONDS
    async def run():
        started = time.monotonic()
        file = SpooledTemporaryFile(max_size=8*1024**2)
        try:
            current, credential_host, current_token = url, urlsplit(url).hostname, token
            async with httpx.AsyncClient(follow_redirects=False, trust_env=False) as client:
                for hop in range(MAX_REDIRECTS+1):
                    diagnostic_event(current, stage='validate', hop=hop, range_requested=probe,
                                     authorization_present=False)
                    symbolic=hop==0 and credential_provider=='cdse' and urlsplit(current).hostname=='download.dataspace.copernicus.eu' and urlsplit(current).path.endswith('/$value')
                    u = await validate_destination(current, None if symbolic else expected_name)
                    if provider_scope and u.hostname not in OPERATOR_HOSTS.get(provider_scope,set()):raise TransferError('blocked_destination')
                    if allowed_origin and (u.hostname!=allowed_origin[0] or not u.path.startswith(allowed_origin[1])):raise TransferError('blocked_redirect')
                    headers = {'Accept-Encoding':'identity'}
                    if probe: headers['Range']='bytes=0-1023'
                    auth_host=AUTH_HOST if credential_provider=='nasa' else 'download.dataspace.copernicus.eu' if credential_provider=='cdse' else None
                    if current_token and u.hostname==auth_host and u.hostname==credential_host:
                        headers['Authorization']='Bearer '+current_token
                    diagnostic_event(current, stage='request', hop=hop, range_requested=probe,
                                     authorization_present='Authorization' in headers)
                    remaining = total_seconds-(time.monotonic()-started)
                    if remaining<=0:raise TransferError('timeout')
                    async with client.stream('GET',current,headers=headers,timeout=httpx.Timeout(min(15,remaining),connect=5)) as r:
                        diagnostic_event(current, stage='response', hop=hop, range_requested=probe,
                                         authorization_present='Authorization' in headers, **response_facts(r))
                        if r.status_code in (301,302,303,307,308):
                            location = r.headers.get('location')
                            if not location or len(location)>8192:raise TransferError('blocked_redirect')
                            new = urljoin(current,location)
                            diagnostic_event(new,stage='redirect',hop=hop,status=r.status_code)
                            auth_reason=AUTH_REQUIRED_HOSTS.get(urlsplit(new).hostname)
                            if auth_reason:raise TransferError(auth_reason,r.status_code,urlsplit(new).hostname)
                            if urlsplit(new).hostname != u.hostname:
                                # Strip permanently after the first cross-host redirect.
                                current_token = None
                            current = new
                            continue
                        if r.status_code not in (200,206):
                            sample=bytearray()
                            async for chunk in r.aiter_bytes():
                                sample.extend(chunk[:2048-len(sample)])
                                if len(sample)>=2048:break
                            diagnostic_event(current, stage='error_body', hop=hop, sampled_bytes=len(sample),
                                             code=response_error(r,bytes(sample)))
                            raise TransferError(response_error(r,bytes(sample)),r.status_code)
                        length = r.headers.get('content-length')
                        range_header = r.headers.get('content-range','')
                        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', range_header)
                        if r.status_code == 206:
                            if not probe:raise TransferError('incomplete_transfer',r.status_code)
                            if not match:raise TransferError('invalid_content_range',r.status_code)
                            start,end,total = map(int,match.groups())
                            if start != 0 or not start <= end < total or (length and length.isdigit() and int(length) != end-start+1):
                                raise TransferError('invalid_content_range',r.status_code)
                        else:
                            total = int(length) if length and length.isdigit() else None
                        if total is not None and total>max_bytes:raise TransferError('size_limit')
                        size=0
                        async for chunk in r.aiter_bytes():
                            if on_bytes:on_bytes(len(chunk))
                            if probe:
                                chunk=chunk[:1024-size]
                            size+=len(chunk)
                            if size>max_bytes:raise TransferError('size_limit')
                            file.write(chunk)
                            if probe and size>=1024:break
                        if size==0:raise TransferError('empty_file')
                        media=r.headers.get('content-type','').split(';')[0].lower()
                        if media in ('text/html','application/xhtml+xml'):raise TransferError('login_page',r.status_code)
                        complete=not probe and r.status_code==200 and (total is None or total==size)
                        if not probe and not complete:raise TransferError('incomplete_transfer')
                        file.seek(0)
                        diagnostic_event(current, stage='received', hop=hop, received_bytes=size,
                                         complete=complete, range_requested=probe)
                        return Payload(file,size,media,complete,r.status_code,total)
                raise TransferError('redirect_limit')
        except BaseException as error:
            if isinstance(error,TransferError):
                diagnostic_event(current,stage='stopped',code=error.code,http_status=error.http_status)
            file.close()
            raise
    try:
        return await asyncio.wait_for(run(),total_seconds)
    except (httpx.TimeoutException,asyncio.TimeoutError):
        raise TransferError('timeout') from None
    except httpx.HTTPError:
        raise TransferError('network_error') from None


async def read_json(url):
    payload=await read(url,max_bytes=JSON_BYTES)
    try:
        value=json.load(payload.file)
        if not isinstance(value,dict):raise ValueError()
        return value
    except ValueError:
        raise TransferError('invalid_metadata') from None
    finally:payload.close()
