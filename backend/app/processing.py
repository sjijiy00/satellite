"""Shared explicit plans/jobs; recommendation, access, QA and success stay separate."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import sys
import httpx
from time import monotonic
from types import SimpleNamespace
from uuid import uuid4
from datetime import datetime,timezone,timedelta
from fastapi import HTTPException
from .analysis_catalog import METHODS
from .models import CompositePlanRequest,ItemReference
from . import cloud_jobs,work_sessions,artifact_store,processing_repository as repository
from .pixel_quality import prepare_pixels,JOB_LOCK,run_worker
from .pixel_policy import QualityError
from .processing_raster import GRID_LIMITS,processing_grid
from . import media_access

PLANS={}
JOBS={}
TTL=900
MAX_SAVED=8
WORKER_SECONDS=75

def stamp():return datetime.now(timezone.utc).isoformat()
def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,allow_nan=False,separators=(',',':')).encode()).hexdigest()

def event(job,identifier,label,status):
    rows=job.setdefault('events',[])
    previous=next((r for r in rows if r['id']==identifier),None)
    value={'id':identifier,'label':label,'status':status,'at':stamp()}
    if previous:previous.update(value)
    else:rows.append(value)

def retain_terminal(job):
    job['expires']=monotonic()+artifact_store.TTL
    job['expires_at']=(datetime.now(timezone.utc)+timedelta(seconds=artifact_store.TTL)).isoformat()
    repository.save(job)

def cleanup():
    for rows in (PLANS,JOBS):
        for k,v in list(rows.items()):
            if v['expires']<monotonic() and v.get('status') not in ('queued','running'):
                rows.pop(k,None)
                # Evict in-memory state only. The verified private file and
                # signed journal have their own wall-clock retention policy.
    artifact_store.cleanup(active=[k for k,v in JOBS.items() if v['status'] in ('queued','running')])

async def prepare(query):
    method=METHODS[query.method_id]
    from .product_policy import PRODUCT_METHODS
    if query.method_id in PRODUCT_METHODS:
        from .product_processing import prepare as prepare_product
        return await prepare_product(query)
    if query.method_id in ('s2_quality','ndvi_change'):
        refs=[ItemReference(collection=s.collection,id=s.id) for s in query.scenes]
        q=SimpleNamespace(bbox=query.roi.bbox,purpose_type=query.purpose_type,start_date=query.start_date,
            end_date=query.end_date,scene_a=refs[0],scene_b=refs[-1],reference_date=query.reference_date,minimum_valid_percent=70)
        payload,_=await prepare_pixels(q,'ndvi_change' if query.method_id=='ndvi_change' else 'quality',
            allow_single=len(refs)==1,grid_limits=GRID_LIMITS)
    else:
        q=CompositePlanRequest(bbox=query.roi.bbox,start_date=query.start_date,end_date=query.end_date,
            purpose_type='vegetation',scene_refs=[{'collection':s.collection,'id':s.id} for s in query.scenes],
            target_scene={'collection':query.scenes[0].collection,'id':query.scenes[0].id},allow_date_change=False)
        payload,_=await cloud_jobs._payload(q)
        payload['analysis_mode']='estimate_execute' if query.method_id=='local_ridge' else 'composite_execute'
    payload.update(method_id=query.method_id,roi=query.roi.model_dump(),roi_fingerprint=query.roi.fingerprint(),
                   processing_input=query.model_dump(mode='json'))
    # Required assets are resolved from the canonical metadata, never browser URLs.
    for s in payload['scenes']:
        selected=next(r for r in query.scenes if r.id==s['id'] and r.collection==s['collection'])
        if not set(s['assets'])<=set(selected.asset_keys):raise QualityError('필수 밴드/QA 선택 누락: '+', '.join(sorted(set(s['assets'])-set(selected.asset_keys))))
    grid,count=processing_grid(payload)
    if query.method_id not in ('s2_quality','ndvi_change') and grid['aoi'].area>25*1e6:
        raise QualityError('기존 합성/ML은 25 km²까지만 지원합니다.')
    return payload,{'tile_count':count if query.method_id in ('s2_quality','ndvi_change') else 1,
        'width':grid['width'],'height':grid['height'],'resolution_m':20,
        'aoi_area_m2':grid['aoi'].area,'maximum_aoi_km2':method['spatial']['maximum_aoi_km2']}

async def plan(query,owner):
    cleanup()
    if os.getenv('PROCESSING_WORKERS','1')!='1':raise HTTPException(503,'영속 결과는 로컬 단일 worker에서만 지원합니다.')
    if len(PLANS)>=MAX_SAVED:raise HTTPException(429,'보관 중인 계획 상한입니다. 15분 뒤 다시 계획하세요.')
    try:
        repository.claim_worker()
        payload,grid=await prepare(query);evidence=None;quality=None
        if query.method_id in ('observed_composite','local_ridge'):
            if not JOB_LOCK.acquire(blocking=False):raise HTTPException(409,'다른 픽셀 작업이 실행 중입니다.')
            try:
                quality=await run_worker(payload|{'analysis_mode':'estimate_plan' if query.method_id=='local_ridge' else 'composite_plan'})
            finally:JOB_LOCK.release()
            if quality.get('status')!='planned' or not quality.get('can_execute'):
                raise QualityError(quality.get('error') or '기존 관측/ML 계획의 실행 조건 미충족')
            evidence=cloud_jobs._estimate_evidence(payload,quality) if query.method_id=='local_ridge' else digest(quality.get('transfer',{}).get('files',{}))
        identifier=uuid4().hex;confirmation=digest({'payload':payload,'evidence':evidence})
        PLANS[identifier]={'owner':owner,'query':query,'payload_digest':digest(payload),'evidence':evidence,
                           'confirmation_digest':confirmation,'expires':monotonic()+TTL}
        return {'plan_id':identifier,'confirmation_digest':confirmation,'status':'awaiting_confirmation',
            'source_access':'range_read_and_qa_checked' if quality else 'canonical_metadata_checked_pixels_pending',
            'pixel_quality':quality if quality else None,'grid':grid,'input':query.model_dump(mode='json'),
            'expected_artifacts':METHODS[query.method_id]['artifacts'],'expires_in_seconds':TTL,
            'notice':'브라우저 원본 수신과 별개인 서버 처리입니다. 명시 확인 후 실제 헤더/픽셀을 읽고 재검증합니다. AOI/기간은 바꾸지 않습니다.'}
    except QualityError as e:
        raise HTTPException(422,str(e)) from None
    except media_access.transfer.TransferError as e:
        raise HTTPException(422,media_access.MESSAGES.get(e.code,'제공처 원본 확인 실패. 접근/품질은 미확인입니다.')) from None
    except (httpx.HTTPError,TimeoutError,ValueError,KeyError,TypeError):
        raise HTTPException(422,'canonical Item/필수 Asset 메타데이터 확인 실패. 파일 접근과 품질은 미확인입니다.') from None

async def run_file_worker(payload,identifier):
    allowed={'SYSTEMROOT','WINDIR','PATH','TEMP','TMP','USERPROFILE','LOCALAPPDATA','PYTHONUTF8','GDAL_DATA','PROJ_DATA'}
    env={k:v for k,v in os.environ.items() if k.upper() in allowed}
    options={'creationflags':0x08000000} if os.name=='nt' else {}
    proc=await asyncio.create_subprocess_exec(sys.executable,'-m','app.processing_worker',cwd=Path(__file__).resolve().parent.parent,
        env=env,stdin=asyncio.subprocess.PIPE,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE,**options)
    try:
        raw=json.dumps({'payload':payload,'job_id':identifier,'storage_root':str(artifact_store.ROOT)},allow_nan=False).encode()
        output,_=await asyncio.wait_for(proc.communicate(raw),payload.get('execution_seconds',WORKER_SECONDS))
        if proc.returncode or len(output)>8_000_000:raise QualityError('처리 프로세스 실패/응답 상한 초과')
        return json.loads(output)
    except asyncio.TimeoutError:raise QualityError('작업 시간 상한 75초 초과. AOI를 직접 줄여 주세요.') from None
    finally:
        if proc.returncode is None:
            proc.kill();await proc.wait()

async def execute(identifier,job,plan_row):
    locked=False
    try:
        job.update(status='running',stage='canonical 조건 재검증',updated_at=stamp())
        repository.save(job)
        event(job,'canonical','canonical Item·조건 재검증','running')
        payload,_=await prepare(plan_row['query'])
        if digest(payload)!=plan_row['payload_digest']:raise QualityError('원본 Item/Asset 또는 조건이 계획 이후 변경됐습니다. 다시 계획하세요.')
        event(job,'canonical','canonical Item·조건 재검증','completed')
        locked=JOB_LOCK.acquire(blocking=False)
        if not locked:raise QualityError('다른 실제 픽셀 작업이 실행 중입니다. 다시 계획하세요.')
        # Reserve the entire worker input budget before it can read. The range
        # store enforces the same per-job ceiling. Reserve owner/global quotas
        # together; once admitted, failed workers retain their reservation.
        budget=payload.get('transfer_budget_bytes',64*1024**2)
        media_access.charge_many(('processing:'+job['owner'],'processing:global'),budget)
        job.update(stage='실제 헤더·AOI 범위·QA 검사 및 파일 생성',updated_at=stamp())
        event(job,'pixels','실제 Asset 읽기·QA·계산·파일 검증','running')
        output=await run_file_worker(payload,identifier)
        if job['status']=='cancelled':artifact_store.discard(identifier);return
        if output.get('status')!='succeeded':
            job['failure']=artifact_store.safe_value(output.get('failure'))
            raise QualityError(output.get('error') or '처리 실패·품질 미확인')
        if payload['method_id']=='local_ridge':
            if cloud_jobs._estimate_evidence(payload,output['result'])!=plan_row['evidence']:
                raise QualityError('ML 원본 ETag/검증 결과가 계획 이후 변경됐습니다.')
        elif payload['method_id']=='observed_composite':
            if digest(output['result'].get('transfer',{}).get('files',{}))!=plan_row['evidence']:
                raise QualityError('합성 원본 ETag가 계획 이후 변경됐습니다.')
        artifact_store.verified_download(identifier,output['artifact'])
        event(job,'pixels','실제 Asset 읽기·QA·계산·파일 검증','completed')
        job.update(status='succeeded',stage='GeoTIFF 재열기·해시 검증 완료',result=output['result'],artifact=output['artifact'],updated_at=stamp())
        retain_terminal(job)
    except asyncio.CancelledError:
        job.update(status='cancelled',stage='취소·자식 프로세스 종료',updated_at=stamp());artifact_store.discard(identifier)
    except Exception as e:
        message=str(e) if isinstance(e,QualityError) else media_access.MESSAGES.get(e.code,'제공처 전송/사용량 상한을 확인하세요.') if isinstance(e,media_access.transfer.TransferError) else '서버 처리 실패. 결과는 미확인입니다.'
        if isinstance(e,media_access.transfer.TransferError) and e.code=='quota_limit':
            seconds=getattr(e,'retry_after_seconds',None)
            job['failure']={'code':'transfer_quota','retry_at':(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat() if seconds else None}
        job.update(status='failed',stage='실패·품질 미확인',error=message,
                   result={'common_valid_area_m2':None,'common_valid_percent_aoi':None},artifact=None,updated_at=stamp())
        artifact_store.discard(identifier)
    finally:
        if job['status'] in ('failed','cancelled'):
            for row in job.get('events',[]):
                if row['status']=='running':row.update(status=job['status'],at=stamp())
            retain_terminal(job)
        if locked:JOB_LOCK.release()

def public(job):
    value={k:job[k] for k in ('job_id','status','stage','created_at','updated_at','error','result','artifact','input')}
    value.update(failure=job.get('failure'),events=job.get('events',[]),retention=artifact_store.retention(job['job_id'],job['artifact']),
                 ownership='same_browser_session_single_worker_persistent',job_expires_at=job.get('expires_at'))
    return value

def start(query,request):
    cleanup();row=PLANS.get(query.plan_id,{})
    work_sessions.require_owner(request,row)
    if row['confirmation_digest']!=query.confirmation_digest:raise HTTPException(409,'확인한 계획과 실행 조건이 다릅니다.')
    previous=repository.duplicate(row['owner'],query.idempotency_key)
    if previous:
        if previous['plan_id']!=query.plan_id:raise HTTPException(409,'다른 계획의 중복 실행 키입니다.')
        return public(previous)
    for job in JOBS.values():
        if job['owner']==row['owner'] and job['idempotency_key']==query.idempotency_key:
            if job['plan_id']!=query.plan_id:raise HTTPException(409,'다른 계획의 중복 실행 키입니다.')
            return public(job)
        if job['plan_id']==query.plan_id:raise HTTPException(409,'이미 실행한 계획입니다.')
    if sum(v['status'] in ('queued','running') for v in JOBS.values())>=MAX_SAVED:raise HTTPException(429,'실행 작업 상한입니다.')
    if len(repository.owned_ids(row['owner']))>=20:raise HTTPException(429,'세션별 보관 작업 20개 상한입니다. 보관 만료 후 다시 실행하세요.')
    identifier=uuid4().hex
    job={'job_id':identifier,'owner':row['owner'],'plan_id':query.plan_id,'idempotency_key':query.idempotency_key,
        'status':'queued','stage':'실행 대기','created_at':stamp(),'updated_at':stamp(),'error':None,'result':None,
        'artifact':None,'expires':monotonic()+TTL,'expires_at':(datetime.now(timezone.utc)+timedelta(seconds=TTL)).isoformat(),
        'events':[],'input':row['query'].model_dump(mode='json')}
    repository.save(job)
    JOBS[identifier]=job;job['task']=asyncio.create_task(execute(identifier,job,row))
    return public(job)

def owned(identifier,request):
    cleanup();job=JOBS.get(identifier,{})
    if not job:
        owner,_=work_sessions.identity(request)
        try:job=repository.load(identifier,owner) or {}
        except QualityError:raise HTTPException(409,'저장 작업 메타데이터가 변경됐습니다. 자동 실행하지 않습니다.') from None
    work_sessions.require_owner(request,job)
    return job

def cancel(identifier,request):
    job=owned(identifier,request)
    if job['status'] in ('queued','running'):
        job.update(status='cancelled',stage='취소 요청',updated_at=stamp());job['task'].cancel()
        retain_terminal(job)
    return public(job)

def download_response(identifier,request):
    from .media_access import BoundedStream,enter,leave,charge_many
    from .provider_transfer import TransferError
    job=owned(identifier,request)
    if job['status']!='succeeded' or not job['artifact']:raise HTTPException(409,'검증된 산출물이 아직 없습니다.')
    try:path=artifact_store.verified_download(identifier,job['artifact'])
    except QualityError:raise HTTPException(410,'산출물이 만료되거나 변경됐습니다.') from None
    try:enter()
    except TransferError:raise HTTPException(429,'다른 파일 전송이 진행 중입니다.') from None
    try:
        charge_many(('processing-download:'+job['owner'],'processing-download:global'),job['artifact']['bytes'])
        stream=path.open('rb')
    except TransferError:
        leave();raise HTTPException(429,'파일 전송 사용량 상한입니다. 잠시 뒤 다시 시도하세요.') from None
    except BaseException:leave();raise
    closed=False
    def close():
        nonlocal closed
        if not closed:closed=True;stream.close();leave()
    async def chunks():
        try:
            while body:=stream.read(65536):yield body
        finally:close()
    return BoundedStream(chunks(),on_close=close,seconds=120,media_type='application/zip',headers={
        'Content-Length':str(job['artifact']['bytes']),'Content-Disposition':'attachment; filename="'+job['artifact']['filename']+'"',
        'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})
