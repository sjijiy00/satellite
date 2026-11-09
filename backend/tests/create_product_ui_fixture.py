"""TEST ONLY generated local real TIFFs for UI transport regression."""
import sys,pathlib,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from test_product_engines import sample
from app import artifact_store
from app.processing_worker import execute
from uuid import uuid4
out=pathlib.Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
artifact_store.ROOT=out/'TEST_ONLY_private'
for method,profile in [('ndvi','es_s2'),('mndwi','es_s2'),('mndwi_change','es_s2'),('ndbi','es_s2'),('surface_temperature','pc_landsat'),('hotspots','pc_landsat'),('temperature_comparison','pc_landsat')]:
    folder=out/method;folder.mkdir(exist_ok=True);query,payload,raws,grid=sample(folder,method,profile);identifier=uuid4().hex
    result=execute(payload,identifier);(out/(method+'.json')).write_text(json.dumps({'job_id':identifier,'input':query,**result},allow_nan=False),encoding='utf-8')
    (out/(method+'.zip')).write_bytes(artifact_store.verified_download(identifier,result['artifact']).read_bytes())

from test_thermal_ml import fixture_payload
folder=out/'thermal_ml';folder.mkdir(exist_ok=True);query,payload=fixture_payload(folder);identifier=uuid4().hex
result=execute(payload,identifier)
(out/'thermal_ml.json').write_text(json.dumps({'job_id':identifier,'input':query,**result},allow_nan=False),encoding='utf-8')
(out/'thermal_ml.zip').write_bytes(artifact_store.verified_download(identifier,result['artifact']).read_bytes())
