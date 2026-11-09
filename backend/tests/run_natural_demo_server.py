"""Explicit diagnostic server for the approved demo; no credentials are recorded."""
import json
from pathlib import Path
import uvicorn
import time,hashlib,re
from app import ai_interpretation as ai

original=ai._send
saved=Path('test-results/natural-demo/ai-output.json')
if saved.exists():
    # Reuse the successful real response for the identical demo sentence only.
    source=Path('frontend/tests/natural-demo-live.spec.ts').read_text(encoding='utf-8')
    sentence=re.search(r"\.fill\('([^']+)'\)",source).group(1)
    body=json.loads(saved.read_text(encoding='utf-8'))
    extraction=ai.Extraction.model_validate_json(body['output'][0]['content'][0]['text'])
    ai._conditions(extraction,sentence)
    key=hashlib.sha256(('detail-flow-1\0'+ai.config()['model']+'\0'+sentence).encode()).hexdigest()
    ai.cache[key]=(time.monotonic(),extraction)
async def capture(payload,key):
    if saved.exists():raise RuntimeError('Approved paid diagnostic budget exhausted; cached sentence only')
    body=await original(payload,key)
    if payload.get('input','').startswith('충청남도 청양군 화성면 장계리'):
        Path('test-results/natural-demo/ai-output.json').write_text(json.dumps({k:body.get(k) for k in ('status','output','usage')},ensure_ascii=False),encoding='utf-8')
    return body
ai._send=capture
if __name__=='__main__':
    uvicorn.run('app.main:app',host='127.0.0.1',port=8000)
