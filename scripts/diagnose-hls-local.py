"""Explicit approved HLS diagnostics; no credential changes, renewals or raw HTTP logs.

Run with scripts/server-env.mjs. Uses only canonical CMR assets. At most one
whole original per product, <=10MiB each; failed probes stop that product.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from datetime import datetime, timezone
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile
import httpx
from app.main import app
from app import media_access as media, provider_transfer as transfer, operator_access as operator

LIMIT=10*1024**2
OUT=ROOT/'test-results'/'hls-diagnostic'


async def minimum_browse(url):
    records=[];current=url
    async with httpx.AsyncClient(trust_env=False,follow_redirects=False) as client:
        for hop in range(transfer.MAX_REDIRECTS+1):
            await transfer.validate_destination(current)
            async with client.stream('GET',current,timeout=15) as response:
                facts={**transfer.diagnostic_target(current),'stage':'minimal_response','hop':hop,
                    'range_requested':False,'authorization_present':False,**transfer.response_facts(response)}
                records.append(facts)
                if response.status_code==429:raise transfer.TransferError('provider_busy',429)
                if response.status_code in (301,302,303,307,308):
                    # No raw Location is retained. Validate before following.
                    from urllib.parse import urljoin
                    current=urljoin(current,response.headers.get('location',''))
                    await transfer.validate_destination(current)
                    continue
                if facts['content_type'] in ('text/html','application/xhtml+xml'):
                    raise transfer.TransferError('login_page',response.status_code)
                content=bytearray()
                async for chunk in response.aiter_bytes():
                    if len(content)+len(chunk)>transfer.PREVIEW_BYTES:raise transfer.TransferError('size_limit')
                    content.extend(chunk)
                facts['received_bytes']=len(content)
                facts['image_signature']=content.startswith((b'\xff\xd8\xff',b'\x89PNG\r\n\x1a\n'))
                return records
    raise transfer.TransferError('redirect_limit')


async def existing_token_only(provider,force=False,failed_token=None):
    """Same configured encrypted grant; NEVER reinitializes, rotates or renews."""
    if force:raise transfer.TransferError('operator_reconnection_required')
    if not operator.enabled(provider):raise transfer.TransferError('operator_disabled')
    values,revision,fp=operator.config(provider)
    status=operator.store().inspect(provider)
    if status['state']=='not_initialized':raise transfer.TransferError('operator_not_initialized')
    # A higher environment revision normally adopts a new grant in Store.load.
    # This diagnostic is read-only with respect to credentials, so reject it.
    if status['revision']!=revision:raise transfer.TransferError('operator_configuration_changed')
    row=operator.store().load(provider,revision,fp,operator.seed(provider,values))
    if row['state']!='active':raise transfer.TransferError('operator_'+row['state'])
    if not row.get('access') or row.get('expires',0)<=time.time()+300:raise transfer.TransferError('operator_expired')
    return row['access'],row['generation']


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    env_hash=hashlib.sha256((ROOT/'backend/.env').read_bytes()).digest()
    query={'purpose_type':'vegetation','bbox':[126.7,36.4,126.71,36.41],
        'start_date':'2025-07-20','end_date':'2025-07-26',
        'collections':['hls-l30-002','hls-s30-002'],'max_items':25}
    report={'time_utc':datetime.now(timezone.utc).isoformat(),'query':query,
            'per_file_limit_bytes':LIMIT,'token_renewal_permitted':False,'products':[]}
    with TestClient(app) as client,patch.object(operator,'token',existing_token_only):
        response=client.post('/search',json=query)
        report['search_http']=response.status_code
        if response.status_code!=200:return report
        data=response.json();report['search_outcome']=data['outcome']
        report['collection_statuses']=data['collection_statuses']
        session=client.get('/media/session')
        cookies={media.COOKIE:session.cookies[media.COOKIE]}
        headers={'Origin':os.getenv('OPERATOR_PUBLIC_ORIGIN','http://127.0.0.1:3000')}
        for collection in query['collections']:
            scene=next((s for s in data['items'] if s['collection']==collection),None)
            row={'collection':collection,'whole_file_status':'not_executed'};report['products'].append(row)
            if scene is None:row['search']='no_scene';continue
            ref={k:scene[k] for k in ('provider_id','collection','id')}
            operator.require_product(ref)
            row.update(reference=ref,original_id=scene['hls']['original_id'],datetime=scene['datetime'])
            raw=asyncio.run(media.canonical(ref));candidates=media.preview_candidates(raw)
            if candidates:
                try:row['minimum_browse']=asyncio.run(minimum_browse(candidates[0][1]['href']))
                except transfer.TransferError as error:
                    row['minimum_browse_error']=error.code
                    # Consent/login, rate limit, redirect and size failures are
                    # hard stops, never reasons to try different credentials.
                    report['stopped']=error.code
                    break
            trace=[]
            with transfer.diagnostics(trace):
                result=client.post('/media/inspect',json=ref|{'asset_keys':[],'include_preview':True},headers=headers,cookies=cookies)
            preview=result.json().get('preview') or {}
            row['app_browse']={'status':preview.get('status'),'http_status':preview.get('http_status'),'trace':trace}
            if preview.get('status') in ('provider_busy','login_page','login_required','eula_required',
                    'application_authorization_required','blocked_destination','blocked_redirect','redirect_limit','size_limit'):
                report['stopped']=preview['status'];break
            if preview.get('status')=='available':
                image=client.get(preview['url'].removeprefix('/api'),cookies=cookies)
                with MemoryFile(image.content) as memory,memory.open() as raster:
                    raster.read();row['app_browse'].update(received_bytes=len(image.content),driver=raster.driver,width=raster.width,height=raster.height)
                (OUT/(collection+'-browse.jpg')).write_bytes(image.content)
            keys={a['key'] for a in scene['download_assets']}
            for key in ('B04','B01','B09','Fmask'):
                if key not in keys:continue
                trace=[]
                with transfer.diagnostics(trace):
                    result=client.post('/media/inspect',json=ref|{'asset_keys':[key],'include_preview':False},headers=headers,cookies=cookies)
                asset=(result.json().get('assets') or [{}])[0]
                row.setdefault('original_probes',[]).append({'key':key,'status':asset.get('status'),
                    'http_status':asset.get('http_status'),'size_bytes':asset.get('size_bytes'),'trace':trace})
                if asset.get('status')!='available':break
                size=asset.get('size_bytes')
                if not isinstance(size,int) or not 0<size<=LIMIT:
                    row['whole_file_status']='size_unknown_or_above_10MiB';continue
                trace=[]
                with patch.object(transfer,'FILE_BYTES',LIMIT),transfer.diagnostics(trace):
                    received=client.get(asset['download_url'].removeprefix('/api'),headers=headers,cookies=cookies)
                row['whole_file_trace']=trace;row['whole_file_http']=received.status_code
                if received.status_code!=200:row['whole_file_status']='transfer_failed';break
                if len(received.content)!=size:row['whole_file_status']='size_mismatch';break
                with MemoryFile(received.content) as memory,memory.open() as raster:
                    if raster.driver!='GTiff':raise transfer.TransferError('invalid_file')
                    # Decode the entire small file, not just its header.
                    raster.read()
                    row.update(whole_file_status='complete_gtiff_decoded',asset_key=key,received_bytes=len(received.content),
                        driver=raster.driver,width=raster.width,height=raster.height,dtype=raster.dtypes[0],crs=str(raster.crs))
                (OUT/(collection+'-'+key+'.tif')).write_bytes(received.content)
                break
    report['env_unchanged']=env_hash==hashlib.sha256((ROOT/'backend/.env').read_bytes()).digest()
    return report


if __name__=='__main__':
    try:
        report=main()
        succeeded=len(report.get('products',[]))==2 and all(r.get('whole_file_status')=='complete_gtiff_decoded' and r.get('app_browse',{}).get('status')=='available' for r in report['products'])
        exit_code=0 if succeeded else 2
    except Exception as error:
        report={'status':'diagnostic_stopped','error_type':type(error).__name__}
        if isinstance(error,transfer.TransferError):report['code']=error.code
        exit_code=3
    report['exit_code']=exit_code
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'report.json').write_text(json.dumps(report,ensure_ascii=True,indent=2),encoding='utf-8')
    print(json.dumps({'report':'test-results/hls-diagnostic/report.json','exit_code':exit_code,
        'search_http':report.get('search_http'),'products':[
            {k:v for k,v in row.items() if k in ('collection','whole_file_status','received_bytes','asset_key')}
            | {'browse':row.get('app_browse',{}).get('status'),
               'probe':[{k:v for k,v in p.items() if k!='trace'} for p in row.get('original_probes',[])]}
            for row in report.get('products',[])]},ensure_ascii=True))
    sys.exit(exit_code)
