"""Explicit manual public runtime diagnostic. Never invokes AI/authentication.

Run directly, not collected by pytest. Receipts/cookies/URLs are never printed.
"""
import json
import argparse
from io import BytesIO
from datetime import datetime, timezone
import httpx

PRODUCTS = [
    ('earth-search', 'sentinel-2-l2a', 's2_msi', 'vegetation', 'scl'),
    ('planetary-computer', 'pc-sentinel-2-l2a', 'pc_s2_msi', 'vegetation', 'SCL'),
    ('planetary-computer', 'pc-landsat-c2-l2', 'pc_landsat_tirs', 'thermal', 'qa_pixel'),
    ('noaa-nodd', 'noaa-viirs-ndvi-cdr', 'noaa_viirs_ndvi', 'vegetation', 'ndvi'),
]

def emit(data):
    print(json.dumps({'checked_at': datetime.now(timezone.utc).isoformat(), **data}, ensure_ascii=False), flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--download',action='store_true',help='Explicitly receive small QA/SCL samples in memory only; NOAA is probe-only')
    args=parser.parse_args()
    with httpx.Client(base_url='http://127.0.0.1:3000', timeout=90, trust_env=False,
                      headers={'Origin': 'http://127.0.0.1:3000'}) as client:
        r=client.get('/api/health'); emit({'health':r.status_code})
        r=client.get('/api/media/session'); emit({'media_session':r.status_code})
        for provider,collection,profile,purpose,key in PRODUCTS:
            try:
                r=client.post('/api/search',json={'purpose_type':purpose,'recommendation_id':profile,
                    'bbox':[126.7,36.4,126.71,36.41], 'start_date':'2025-07-20',
                    'end_date':'2025-07-20' if provider=='noaa-nodd' else '2025-07-26','max_items':1})
                data=r.json();items=data.get('items',[])
                emit({'collection':collection,'search_http':r.status_code,'returned':len(items),
                    'statuses':[{k:s.get(k) for k in ('status','reason')} for s in data.get('collection_statuses',[])]})
                if not items:continue
                scene=items[0];asset=next((a for a in scene.get('download_assets',[]) if a['key']==key),{})
                emit({'collection':collection,'item':scene['id'],'key':key,'declared_bytes':asset.get('size_bytes'),
                    'requester_pays':asset.get('requester_pays'),'media_type':asset.get('media_type')})
                r=client.post('/api/media/inspect',json={'provider_id':provider,'collection':collection,
                    'id':scene['id'],'asset_keys':[key],'include_preview':True})
                report=r.json();p=report.get('preview') or {}
                emit({'collection':collection,'inspect_http':r.status_code,
                    'preview':{k:p.get(k) for k in ('status','http_status','message')},
                    'assets':[{k:a.get(k) for k in ('key','status','http_status','message')} for a in report.get('assets',[])],
                    'error':report.get('error',{}).get('code')})
                if p.get('status')=='available':
                    image=client.get(p['url'])
                    emit({'collection':collection,'preview_proxy_http':image.status_code,
                        'preview_bytes':len(image.content),'content_type':image.headers.get('content-type')})
                if args.download:
                    if provider=='noaa-nodd':
                        emit({'collection':collection,'full_download':'not_requested_large_file','probe_only':True})
                        continue
                    access=next((a for a in report.get('assets',[]) if a.get('key')==key),{})
                    if access.get('status')!='available':continue
                    # Same exact small QA/SCL samples from TEST_REPORT; NOAA size is supplied by S3 metadata.
                    expected={'sentinel-2-l2a':1591434,'pc-sentinel-2-l2a':1474350,
                              'pc-landsat-c2-l2':3718793,'noaa-viirs-ndvi-cdr':64011565}[collection]
                    emit({'collection':collection,'download_precheck_bytes':asset.get('size_bytes') or expected,
                          'size_basis':'current_metadata' if asset.get('size_bytes') else 'same_item_previous_full_receipt',
                          'client_limit_bytes':expected+1024})
                    output=BytesIO()
                    with client.stream('GET',access['download_url']) as response:
                        if response.status_code!=200:
                            response.read();body=response.json()
                            emit({'collection':collection,'download_http':response.status_code,
                                  'error':body.get('error',{}).get('status')});continue
                        length=int(response.headers.get('content-length','0'))
                        if not 0<length<=expected+1024:raise ValueError('Unexpected file size; body not read')
                        size=0
                        for chunk in response.iter_bytes():
                            size+=len(chunk)
                            if size>expected+1024:raise ValueError('File limit exceeded')
                            output.write(chunk)
                        if size!=length:raise ValueError('Incomplete response')
                    import rasterio
                    from rasterio.windows import Window
                    with rasterio.MemoryFile(output.getvalue()) as memory, memory.open() as dataset:
                        sample=dataset.read(1,window=Window(0,0,4,4))
                        decoded={'driver':dataset.driver,'width':dataset.width,'height':dataset.height,'sample_shape':list(sample.shape)}
                    output.close()
                    completed=client.get(access['download_url']+'/status').json().get('download_completed')
                    emit({'collection':collection,'download_http':200,'download_bytes':size,
                          'server_completed':completed,'decoded':decoded})
            except Exception as exc:
                emit({'collection':collection,'exception_type':type(exc).__name__})

if __name__=='__main__':main()
