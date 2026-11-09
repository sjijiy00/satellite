"""Anonymous public file access. SAS is internal, short-lived and never a link API."""
from urllib.parse import urlsplit,parse_qs
from . import planetary,provider_transfer as transfer
from .provider_registry import COLLECTION_REGISTRY
from .safe_urls import safe_url

active_files=set()


async def fetch(reference,asset,*,preview=False,probe=False,on_bytes=None):
    key=(reference['provider_id'],reference['collection'],reference['id'],asset.get('href'))
    if not preview and not probe:
        if key in active_files:raise transfer.TransferError('busy')
        active_files.add(key)
    try:return await _fetch(reference,asset,preview=preview,probe=probe,on_bytes=on_bytes)
    finally:
        if not preview and not probe:active_files.discard(key)


async def _fetch(reference,asset,*,preview=False,probe=False,on_bytes=None):
    url=asset.get('href','')
    if not safe_url(url,('https',)):raise transfer.TransferError('blocked_destination')
    if asset.get('storage:requester_pays'):raise transfer.TransferError('requester_pays')
    limit=transfer.PREVIEW_BYTES if preview else transfer.FILE_BYTES
    if isinstance(asset.get('file:size'),int) and asset['file:size']>limit:raise transfer.TransferError('size_limit')
    u=urlsplit(url);provider=reference['provider_id'];name=u.path.rsplit('/',1)[-1]
    async def read(target,origin):
        return await transfer.read(target,max_bytes=limit,probe=probe,expected_name=None if preview else name,
            provider_scope=provider,allowed_origin=origin,on_bytes=on_bytes)
    if provider=='noaa-nodd':return await read(url,('noaa-cdr-ndvi-pds.s3.amazonaws.com','/data/'))
    if provider!='planetary-computer':raise transfer.TransferError('blocked_destination')
    if u.hostname=='planetarycomputer.microsoft.com':
        params=parse_qs(u.query);remote=COLLECTION_REGISTRY[reference['collection']]['remote_id']
        if not preview or u.path!='/api/data/v1/item/preview.png' or params.get('collection')!=[remote] or params.get('item')!=[reference['id']]:raise transfer.TransferError('blocked_destination')
        return await read(url,(u.hostname,'/api/data/v1/item/preview.png'))
    account,container=planetary.storage(reference['collection'],url)
    signed,token=await planetary.signed(reference['collection'],url)
    try:return await read(signed,(u.hostname,'/'+container+'/'))
    except transfer.TransferError as error:
        if error.code not in ('unauthorized','permission_required'):raise
        signed,_=await planetary.signed(reference['collection'],url,True,token)
        return await read(signed,(u.hostname,'/'+container+'/')) # one renewal, no loop
