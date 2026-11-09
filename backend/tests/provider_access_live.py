"""Explicit public-only local app search/media probes. Never records receipts/URLs."""
import hashlib
import io
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone
import httpx
from rasterio.io import MemoryFile

assert os.getenv('LIVE_STAC')=='1', 'LIVE_STAC=1 required'
base=sys.argv[1];out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
assert base in ('http://127.0.0.1:3012','http://localhost:3012')
rows=[]
with httpx.Client(base_url=base,headers={'Origin':base},timeout=120,follow_redirects=False) as client:
    registry=client.get('/api/catalog').json()
    assert client.get('/api/media/session').status_code==200
    for collection in registry['collections']:
        purpose='thermal' if 'landsat' in collection else 'flood' if 'sentinel-1' in collection else 'vegetation'
        query={'purpose_type':purpose,'collections':[collection],'bbox':[126.7,36.4,126.71,36.41],
               'start_date':'2025-07-20','end_date':'2025-07-26','max_items':2}
        row={'collection':collection,'at':datetime.now(timezone.utc).isoformat(),'query':query,
             'authentication':'isolated public mode; operator/OAuth credentials not loaded',
             'full_original_download':'not_executed','pixel_processing':'not_tested_by_this_probe'}
        try:
            response=client.post('/api/search',json=query);row['search_http']=response.status_code
            data=response.json();row['returned']=data.get('returned');row['outcome']=data.get('outcome')
            row['collection_statuses']=[{k:s.get(k) for k in ('provider_id','collection','status','reason','returned','truncated')} for s in data.get('collection_statuses',[])]
            if response.status_code!=200 or not data.get('items'):
                row['preview']='not_checked_no_search_item';row['original_access']='not_checked_no_search_item'
            else:
                scene=data['items'][0];row.update(item_id=scene['id'],provider_id=scene['provider_id'],datetime=scene['datetime'])
                key=next(iter(scene.get('purpose_plan',{}).get('default_keys') or []),None)
                if not key:key=next(iter(a['key'] for a in scene.get('download_assets',[])),None)
                reference={'provider_id':scene['provider_id'],'collection':scene['collection'],'id':scene['id'],'asset_keys':[key] if key else [],'include_preview':True}
                inspected=client.post('/api/media/inspect',json=reference);row['inspect_http']=inspected.status_code
                if inspected.status_code==200:
                    status=inspected.json();preview=status.get('preview') or {};row['preview']={k:preview.get(k) for k in ('status','message','http_status','access_verified','original_status')}
                    row['original_access']=[{k:a.get(k) for k in ('key','status','message','http_status','access_verified','size_bytes','format_verified')} for a in status.get('assets',[])]
                    if preview.get('status')=='available' and preview.get('url','').startswith('/api/media/previews/'):
                        image=client.get(preview['url']);assert image.status_code==200
                        with MemoryFile(image.content) as memory:
                            with memory.open() as decoded:
                                decoded.read();row['preview_image']={'bytes':len(image.content),'format':decoded.driver,'size':[decoded.width,decoded.height],'sha256':hashlib.sha256(image.content).hexdigest(),'full_image_decoded':True}
                else:row['preview']=row['original_access']='inspect_failed'
        except Exception as error:
            # Never serialize exception URLs, bodies, cookies or auth headers.
            row['probe_error_type']=type(error).__name__
        rows.append(row)
        (out/'providers.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
        print(collection,row.get('search_http'),row.get('returned'),row.get('preview'),flush=True)
