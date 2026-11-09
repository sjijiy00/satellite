"""TEST ONLY: create real small TIFF/ZIP bytes for mocked browser transport."""
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from uuid import uuid4
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_processing_foundation import raster_payload
from app import artifact_store
from app.processing_worker import execute

def main():
    output=Path(sys.argv[1]).resolve();output.mkdir(parents=True,exist_ok=True)
    artifact_store.ROOT=output/'artifacts'
    with TemporaryDirectory() as temporary:
        payload=raster_payload(Path(temporary),method='ndvi_change')
        identifier=uuid4().hex;result=execute(payload,identifier)
    body=(artifact_store.ROOT/identifier/'result.zip').read_bytes()
    (output/'TEST_ONLY_result.zip').write_bytes(body)
    result.update(job_id=identifier,input=payload['processing_input'],scope='TEST ONLY local TIFF arithmetic; no real provider transport')
    (output/'TEST_ONLY_result.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False),encoding='utf8')
    print('TEST ONLY verified TIFF/ZIP fixture created; no credentials/providers used.')

if __name__=='__main__':main()
