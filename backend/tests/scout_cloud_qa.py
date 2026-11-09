"""LIVE QA-only spatial scouting. Coarse QA never counts as ML validation."""
import asyncio,json,os
from pathlib import Path
import numpy as np,rasterio
from rasterio.windows import from_bounds
from rasterio.warp import transform_bounds,transform
from app import product_processing as pp
from app.product_policy import products,QA_VERSION
from app.processing_models import ProcessingRequest
from app.raster_source import open_sources
assert os.getenv('LIVE_STAC')=='1'
p=products('thermal_ml')[0];ids=['LC08_L2SP_039035_20250719_02_T1','LC08_L2SP_039035_20250703_02_T1']
q=dict(purpose_type='thermal',analysis_id='surface_temperature',method_id='thermal_ml',roi=dict(confirmed=True,mode='bbox',source='manual_bbox',bbox=[-115.17,36.14,-115.13,36.18]),start_date='2025-07-19',end_date='2025-08-04',qa_policy_version=QA_VERSION,scenes=[dict(provider_id=p['provider_id'],collection=p['collection'],id=id,asset_keys=p['required_keys']) for id in ids])
q['start_date']='2025-07-01';q['end_date']='2025-07-31'
payload,_=asyncio.run(pp.prepare(ProcessingRequest.model_validate(q)));store=open_sources(payload)
try:
 a=payload['scenes'][0]['assets']['qa_pixel']
 with rasterio.open(a['path'],opener=store,driver='GTiff',sharing=False) as src:
  bounds=transform_bounds('EPSG:4326',src.crs,-115.8,35.6,-114.5,36.8)
  w=from_bounds(*bounds,src.transform);arr=src.read(1,window=w,out_shape=(1024,1024))
  t=src.window_transform(w)*rasterio.Affine.scale(w.width/1024,w.height/1024)
  cloud=(arr&(8 if os.getenv('CLOUD_ONLY')=='1' else 30))!=0;clear=(arr&63)==0;found=[]
  for y in range(20,1004,16):
   for x in range(20,1004,16):
    region=cloud[y-16:y+16,x-16:x+16];clr=clear[y-16:y+16,x-16:x+16]
    if .02<region.mean()<.15 and min(clr[:16,:16].mean(),clr[:16,16:].mean(),clr[16:,:16].mean(),clr[16:,16:].mean())>.6:
     lon,lat=transform(src.crs,'EPSG:4326',*[ [v] for v in t*(x,y)])
     found.append({'bbox':[round(lon[0]-.02,5),round(lat[0]-.02,5),round(lon[0]+.02,5),round(lat[0]+.02,5)],'coarse_cloud':float(region.mean())})
  Path('../test-results/real-cloud-demo/scout.json').write_text(json.dumps(found,indent=2));print(json.dumps(found[:12]),flush=True)
finally:store.close()
