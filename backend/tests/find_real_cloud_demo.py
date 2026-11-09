"""Explicit public-data experiment; never changes QA, model, or validation gates."""
import asyncio,json,os,time
from pathlib import Path
from uuid import uuid4
from app import product_processing as pp,artifact_store
from app.product_policy import products,QA_VERSION
from app.processing_models import ProcessingRequest
from app.raster_source import open_sources

assert os.environ.get('LIVE_STAC')=='1' and os.environ.get('LIVE_PROCESSING')=='1'
out=Path('../test-results/real-cloud-demo');out.mkdir(parents=True,exist_ok=True)
p=products('thermal_ml')[0]
candidates=[
 ('LC08_L2SP_039035_20250804_02_T1','LC08_L2SP_039035_20250719_02_T1','2025-07-19','2025-08-04'),
 ('LC09_L2SP_039035_20250828_02_T1','LC09_L2SP_039035_20250812_02_T1','2025-08-12','2025-08-28'),
 ('LC09_L2SP_040035_20250718_02_T1','LC09_L2SP_040035_20250803_02_T1','2025-07-18','2025-08-03'),
]
boxes=[[-115.17,36.14,-115.13,36.18],[-115.25,36.20,-115.21,36.24],[-115.09,36.04,-115.05,36.08]]
if os.getenv('CLOUD_SCOUT')=='1':
 candidates=[('LC08_L2SP_039035_20250719_02_T1','LC08_L2SP_039035_20250703_02_T1','2025-07-01','2025-07-31')]
 rows=json.loads((out/'scout.json').read_text())
 boxes=[r['bbox'] for r in sorted(rows,key=lambda r:abs(r['bbox'][1]-36.2)+abs(r['bbox'][0]+115.15))[:12]]
if os.getenv('CLOUD_TARGETED')=='1':
 candidates=[('LC08_L2SP_039035_20250719_02_T1','LC08_L2SP_039035_20250703_02_T1','2025-07-01','2025-07-31')]
 boxes=[[-115.175,35.96,-115.127,36.005],[-115.18,35.95,-115.132,35.995],[-115.165,35.96,-115.117,36.005]]
if os.getenv('CLOUD_AUGUST_DONOR')=='1':
 candidates=[('LC08_L2SP_039035_20250719_02_T1','LC08_L2SP_039035_20250804_02_T1','2025-07-19','2025-08-04')]
if os.getenv('CLOUD_NORTH')=='1':
 candidates=[('LC08_L2SP_039035_20250719_02_T1','LC08_L2SP_039035_20250703_02_T1','2025-07-01','2025-07-31')]
 boxes=[[-115.14904,36.6343,-115.10904,36.6743],[-115.17036,36.61557,-115.13036,36.65557],[-114.79106,36.7425,-114.75106,36.7825]]
for target,donor,start,end in candidates:
 for bbox in boxes:
  uncertainty=float(os.getenv('DEMO_QA_K','2'))
  label=target+'_'+str(bbox[0])+'_qa'+str(uncertainty)+('_augdonor' if os.getenv('CLOUD_AUGUST_DONOR')=='1' else '');file=out/(label+'.json')
  if file.exists():continue
  q=dict(purpose_type='thermal',analysis_id='surface_temperature',method_id='thermal_ml',roi=dict(confirmed=True,mode='bbox',source='manual_bbox',bbox=bbox),start_date=start,end_date=end,qa_policy_version=QA_VERSION,qa_options={'maximum_uncertainty_k':2,'minimum_cloud_distance_km':1},scenes=[dict(provider_id=p['provider_id'],collection=p['collection'],id=id,asset_keys=p['required_keys']) for id in [target,donor]])
  q['qa_options']['maximum_uncertainty_k']=uncertainty
  evidence={'input':q,'real_cloud_qa_unmodified':True};store=None;t=time.monotonic()
  try:
   payload,_=asyncio.run(pp.prepare(ProcessingRequest.model_validate(q)))
   store=open_sources(payload);identifier=uuid4().hex
   result=pp.execute(payload,identifier,store)
   evidence.update(status='succeeded',result=result)
   path=artifact_store.verified_download(identifier,result['artifact']);(out/(label+'.zip')).write_bytes(path.read_bytes())
  except Exception as e:evidence.update(status='failed',error=str(e),failure=getattr(e,'failure',None))
  finally:
   if store:evidence['transfer']={'bytes':store.bytes,'requests':store.requests};store.close()
   evidence['seconds']=round(time.monotonic()-t,1);file.write_text(json.dumps(evidence,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
  print(label,evidence['status'],evidence.get('failure',{}),flush=True)
  if evidence['status']=='succeeded' and evidence['result']['result']['ml_validation']['estimated_cells']>=100:raise SystemExit(0)
