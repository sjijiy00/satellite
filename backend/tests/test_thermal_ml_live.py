"""Real public temperatures, deliberately simulated cloud gap; NOT real cloud truth."""
import asyncio,json,os
from pathlib import Path
from uuid import uuid4
import numpy as np
import pytest
from app import product_processing,artifact_store
from app.product_policy import products,QA_VERSION
from app.processing_models import ProcessingRequest
from app.processing_failure import ProcessingBlocked
from app.raster_source import open_sources

@pytest.mark.skipif(os.getenv('LIVE_STAC')!='1' or os.getenv('LIVE_PROCESSING')!='1',reason='Explicit public read flags only')
def test_real_public_pixels_with_simulated_cloud_holdout(tmp_path,monkeypatch):
 p=products('thermal_ml')[0]
 q=dict(purpose_type='thermal',analysis_id='surface_temperature',method_id='thermal_ml',
        roi=dict(confirmed=True,mode='bbox',source='manual_bbox',bbox=[-115.17,36.14,-115.13,36.18]),
        start_date='2025-07-01',end_date='2025-07-31',qa_policy_version=QA_VERSION,
        scenes=[dict(provider_id=p['provider_id'],collection=p['collection'],id=id,asset_keys=p['required_keys']) for id in ['LC08_L2SP_039035_20250719_02_T1','LC08_L2SP_039035_20250703_02_T1']])
 payload,_=asyncio.run(product_processing.prepare(ProcessingRequest.model_validate(q)))
 original=product_processing.read_scene;truth={}
 def simulated(scene,g,opener):
  bands,valid,observed,headers,qa=original(scene,g,opener)
  if scene['id']==q['scenes'][0]['id']:
   h,w=valid.shape;mask=np.zeros(valid.shape,bool);mask[h*2//5:h*3//5,w*2//5:w*3//5]=True
   truth.update(values=bands['thermal'].copy(),valid=valid.copy(),mask=mask)
   qa=qa.copy();qa[mask]|=8;valid=valid&~mask
  return bands,valid,observed,headers,qa
 monkeypatch.setattr(product_processing,'read_scene',simulated)
 monkeypatch.setattr(artifact_store,'ROOT',tmp_path/'artifacts')
 out=Path(os.environ['PROCESSING_EVIDENCE_DIR']);out.mkdir(parents=True,exist_ok=True)
 store=open_sources(payload)
 evidence={'scope':'Actual public Landsat pixels; center 20% width/height simulated cloud mask; not real cloud accuracy','input':q}
 try:
  try:
   result=product_processing.execute(payload,uuid4().hex,store)
   evidence.update(status='passed',validation=result['result']['ml_validation'])
   path=artifact_store.verified_download(result['artifact']['filename'][11:-4],result['artifact'])
   (out/'public-simulated-cloud.zip').write_bytes(path.read_bytes())
   import zipfile,rasterio
   with zipfile.ZipFile(path) as z:
    with rasterio.io.MemoryFile(z.read('estimated_only.tif')) as f:
     with f.open() as d:estimated=d.read(1)
   mask=truth['valid']&truth['mask']&(estimated!=-9999)
   assert mask.any()
   error=estimated[mask]-truth['values'][mask]
   evidence['independent_simulated_gap']={'count':int(mask.sum()),'rmse_k':float(np.sqrt(np.mean(error**2))),'mae_k':float(np.abs(error).mean())}
  except ProcessingBlocked as e:
   evidence.update(status='blocked',message=str(e),failure=e.failure)
   assert e.failure['code'].startswith('ml_')
 finally:
  evidence['transfer']={'bytes':store.bytes,'requests':store.requests};store.close()
  (out/'public-simulated-cloud.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
