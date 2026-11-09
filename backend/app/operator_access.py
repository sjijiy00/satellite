"""Opt-in operator access, separate from visitor Earthdata OAuth.

Only reviewed products are enabled. Issuer authentication does not confer
redistribution rights; an explicit per-product policy acknowledgement is required.
"""
import asyncio
from contextlib import asynccontextmanager
import os
import multiprocessing
import math
import re
import secrets
import time
from urllib.parse import urlsplit,unquote,quote
from . import operator_adapters as adapters
from .operator_store import Store,fingerprint
from .provider_transfer import TransferError

PRODUCTS={'landsat-c2-l2':('usgs','earth-search'),'sentinel-1-grd':('cdse','copernicus'),'viirs-vnp09ga-002':('nasa','nasa-cmr')}
from .hls import COLLECTIONS as HLS_COLLECTIONS
PRODUCTS.update({key:('nasa','nasa-cmr') for key in HLS_COLLECTIONS})
FIELDS={'usgs':('USERNAME','APPLICATION_TOKEN'),'cdse':('USERNAME','PASSWORD','REFRESH_TOKEN'),'nasa':('USER_TOKEN','TOKEN_EXPIRES_AT')}
_locks={}
_store=None


def enabled(provider):return os.getenv('OPERATOR_ACCESS_ENABLED')=='1' and os.getenv('OPERATOR_'+provider.upper()+'_ENABLED')=='1'


def provider_for(reference):
    row=PRODUCTS.get(reference.get('collection'))
    return row[0] if row and row[1]==reference.get('provider_id') else None


def require_product(reference):
    """Do not silently expand a previous VIIRS-only redistribution acknowledgement."""
    if provider_for(reference)!='nasa':return
    allowed={v.strip() for v in os.getenv('OPERATOR_NASA_COLLECTIONS','viirs-vnp09ga-002').split(',')}
    if reference['collection'] not in allowed:raise TransferError('operator_product_not_enabled')
    if reference['collection'] in HLS_COLLECTIONS and os.getenv('OPERATOR_NASA_HLS_REDISTRIBUTION_REVIEWED')!='1':
        raise TransferError('operator_policy_not_reviewed')


def store():
    global _store
    if _store is None:_store=Store()
    return _store


def config(provider):
    prefix='OPERATOR_'+provider.upper()+'_'
    values={name.lower():(os.getenv(prefix+name,'') if name=='PASSWORD' else os.getenv(prefix+name,'').strip()) for name in FIELDS[provider]}
    resume_stored=provider=='nasa' and not values['user_token'] and os.getenv('OPERATOR_NASA_RESUME_STORED_GRANT')=='1'
    missing=[] if resume_stored else missing_fields(provider,values)
    if os.getenv(prefix+'REDISTRIBUTION_REVIEWED')!='1':missing.append(prefix+'REDISTRIBUTION_REVIEWED')
    try:revision=int(os.getenv(prefix+'REVISION','1'))
    except ValueError:revision=0
    if revision<1:missing.append(prefix+'REVISION')
    if os.getenv('WEB_CONCURRENCY','1')!='1' or os.getenv('OPERATOR_WORKERS','1')!='1' or multiprocessing.current_process().name!='MainProcess':raise TransferError('operator_multiworker_unsupported')
    if missing:raise TransferError('operator_not_ready')
    fp=store().existing_fingerprint(provider,revision) if resume_stored else fingerprint({k:v for k,v in values.items() if k!='token_expires_at'})
    return values,revision,fp


def missing_fields(provider,values):
    names=FIELDS[provider]
    if provider=='cdse':names=() if values.get('refresh_token') else ('USERNAME','PASSWORD')
    return ['OPERATOR_'+provider.upper()+'_'+k for k in names if not values.get(k.lower())]


def seed(provider,values):
    if provider=='nasa':
        if not values['user_token']:return None # existing encrypted grant only
        try:expires=float(values['token_expires_at'])
        except ValueError:raise TransferError('operator_not_ready') from None
        if not math.isfinite(expires) or not 0<expires<=time.time()+61*86400:raise TransferError('operator_not_ready')
        return {'access':adapters.secret(values['user_token']),'expires':expires}
    return {'access':None,'expires':0,**({'refresh':values.get('refresh_token') or None} if provider=='cdse' else {})}


async def token(provider,force=False,failed_token=None):
    if not enabled(provider):raise TransferError('operator_disabled')
    lock=_locks.setdefault(provider,asyncio.Lock())
    async with lock:
        values,revision,fp=config(provider)
        row=store().load(provider,revision,fp,seed(provider,values))
        if row['state']!='active':raise TransferError('operator_'+('reconnection_required' if row['state']=='renewing' else row['state']))
        if row.get('access') and row.get('expires',0)>time.time()+300 and (not force or failed_token and row['access']!=failed_token):return row['access'],row['generation']
        if provider=='nasa' and row.get('expires',0)<=time.time():
            store().change(provider,row['generation'],'expired');raise TransferError('operator_expired')
        # Commit the indeterminate state first. If the issuer rotates successfully
        # but the process/write fails, a restart requires operator intervention.
        generation=store().change(provider,row['generation'],'renewing')
        try:
            grant=await adapters.renew(provider,row,values)
            generation=store().change(provider,generation,'active',grant)
            return grant['access'],generation
        except TransferError as error:
            state=error.code.removeprefix('operator_')
            store().change(provider,generation,state if state in ('expired','reconnection_required','mfa_required','permission_denied') else 'reconnection_required')
            raise


def current_generation(provider):
    values,revision,fp=config(provider)
    row=store().load(provider,revision,fp,seed(provider,values))
    if row['state']!='active':raise TransferError('operator_'+row['state'])
    return row['generation']


def public_status(provider):
    # Deliberately no setting names, account identity, fingerprint or admin action.
    state='not_initialized'
    try:
        config(provider)
        # Reading status must not adopt a seed or authenticate at an issuer.
        if store().path.exists():state=store().inspect(provider)['state']
    except TransferError as e:state=e.code.removeprefix('operator_')
    return {'configured':True,'connected':False,'integration':'operator','storage':'server_encrypted',
        'operator_mode':True,'access_state':state,
        'message':'운영자가 제공하는 자료 접근 · 파일별 접근 확인 필요' if state in ('active','not_initialized') else '운영자 제공 자료 접근이 현재 제한됩니다. 공개 경로는 별도로 확인합니다.'}


def admin_status(provider):
    prefix='OPERATOR_'+provider.upper()+'_'
    return {**public_status(provider),'missing_settings':missing_fields(provider,{k.lower():os.getenv(prefix+k,'') for k in FIELDS[provider]}),
        'policy_reviewed':os.getenv(prefix+'REDISTRIBUTION_REVIEWED')=='1','enabled':enabled(provider)}


@asynccontextmanager
async def transfer_scope(provider,resource=None):
    identifier=fingerprint([provider,resource]) if resource else secrets.token_hex(16)
    store().enter(provider,identifier,27*60 if provider=='cdse' else 125)
    try:yield
    finally:store().leave(identifier)


def cdse_asset(raw,key):
    assets=raw.get('assets',{});product=assets.get('Product',{}).get('href','')
    match=re.fullmatch(r'https://download\.dataspace\.copernicus\.eu/odata/v1/Products\(([a-f0-9-]{36})\)/\$value',product)
    if not match:raise TransferError('product_mismatch')
    original=assets[key]
    if key=='Product':return {**original,'operator_provider':'cdse','filename':raw['id']+'.zip'}
    if key not in ('vv','vh','hh','hv'):raise TransferError('unsupported_format')
    u=urlsplit(original.get('href',''));parts=unquote(u.path).split('/')
    try:index=parts.index(raw['id']+'.SAFE');nodes=parts[index:]
    except ValueError:raise TransferError('product_mismatch') from None
    if u.scheme!='s3' or u.hostname!='eodata' or len(nodes)!=3 or nodes[1]!='measurement' or any(not re.fullmatch(r'[A-Za-z0-9_.-]+',v) for v in nodes):raise TransferError('product_mismatch')
    href='https://download.dataspace.copernicus.eu/odata/v1/Products('+match[1]+')/'+ '/'.join('Nodes('+quote(v,safe='')+')' for v in nodes)+'/$value'
    return {**original,'href':href,'operator_provider':'cdse','filename':nodes[-1]}


async def cdse_preview(raw):
    from .provider_transfer import read_json
    product=cdse_asset(raw,'Product')['href'].removesuffix('/$value')
    current=product
    # Every node must actually occur in the public official listing, not merely
    # be a plausible pathname next to a product with a similar acquisition date.
    for expected in (raw['id']+'.SAFE','preview','quick-look.png'):
        data=await read_json(current+'/Nodes')
        rows=data.get('result',[])
        if not isinstance(rows,list):raise TransferError('operator_invalid_response')
        matches=[r for r in rows if isinstance(r,dict) and r.get('Name')==expected]
        if len(matches)!=1:raise TransferError('operator_file_unavailable')
        current+='/Nodes('+quote(expected,safe='')+')'
    return {'href':current+'/$value','type':'image/png','operator_provider':'cdse','filename':'quick-look.png'}
