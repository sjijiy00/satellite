"""In-process, bounded plan confirmation and cancellable observed-pixel jobs."""
import asyncio
import base64
from datetime import datetime,timezone
import hashlib
import json
from time import monotonic
from uuid import uuid4
from urllib.parse import quote

import httpx
from fastapi import HTTPException

from . import analysis_conditions as a2
from .models import CompositePlanRequest
from .metadata import normalize
from .purpose_plan import purpose_plan, RULES
from .change_analysis import calibration_for_change
from .cloud_composite import BANDS,VERSION
from .pixel_quality import JOB_LOCK,run_worker
from .pixel_raster import make_grid
from .pixel_policy import QualityError
from .range_reader import public_cog

PLANS={}
JOBS={}
TTL_SECONDS=900
MAX_SAVED=8


def _now():return datetime.now(timezone.utc).isoformat()


def _trim():
    for key in list(PLANS):
        if PLANS[key]['expires']<monotonic():PLANS.pop(key,None)
    if len(PLANS)>=MAX_SAVED:
        oldest=min(PLANS,key=lambda k:PLANS[k]['expires']);PLANS.pop(oldest,None)
    for key in list(JOBS):
        if JOBS[key]['expires']<monotonic() and JOBS[key]['status'] not in ('queued','running'):
            JOBS.pop(key,None)


async def _payload(query):
    make_grid(query.bbox)
    if set(BANDS)!=set(dict.fromkeys(RULES['vegetation']['required']+RULES['vegetation']['visual'])):
        raise QualityError('식생 목적 밴드 규칙과 합성 밴드 설정이 다릅니다.')
    scenes=[];budget={'started':monotonic(),'requests':0}
    async with httpx.AsyncClient(follow_redirects=False) as client:
        for index,ref in enumerate(query.scene_refs):
            url=f'{a2.STAC_URL}/collections/{ref.collection}/items/{quote(ref.id,safe="")}'
            code,_,raw=await a2.request_metadata(client,'GET',url,budget)
            if code!=200 or not isinstance(raw,dict) or raw.get('id')!=ref.id or raw.get('collection')!=ref.collection:
                raise QualityError('원본 Item 조회 실패/식별자 불일치. 가용성을 확인하지 못했습니다.')
            item=normalize(raw);plan=purpose_plan(item,'vegetation')
            if plan['product_status']!='met' or plan['missing_bands'] or item.get('collection')!='sentinel-2-l2a':
                raise QualityError('Sentinel-2 L2A 제품·식생 필수 밴드 조건 미충족')
            if not item.get('datetime') or not item.get('geometry') or not item.get('platform'):
                raise QualityError('촬영일·footprint·위성 플랫폼 메타데이터 미확인')
            when=a2.captured(item)
            if not when or not query.start_date<=when.date()<=query.end_date:
                raise QualityError('허용 기간 밖 또는 날짜 미확인 Item은 사용할 수 없습니다.')
            assets={}
            for key in (*BANDS,'scl'):
                asset=raw.get('assets',{}).get(key) or {}
                href=asset.get('href')
                bands=asset.get('raster:bands') or []
                if not public_cog(href) or asset.get('storage:requester_pays'):
                    raise QualityError('허용된 공개 Sentinel-2 COG만 읽습니다. 인증/비용/리다이렉트 자료는 미지원입니다.')
                if len(bands)!=1 or bands[0].get('nodata')!=0:
                    raise QualityError('필수 밴드·SCL의 NoData 자료 미확인. 구름 0%로 간주하지 않습니다.')
                assets[key]={'url':href,'path':f'composite-{index}-{key}.tif','nodata':0,
                             'scale':bands[0].get('scale'),'offset':bands[0].get('offset')}
            scene={'id':ref.id,'collection':ref.collection,'datetime':item['datetime'],
                   'geometry':item['geometry'],'platform':item['platform'],
                   'processing_baseline':raw.get('properties',{}).get('s2:processing_baseline'),
                   'boa_offset_applied':raw.get('properties',{}).get('earthsearch:boa_offset_applied'),
                   'required_keys':list(BANDS),'assets':assets,'item_url':url}
            if any(not calibration_for_change(assets[key],scene) for key in BANDS):
                raise QualityError('반사도 scale/offset·보정 표시 누락/상충. 구름 검사와 수치 합성을 혼동하지 않습니다.')
            scenes.append(scene)
    if len({(s['platform'],s['processing_baseline']) for s in scenes})!=1 or not scenes[0]['processing_baseline']:
        raise QualityError('동일 플랫폼·처리 기준선의 제품만 합성할 수 있습니다.')
    return {'bbox':list(query.bbox),'start_date':str(query.start_date),'end_date':str(query.end_date),
            'purpose':'vegetation','temporal_mode':'single','target_id':query.target_scene.id,
            'allow_date_change':query.allow_date_change,'minimum_valid_percent':70,'scenes':scenes},budget['requests']


def _digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def _estimate_evidence(payload,result):
    files=result.get('transfer',{}).get('files',{})
    if not files or not all(info.get('etag') for info in files.values()):
        raise QualityError('추정 계획은 원본 파일 ETag 확인이 필요합니다. 파일 변경 여부를 검증할 수 없어 중단합니다.')
    return _digest({'payload':payload,'models_fingerprint':result.get('models_fingerprint'),
                    'validation':result.get('validation'),'areas':result.get('areas'),
                    'source_etags':{key:info['etag'] for key,info in files.items()}})


async def make_plan(query:CompositePlanRequest,kind='observed'):
    if kind not in ('observed','estimate'):raise ValueError('알 수 없는 처리 모드')
    if kind=='estimate' and len(query.scene_refs)<2:
        return {'status':'blocked','can_execute':False,'error':'목표 영상과 다른 날짜의 참조 영상이 필요합니다.'}
    if not JOB_LOCK.acquire(blocking=False):
        return {'status':'busy','error':'다른 실제 픽셀 작업이 실행 중입니다. 잠시 뒤 다시 계획을 검사하세요.'}
    try:
        payload,requests=await _payload(query)
        result=await run_worker(payload|{'analysis_mode':'estimate_plan' if kind=='estimate' else 'composite_plan'})
        result['metadata_requests']=requests
        if result.get('status')!='planned':return result
        _trim();identifier=uuid4().hex;digest=_estimate_evidence(payload,result) if kind=='estimate' else _digest(payload)
        PLANS[identifier]={'query':query,'payload':payload,'digest':digest,'kind':kind,'expires':monotonic()+TTL_SECONDS}
        result.update(plan_id=identifier,confirmation_digest=digest,expires_in_seconds=TTL_SECONDS)
        return result
    except (QualityError,httpx.HTTPError,TimeoutError,ValueError,KeyError,TypeError) as exc:
        return {'status':'failed','error':str(exc) if isinstance(exc,QualityError) else '원본 메타데이터/접근 확인 실패. 합성 계획 미확인.'}
    finally:JOB_LOCK.release()


async def _execute(identifier,job):
    acquired=False
    try:
        if job['status']=='cancelled':return
        acquired=JOB_LOCK.acquire(blocking=False)
        if not acquired:raise QualityError('다른 실제 픽셀 작업이 실행 중입니다. 이 요청은 실행하지 않았습니다.')
        job.update(status='running',stage='원본 Item 재확인',updated_at=_now())
        plan=PLANS.get(identifier)
        if not plan or plan['expires']<monotonic():raise QualityError('계획이 만료되었습니다. 다시 검사하고 확인하세요.')
        fresh,_=await _payload(plan['query'])
        kind=plan.get('kind','observed')
        if kind=='observed' and _digest(fresh)!=plan['digest']:
            raise QualityError('원본 Item 또는 처리 조건이 계획 이후 바뀌었습니다. 다시 확인하세요.')
        job.update(stage='실제 밴드·SCL 범위 읽기 및 '+('국소 지도학습 추정' if kind=='estimate' else '픽셀 선택'),updated_at=_now())
        result=await run_worker(fresh|{'analysis_mode':'estimate_execute' if kind=='estimate' else 'composite_execute'})
        if job['status']=='cancelled':return
        if result.get('status')!='succeeded' or not result.get('artifact_base64'):
            raise QualityError(result.get('error') or '합성 작업이 파일을 생성하지 못했습니다.')
        if kind=='estimate' and _estimate_evidence(fresh,result)!=plan['digest']:
            raise QualityError('추정 계획 이후 원본 파일·학습/검증 결과가 바뀌었습니다. 다시 검사하고 확인하세요.')
        data=base64.b64decode(result.pop('artifact_base64'),validate=True)
        job.update(status='succeeded',stage='GeoTIFF 재열기 검증·'+('추정/관측 분리' if kind=='estimate' else '관측 합성')+' ZIP 준비 완료',updated_at=_now(),
                   result=result,artifact=data,expires=monotonic()+TTL_SECONDS)
    except asyncio.CancelledError:
        job.update(status='cancelled',stage='작업 취소·자식 래스터 프로세스 종료',updated_at=_now(),artifact=None)
    except Exception as exc:
        message=str(exc) if isinstance(exc,QualityError) else '합성 작업 중 오류. 자료는 미확인입니다.'
        job.update(status='failed',stage='실패',error=message,updated_at=_now(),artifact=None)
    finally:
        if acquired:JOB_LOCK.release()


def start_job(plan_id,digest,kind='observed'):
    _trim();plan=PLANS.get(plan_id)
    if not plan or plan['expires']<monotonic():raise HTTPException(404,'확인된 계획이 없거나 만료되었습니다.')
    if plan.get('kind','observed')!=kind:raise HTTPException(409,'서로 다른 처리 모드의 계획을 실행할 수 없습니다.')
    if digest!=plan['digest']:raise HTTPException(409,'확인한 계획과 요청 조건이 다릅니다.')
    if any(j['plan_id']==plan_id for j in JOBS.values()):raise HTTPException(409,'같은 계획의 중복 작업은 실행하지 않습니다.')
    if len(JOBS)>=MAX_SAVED:raise HTTPException(429,'보관 중인 작업 상한입니다. 15분 뒤 다시 시도하세요.')
    identifier=uuid4().hex
    job={'job_id':identifier,'plan_id':plan_id,'status':'queued','stage':'실행 대기','created_at':_now(),
         'updated_at':_now(),'error':None,'result':None,'artifact':None,'kind':kind,'expires':monotonic()+TTL_SECONDS,'owner':plan.get('owner')}
    JOBS[identifier]=job
    job['task']=asyncio.create_task(_execute(plan_id,job))
    return public_job(job)


def public_job(job):
    return {key:job[key] for key in ('job_id','plan_id','status','stage','created_at','updated_at','error','result')}


def get_job(identifier,kind='observed'):
    _trim();job=JOBS.get(identifier)
    if not job:raise HTTPException(404,'작업이 없거나 만료되었습니다.')
    if job.get('kind','observed')!=kind:raise HTTPException(404,'다른 처리 모드의 작업입니다.')
    return job


def cancel_job(identifier,kind='observed'):
    job=get_job(identifier,kind)
    if job['status'] in ('queued','running'):
        job.update(status='cancelled',stage='취소 중',updated_at=_now(),artifact=None)
        job['task'].cancel()
    return public_job(job)
