import asyncio,json,os
import numpy as np
from pathlib import Path
from app import product_processing as pp
from app.processing_models import ProcessingRequest
from app.raster_source import open_sources
from app.processing_raster import processing_grid
from app.landsat_temperature import thermal_valid
assert os.getenv('LIVE_STAC')=='1'
q=json.loads(Path('../test-results/real-cloud-demo/LC08_L2SP_039035_20250804_02_T1_-115.14545.json').read_text(encoding='utf8'))['input']
payload,_=asyncio.run(pp.prepare(ProcessingRequest.model_validate(q)));g,_=processing_grid(payload);store=open_sources(payload)
try:
 for s in payload['scenes']:
  b,v,o,h,qa=pp.read_scene(s,g,store)
  print(s['id'], 'basevalid',int(v.sum()),'observed',int(o.sum()),'thermalvalid',int((v&thermal_valid(b['qa'],b['cdist'],q['qa_options'])).sum()),flush=True)
  for k in ['qa','cdist','thermal']:
   a=b[k];print(k,np.nanpercentile(a,[0,10,50,90,100]).tolist(),flush=True)
  print('qa flags',np.unique(qa,return_counts=True),flush=True)
finally:store.close()
