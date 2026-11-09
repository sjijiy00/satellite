"""A3 coordinator: reuse A2 metadata transport, product rules, geometry and dates."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
from time import monotonic
from datetime import datetime,timezone
from urllib.parse import quote
import httpx
from . import analysis_conditions as a2
from .metadata import normalize
from .purpose_plan import purpose_plan
from .selection import footprint_metrics
from .pixel_policy import LIMITS,POLICY,VERSION,QualityError
from .pixel_raster import make_grid
from .range_reader import public_cog

JOB_LOCK=threading.Lock()


def failure(message,status='failed'):
    return {'status':status,'error':message,'common_valid_area_m2':None,'common_valid_percent_aoi':None,
            'common_valid_percent_observed':None,'scenes':[],'policy':POLICY,'limits':LIMITS,'analysis_ready':False}


async def run_worker(payload):
    flags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
    p=subprocess.Popen([sys.executable,'-m','app.pixel_worker'],cwd=Path(__file__).resolve().parent.parent,
                       stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=flags)
    task=asyncio.create_task(asyncio.to_thread(p.communicate,json.dumps(payload,allow_nan=False).encode(),timeout=LIMITS['worker_seconds']))
    try:
        output,_=await asyncio.shield(task)
        if p.returncode!=0 or len(output)>8_000_000:return failure('래스터 작업 프로세스 실패/응답 크기 상한: 진단 값 미확인')
        return json.loads(output)
    except subprocess.TimeoutExpired:
        p.kill();await asyncio.to_thread(p.communicate)
        return failure('픽셀 처리 시간 상한 60초 초과: 작업을 중단했습니다. AOI를 줄여 주세요.','limited')
    except asyncio.CancelledError:
        p.kill()
        await task
        raise
    finally:
        if p.poll() is None:p.kill();await asyncio.to_thread(p.wait)


async def inspect_pixels(query,mode='quality'):
    if not JOB_LOCK.acquire(blocking=False):return failure('다른 픽셀 검사가 실행 중입니다. 동시 작업은 1개로 제한합니다.','busy')
    try:
        payload,requests=await prepare_pixels(query,mode)
        result=await run_worker(payload)
        result.update(version=result.get('version',VERSION),checked_at=result.get('checked_at',datetime.now(timezone.utc).isoformat()),input=query.model_dump(mode='json'),
                      provenance=[{k:s[k] for k in ('id','collection','datetime','source_url','processing_baseline','boa_offset_applied')} for s in payload['scenes']],metadata_requests=requests)
        return result
    except (QualityError,httpx.HTTPError,TimeoutError,ValueError,KeyError,TypeError) as e:
        return failure(str(e) if isinstance(e,QualityError) else '메타데이터·네트워크 검사 실패. 진단 값은 미확인입니다.')
    finally:JOB_LOCK.release()


async def prepare_pixels(query,mode='quality',*,allow_single=False,grid_limits=None):
    # Reject oversized AOIs before contacting any provider or opening rasters.
    make_grid(query.bbox,limits=grid_limits)
    scenes=[];normalized=[];budget={'started':monotonic(),'requests':0}
    async with httpx.AsyncClient(follow_redirects=False) as client:
        for i,ref in enumerate((query.scene_a,query.scene_b)):
            url=f'{a2.STAC_URL}/collections/{ref.collection}/items/{quote(ref.id,safe="")}'
            code,_,raw=await a2.request_metadata(client,'GET',url,budget)
            if code!=200 or not isinstance(raw,dict) or raw.get('id')!=ref.id or raw.get('collection')!=ref.collection:
                raise QualityError('원본 Item 조회 실패/식별자 불일치: 진단 보류')
            scene=normalize(raw);plan=purpose_plan(scene,query.purpose_type)
            if plan['product_status']!='met' or plan['missing_bands']:raise QualityError('S2 L2A 제품 또는 목적별 필수 밴드 미확인')
            if 'scl' not in plan['analysis_keys']:raise QualityError('SCL 품질 자료가 없습니다. 유효율은 미확인입니다.')
            normalized.append(scene)
            keys=[k for k in plan['analysis_keys'] if k!='scl'];assets={}
            for key in keys+['scl']:
                asset=raw['assets'][key];url=asset.get('href')
                if not public_cog(url) or asset.get('storage:requester_pays'):raise QualityError('인증·비용 없는 공개 Sentinel-2 COG만 읽을 수 있습니다.')
                bands=asset.get('raster:bands') or []
                if len(bands)!=1 or bands[0].get('nodata')!=0:raise QualityError('필수 밴드/SCL의 NoData 메타데이터 미확인')
                assets[key]={'url':url,'path':f'scene{i}-{key}.tif','nodata':bands[0]['nodata'],
                             'scale':bands[0].get('scale'),'offset':bands[0].get('offset')}
            scenes.append({'id':ref.id,'collection':ref.collection,'datetime':scene['datetime'],
                           'geometry':scene['geometry'],'source_url':f'{a2.STAC_URL}/collections/{ref.collection}/items/{quote(ref.id,safe="")}',
                           'processing_baseline':raw['properties'].get('s2:processing_baseline'),
                           'boa_offset_applied':raw['properties'].get('earthsearch:boa_offset_applied'),
                           'required_keys':keys,'assets':assets})
    times=[a2.captured(s) for s in normalized]
    if not all(times) or (not allow_single and (times[0]>=times[1] or times[0].date()==times[1].date())):raise QualityError('A3는 영상 1이 이전인 서로 다른 UTC 날짜의 쌍이 필요합니다.')
    if any(not query.start_date<=t.date()<=query.end_date for t in times):raise QualityError('촬영일이 검색 기간 밖입니다.')
    if query.reference_date and not times[0].date()<query.reference_date<=times[1].date():raise QualityError('선택한 날짜가 기준일 전후 조건을 충족하지 않습니다.')
    if not normalized[0]['instruments'] or normalized[0]['instruments']!=normalized[1]['instruments'] or normalized[0]['processing_level']!=normalized[1]['processing_level']:
        raise QualityError('동일 센서·제품 조건이 확인되지 않습니다.')
    if mode=='ndvi_change':
        if query.purpose_type!='vegetation':raise QualityError('A4는 식생 NDVI 변화만 지원합니다.')
        if normalized[0]['platform']!=normalized[1]['platform']:raise QualityError('A4는 같은 위성 플랫폼의 두 날짜만 지원합니다.')
        baselines=[s['processing_baseline'] for s in scenes]
        if not all(baselines) or baselines[0]!=baselines[1]:raise QualityError('두 시점 처리 기준선이 같지 않거나 미제공입니다.')
        from .change_analysis import calibration_for_change
        for scene in scenes:
            for key in ('red','nir'):
                if key not in scene['assets'] or not calibration_for_change(scene['assets'][key],scene):
                    raise QualityError('적색·근적외선 처리 기준선·scale/offset·Earth Search 보정 표시가 없거나 상충합니다. NDVI 계산을 보류합니다.')
    coverage=footprint_metrics(query.bbox,*[s['geometry'] for s in normalized])
    if coverage['common_area_m2'] is None or coverage['common_area_m2']<=0:raise QualityError('두 시점 공통 촬영 영역이 없거나 미확인입니다.')
    return {'bbox':list(query.bbox),'scenes':scenes,'minimum_valid_percent':query.minimum_valid_percent,'purpose':query.purpose_type,'reference_date':str(query.reference_date) if query.reference_date else None,'analysis_mode':mode},budget['requests']
