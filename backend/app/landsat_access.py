"""Exact USGS correspondence. Never convert requester-pays S3 URLs into public URLs."""
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, unquote, quote
from .provider_transfer import read_json, TransferError

USGS = 'https://landsatlook.usgs.gov/stac-server'
PRODUCT = re.compile(r'^LC0[89]_L2(?:SP|SR)_\d{6}_\d{8}_\d{8}_02_T[12]$')
ITEM = re.compile(r'^LC0[89]_L2(?:SP|SR)_\d{6}_\d{8}_02_T[12]$')


def product_id(raw):
    candidates=set()
    for asset in (raw.get('assets') or {}).values():
        href=asset.get('href','')
        if not isinstance(href,str):continue
        for part in unquote(urlsplit(href).path).split('/'):
            if PRODUCT.fullmatch(part):candidates.add(part)
    return candidates.pop() if len(candidates)==1 else None


def matching(raw, other, product, family):
    p,q=raw.get('properties',{}),other.get('properties',{})
    try:
        platform=lambda value: str(value).lower().replace('_','-')
        captured=lambda value:datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(timezone.utc)
        level=product.split('_')[1]
        return (other.get('id')==product+'_'+family and
                other.get('collection')=='landsat-c2l2-'+family.lower() and
                platform(p.get('platform'))==platform(q.get('platform')) and
                captured(p['datetime'])==captured(q['datetime']) and
                str(p.get('landsat:collection_number'))==str(q.get('landsat:collection_number'))=='02' and
                (p.get('landsat:correction') or p.get('processing:level') or p.get('landsat:processing_level'))==level and
                q.get('landsat:correction')==level and
                p.get('landsat:scene_id')==q.get('landsat:scene_id') and bool(p.get('landsat:scene_id')))
    except (ValueError,TypeError,KeyError,AttributeError):return False


async def corresponding(raw, family):
    product=product_id(raw)
    if not product:return None,None
    url=f'{USGS}/collections/landsat-c2l2-{family.lower()}/items/{product}_{family}'
    other=await read_json(url)
    if not matching(raw,other,product,family):raise TransferError('product_mismatch')
    return other,url


def same_file(original,alternate):
    # Identical basename/full product prefix is necessary; differing checksums fail.
    a,b=original.get('href',''),alternate.get('href','')
    if unquote(urlsplit(a).path).rsplit('/',1)[-1]!=unquote(urlsplit(b).path).rsplit('/',1)[-1]:return False
    ca,cb=original.get('file:checksum'),alternate.get('file:checksum')
    return not (ca and cb and ca!=cb)


def matching_pc(raw, other):
    """Same reviewed product, not a claim of identical preview or band bytes."""
    product=product_id(raw)
    if not product or product_id(other)!=product:return False
    p,q=raw.get('properties',{}),other.get('properties',{})
    try:
        a=datetime.fromisoformat(p['datetime'].replace('Z','+00:00'))
        b=datetime.fromisoformat(q['datetime'].replace('Z','+00:00'))
        fields=product.split('_')
        return (raw.get('collection')=='landsat-c2-l2' and
                other.get('collection') in ('landsat-c2-l2','pc-landsat-c2-l2') and
                ITEM.fullmatch(str(raw.get('id',''))) is not None and other.get('id')==raw['id'] and
                p.get('platform')==q.get('platform')=='landsat-'+str(int(fields[0][2:])) and
                a.tzinfo is not None and b.tzinfo is not None and a==b and a.astimezone(timezone.utc).strftime('%Y%m%d')==fields[3] and
                str(p.get('landsat:collection_number'))==str(q.get('landsat:collection_number'))==fields[5]=='02' and
                p.get('landsat:correction')==q.get('landsat:correction')==fields[1] and
                p.get('landsat:scene_id')==q.get('landsat:scene_id') and bool(p.get('landsat:scene_id')))
    except (ValueError,TypeError,KeyError,AttributeError):return False


async def corresponding_pc(raw):
    # PC's published Item ID omits the processing date. The full product identity
    # MUST therefore be checked from canonical asset paths, never Item ID alone.
    from . import planetary
    if not product_id(raw) or not ITEM.fullmatch(str(raw.get('id',''))):raise TransferError('product_mismatch')
    url=planetary.ENDPOINT+'/collections/landsat-c2-l2/items/'+quote(raw['id'],safe='')
    other=await read_json(url)
    if not matching_pc(raw,other):raise TransferError('product_mismatch')
    return planetary.feature(other),url
