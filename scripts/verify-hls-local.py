"""Explicit, bounded HLS verification. Run ONLY after operator credential-use approval.

Environment must be supplied by scripts/server-env.mjs; never reads/prints secrets.
At most one whole original per product, 16 MiB each. No AI or pixel analysis.
"""
import json
import os
from pathlib import Path
import sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'backend'))
os.environ['AI_NL_ENABLED']='0' # this verification process only
from fastapi.testclient import TestClient
from rasterio.io import MemoryFile
from app.main import app
from app import media_access as media,provider_transfer as transfer,operator_access as operator

LIMIT=16*1024**2
OUT=ROOT/'frontend'/'test-results'/'hls'


def main():
    if not operator.enabled('nasa'):raise RuntimeError('Operator NASA mode is disabled')
    operator.config('nasa') # validates settings without printing their values
    OUT.mkdir(parents=True,exist_ok=True)
    report={'time_utc':datetime.now(timezone.utc).isoformat(),'authentication_attempted':True,
        'limit_bytes_per_file':LIMIT,'products':[]}
    client=TestClient(app)
    query={'purpose_type':'vegetation','bbox':[126.7,36.4,126.71,36.41],
        'start_date':'2025-07-20','end_date':'2025-07-26','collections':['hls-l30-002','hls-s30-002'],'max_items':25}
    response=client.post('/search',json=query)
    report['search_http']=response.status_code
    if response.status_code!=200:
        report['search_status']='failed'
        return report
    data=response.json();report['search_status']=data['outcome'];report['collection_statuses']=data['collection_statuses']
    session=client.get('/media/session');cookies={media.COOKIE:session.cookies[media.COOKIE]}
    headers={'Origin':os.getenv('OPERATOR_PUBLIC_ORIGIN','http://127.0.0.1:3000')}
    for collection in query['collections']:
        scene=next((s for s in data['items'] if s['collection']==collection),None)
        row={'collection':collection,'download_status':'not_executed'};report['products'].append(row)
        if scene is None:row['search_status']='no_scene';continue
        reference={key:scene[key] for key in ('provider_id','collection','id')}
        operator.require_product(reference)
        row.update(reference=reference,original_id=scene['hls']['original_id'],datetime=scene['datetime'],
            overlap_percent=scene['overlap_percent'],scene_cloud_cover=scene['scene_cloud_cover'])
        inspected=client.post('/media/inspect',json=reference|{'asset_keys':[],'include_preview':True},headers=headers,cookies=cookies)
        preview=inspected.json().get('preview') or {}
        row.update(preview_status=preview.get('status','failed'),preview_http=preview.get('http_status'))
        if preview.get('status')=='available':
            image=client.get(preview['url'].replace('/api','',1),cookies=cookies)
            with MemoryFile(image.content) as mem,mem.open() as f:
                f.read();row.update(preview_bytes=len(image.content),preview_driver=f.driver,preview_dimensions=[f.width,f.height])
            (OUT/(collection+'-browse.jpg')).write_bytes(image.content)
        keys={a['key'] for a in scene['download_assets']}
        for key in ('B04','B01','B09','Fmask'):
            if key not in keys:continue
            result=client.post('/media/inspect',json=reference|{'asset_keys':[key],'include_preview':False},headers=headers,cookies=cookies)
            asset=(result.json().get('assets') or [{}])[0]
            row.setdefault('probes',[]).append({'key':key,'status':asset.get('status'),'http_status':asset.get('http_status'),'size_bytes':asset.get('size_bytes')})
            if asset.get('status')!='available':
                row['download_status']=asset.get('status','access_failed')
                break # no retry loops against auth/provider failures
            size=asset.get('size_bytes')
            if not isinstance(size,int) or not 0<size<=LIMIT:
                row['download_status']='size_unknown_or_above_verification_limit'
                continue
            # The provider could change size after probing. Enforce the same
            # strict ceiling during complete transfer, not just on the old HEAD.
            old_limit=transfer.FILE_BYTES;transfer.FILE_BYTES=LIMIT
            try:file=client.get(asset['download_url'].replace('/api','',1),headers=headers,cookies=cookies)
            finally:transfer.FILE_BYTES=old_limit
            row['download_http']=file.status_code
            if file.status_code!=200:
                row['download_status']=(file.json().get('error') or {}).get('status','transfer_failed');break
            if len(file.content)!=size or len(file.content)>LIMIT:
                row['download_status']='size_changed_or_incomplete';break
            with MemoryFile(file.content) as mem,mem.open() as f:
                if f.driver!='GTiff':raise ValueError('not_gtiff')
                sample=f.read(1,window=((0,min(8,f.height)),(0,min(8,f.width))))
                row.update(download_status='complete_gtiff_verified',asset_key=key,
                    asset_role='quality_mask' if key=='Fmask' else 'optical_band',download_bytes=len(file.content),
                    driver=f.driver,dimensions=[f.width,f.height],dtype=f.dtypes[0],crs=str(f.crs),sample_shape=list(sample.shape))
            (OUT/(collection+'-original-'+key+'.tif')).write_bytes(file.content)
            break
    report['operator_state']=operator.public_status('nasa')['access_state']
    return report


if __name__=='__main__':
    try:result=main()
    except Exception:
        # Never stringify exceptions or provider request objects containing auth.
        result={'status':'verification_failed','detail':'Local verification failed; secret diagnostics suppressed.'}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'authenticated-live.json').write_text(json.dumps(result,ensure_ascii=True,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=True))
