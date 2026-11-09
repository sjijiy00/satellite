import asyncio
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response, FileResponse
from .analysis_catalog import catalog as analysis_catalog
from .models import PurposeRequest, SearchRequest, SelectionRequest, ConditionsRequest, PixelQualityRequest, ChangeRequest, InterpretRequest, CompositePlanRequest, CompositeStartRequest, COLLECTIONS
from .request_interpretation import interpret
from .ai_interpretation import propose_with_ai, public_status
from .cloud_jobs import make_plan,start_job,get_job,cancel_job,public_job
from .pixel_quality import inspect_pixels
from .analysis_conditions import inspect_conditions
from .selection import common_footprint
from .recommendations import recommend, update_availability
from .purpose_plan import scene_matches_profile
from .stac import search_collections, CatalogError, STAC_URL
from .metadata import normalize
from .evaluation import evaluate, rank_key
from .provider_search import search_providers
from .provider_registry import PROVIDERS, COLLECTION_REGISTRY, CANDIDATES, PLATFORMS, SENSORS, PRODUCTS
from .sensor_catalog import CATALOG
from .catalog_discovery import discover
from . import earthdata_auth
from . import work_sessions
from .cloud_jobs import PLANS
from . import media_access
from . import place_search
from .log_safety import install as install_log_safety
from .access_paths import group_paths
from .access_guidance import for_purpose as access_guidance
from . import processing,artifact_store
from .processing_models import ProcessingRequest,ProcessingStart

install_log_safety()

app = FastAPI(title='Satellite Insight AI', version='0.1.0')


@app.get('/places/config')
async def place_config():
    return JSONResponse(place_search.config(),headers={'Cache-Control':'no-store'})


@app.post('/places/search')
async def search_places(query:place_search.PlaceRequest):
    return JSONResponse(await place_search.search(query),headers={'Cache-Control':'no-store'})


@app.get('/auth/earthdata/status')
async def earthdata_status(request: Request):
    return earthdata_auth.status(request)


@app.get('/auth/providers/status')
async def provider_auth_status(request: Request):
    return earthdata_auth.providers_status(request)


@app.get('/auth/earthdata/start')
async def earthdata_start():
    from . import operator_access as operator
    if operator.enabled('nasa'):return JSONResponse({'error':{'code':'OPERATOR_MODE','message':'운영자 제공 자료 접근 모드입니다. 파일별 접근 상태를 확인하세요.'}},status_code=409)
    return earthdata_auth.start()


@app.get('/auth/earthdata/callback')
async def earthdata_callback(request: Request, code: str | None = None,
                             state: str | None = None, error: str | None = None):
    return await earthdata_auth.callback(request, code, state, error)


@app.post('/auth/earthdata/logout')
async def earthdata_logout(request: Request):
    return earthdata_auth.logout(request)


@app.post('/auth/earthdata/refresh')
async def earthdata_refresh(request: Request):
    media_access.same_origin(request)
    try:
        await earthdata_auth.access_token(request)
    except earthdata_auth.AuthenticationRequired:
        pass
    return earthdata_auth.status(request)


@app.post('/media/inspect')
async def inspect_media(query: media_access.InspectRequest, request: Request):
    return await media_access.inspect(request,query)


@app.get('/media/session')
async def media_session(request: Request):
    return media_access.session_response(request)


@app.get('/media/previews/{ticket}')
async def media_preview(ticket: str, request: Request, download: bool=False):
    return media_access.preview_response(request,ticket,download)


@app.get('/media/downloads/{ticket}')
async def media_download(ticket: str, request: Request):
    return await media_access.download(request,ticket)


@app.get('/media/downloads/{ticket}/status')
async def media_download_status(ticket: str, request: Request):
    return media_access.download_status(request,ticket)


@app.exception_handler(RequestValidationError)
async def invalid_request(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={'error': {'code': 'INVALID_INPUT', 'message': '입력 조건을 확인하세요.',
                        'details': [{'field': '.'.join(str(x) for x in e['loc']), 'message': e['msg']} for e in exc.errors()]}})


@app.exception_handler(CatalogError)
async def catalog_error(request: Request, exc: CatalogError):
    return JSONResponse(status_code=exc.status, content={'error': {'code': 'STAC_ERROR', 'message': exc.message}})


@app.get('/health')
def health():
    return {'status': 'ok', 'phase': 1}


@app.post('/recommend')
def recommendation(query: PurposeRequest):
    return recommend("", query.purpose_type, target_size_m=query.target_size_m, observation_need=query.observation_need, temporal_mode=query.temporal_mode,detail_intent=query.detail_intent,requested_resolution_m=query.requested_resolution_m)


@app.get('/analysis/catalog')
def analysis_choices():
    return analysis_catalog()


@app.post('/processing/plans')
async def processing_plan(query:ProcessingRequest,request:Request):
    work_sessions.protect(request)
    owner,cookie=work_sessions.identity(request,True)
    result=await processing.plan(query,owner)
    return work_sessions.attach(JSONResponse(result,headers={'Cache-Control':'no-store'}),request,cookie)


@app.post('/processing/jobs')
async def processing_start(query:ProcessingStart,request:Request):
    work_sessions.protect(request)
    return JSONResponse(processing.start(query,request),status_code=202,headers={'Cache-Control':'no-store'})


@app.get('/processing/jobs/{identifier}')
async def processing_status(identifier:str,request:Request):
    return JSONResponse(processing.public(processing.owned(identifier,request)),headers={'Cache-Control':'no-store'})


@app.get('/processing/jobs')
async def processing_archive(request:Request):
    from . import processing_repository as repository
    owner,_=work_sessions.identity(request)
    rows=[]
    for identifier in repository.owned_ids(owner):
        try:
            j=processing.owned(identifier,request)
            value=processing.public(j)
            rows.append({k:value.get(k) for k in ('job_id','status','created_at','input','artifact','retention')})
        except HTTPException:continue
    return JSONResponse({'jobs':rows},headers={'Cache-Control':'no-store'})


@app.post('/processing/jobs/{identifier}/cancel')
async def processing_cancel(identifier:str,request:Request):
    work_sessions.protect(request)
    return JSONResponse(processing.cancel(identifier,request),headers={'Cache-Control':'no-store'})


@app.get('/processing/jobs/{identifier}/download')
async def processing_download(identifier:str,request:Request):
    return processing.download_response(identifier,request)


@app.get('/catalog')
def catalog():
    return {'providers': PROVIDERS, 'collections': COLLECTION_REGISTRY, 'profiles': CATALOG,
            'platforms': PLATFORMS, 'sensors': SENSORS, 'products': PRODUCTS, 'unconnected_candidates': CANDIDATES,
            'notice': '발견된 컬렉션은 자동 추천·연결하지 않습니다. 등록 제품만 검토된 후보이며 전체 위성 목록이 아닙니다.'}


@app.get('/catalog/discover/{provider_id}')
async def catalog_discover(provider_id: str):
    return await discover(provider_id)


@app.post('/selection-overlap')
def selection_overlap(query: SelectionRequest):
    return common_footprint(query)


@app.post('/analysis-conditions')
async def analysis_conditions(query: ConditionsRequest):
    return await inspect_conditions(query)


@app.post('/pixel-quality')
async def pixel_quality(query: PixelQualityRequest):
    return await inspect_pixels(query)


@app.post('/change-analysis')
async def change_analysis(query: ChangeRequest):
    return JSONResponse(await inspect_pixels(query,mode='ndvi_change'),headers={'Cache-Control':'no-store'})


@app.get('/request/config')
def interpretation_config():
    return JSONResponse(public_status(),headers={'Cache-Control':'no-store'})


@app.post('/request/interpret')
async def interpret_request(query: InterpretRequest, request: Request):
    # Condition input never invokes the legacy keyword/date interpreter, even
    # when an older client sends interpretation_mode=rules.
    result={} if query.resolve_conditions else interpret(query)
    if query.resolve_conditions:
        task=asyncio.create_task(propose_with_ai(query.purpose,query.condition_region_id))
        try:
            while not task.done():
                if await request.is_disconnected():
                    task.cancel()
                    return Response(status_code=499)
                await asyncio.sleep(0.05)
            result['condition_proposals']=await task
            result['condition_proposals']['engine']['usage']=public_status()['usage']
        finally:
            if not task.done():task.cancel()
    return JSONResponse(result,headers={'Cache-Control':'no-store'})


@app.post('/cloud/plan')
async def cloud_plan(query: CompositePlanRequest,request:Request):
    work_sessions.protect(request)
    owner,cookie=work_sessions.identity(request,True)
    result=await make_plan(query)
    if result.get('plan_id') in PLANS:PLANS[result['plan_id']]['owner']=owner
    return work_sessions.attach(JSONResponse(result,headers={'Cache-Control':'no-store'}),request,cookie)


@app.post('/cloud/jobs')
async def cloud_start(query: CompositeStartRequest,request:Request):
    work_sessions.protect(request);work_sessions.require_owner(request,PLANS.get(query.plan_id,{}))
    return JSONResponse(start_job(query.plan_id,query.confirmation_digest),status_code=202,headers={'Cache-Control':'no-store'})


@app.get('/cloud/jobs/{job_id}')
async def cloud_status(job_id:str,request:Request):
    job=get_job(job_id);work_sessions.require_owner(request,job)
    return JSONResponse(public_job(job),headers={'Cache-Control':'no-store'})


@app.post('/cloud/jobs/{job_id}/cancel')
async def cloud_cancel(job_id:str,request:Request):
    work_sessions.protect(request);work_sessions.require_owner(request,get_job(job_id))
    return JSONResponse(cancel_job(job_id),headers={'Cache-Control':'no-store'})


@app.get('/cloud/jobs/{job_id}/download')
async def cloud_download(job_id:str,request:Request):
    job=get_job(job_id);work_sessions.require_owner(request,job)
    if job['status']!='succeeded' or not job['artifact']:
        return JSONResponse(status_code=409,content={'error':{'code':'NOT_READY','message':'완료된 실제 합성 파일이 없습니다.'}})
    return Response(content=job['artifact'],media_type='application/zip',headers={
        'Content-Disposition':'attachment; filename="sentinel-2-observed-composite.zip"',
        'Cache-Control':'no-store'})


@app.post('/estimate/plan')
async def estimate_plan(query: CompositePlanRequest,request:Request):
    work_sessions.protect(request)
    owner,cookie=work_sessions.identity(request,True)
    result=await make_plan(query,kind='estimate')
    if result.get('plan_id') in PLANS:PLANS[result['plan_id']]['owner']=owner
    return work_sessions.attach(JSONResponse(result,headers={'Cache-Control':'no-store'}),request,cookie)


@app.post('/estimate/jobs')
async def estimate_start(query: CompositeStartRequest,request:Request):
    work_sessions.protect(request);work_sessions.require_owner(request,PLANS.get(query.plan_id,{}))
    return JSONResponse(start_job(query.plan_id,query.confirmation_digest,kind='estimate'),status_code=202,
                        headers={'Cache-Control':'no-store'})


@app.get('/estimate/jobs/{job_id}')
async def estimate_status(job_id:str,request:Request):
    job=get_job(job_id,kind='estimate');work_sessions.require_owner(request,job)
    return JSONResponse(public_job(job),headers={'Cache-Control':'no-store'})


@app.post('/estimate/jobs/{job_id}/cancel')
async def estimate_cancel(job_id:str,request:Request):
    work_sessions.protect(request);work_sessions.require_owner(request,get_job(job_id,kind='estimate'))
    return JSONResponse(cancel_job(job_id,kind='estimate'),headers={'Cache-Control':'no-store'})


@app.get('/estimate/jobs/{job_id}/download')
async def estimate_download(job_id:str,request:Request):
    job=get_job(job_id,kind='estimate');work_sessions.require_owner(request,job)
    if job['status']!='succeeded' or not job['artifact']:
        return JSONResponse(status_code=409,content={'error':{'code':'NOT_READY','message':'완료된 추정영상 파일이 없습니다.'}})
    return Response(content=job['artifact'],media_type='application/zip',headers={
        'Content-Disposition':'attachment; filename="sentinel-2-local-ml-estimate.zip"',
        'Cache-Control':'no-store'})


@app.post('/search')
async def search(query: SearchRequest):
    rec = recommendation(query)
    if rec['purpose_type'] is None:
        return JSONResponse(status_code=422, content={'error': {'code': 'PURPOSE_REQUIRED', 'message': rec['reasons'][0]}})
    card = next((c for c in rec['cards'] if c['id'] == query.recommendation_id), None)
    if query.recommendation_id and (not card or not card['search_enabled']):
        return JSONResponse(status_code=422, content={'error':{'code':'RECOMMENDATION_UNAVAILABLE','message':'선택한 추천은 현재 목적·관측 조건에서 앱 내 검색을 지원하지 않습니다.'}})
    if not rec['collections'] and not query.collections:
        return JSONResponse(status_code=422, content={'error':{'code':'OBSERVATION_UNSUPPORTED','message':'필수 관측 조건을 충족하며 현재 검색 연결된 후보가 없습니다. 목적을 바꾸지 않고 검색을 중단했습니다.'}})
    collections = list(dict.fromkeys(card['search_conditions']['collections'] if card else query.collections or rec['collections']))
    # Explicit manual reference searches remain possible; never label them as matching recommendations.
    def prepare(raw):
        item=evaluate(normalize(raw), query, rec['purpose_type'])
        if card and not scene_matches_profile(item, rec['purpose_type'], card['id']):return None
        return item
    result = await search_providers(query, collections, prepare)
    update_availability(rec,result)
    items = result['items']
    group_paths(items)
    if rec['purpose_type']=='flood' and not any(i['collection']=='sentinel-1-grd' for i in items):
        for item in items:
            if item['collection']=='sentinel-2-l2a':
                item['purpose_plan'].update(group='primary',group_reason='현재 조회에는 SAR 결과가 없습니다. Sentinel-2는 맑은 시기의 광학 보완 후보이며 SAR 대체 관측량이 아닙니다.')
    items.sort(key=rank_key)
    if not card and query.collections:
        rec['assumptions'].append('직접 선택 검색은 컬렉션 참고 후보를 포함합니다. 목적 관측 조건 충족이나 필수 제품·밴드 확인을 보장하지 않습니다. 추천 카드의 조건 검색을 사용하면 해당 메타데이터 조건으로 거릅니다.')
    response = {**result, 'source': 'live-stac', 'endpoint': STAC_URL,
            'access_guidance':access_guidance(rec['purpose_type']),
            'endpoints': {p:PROVIDERS[p]['endpoint'] for p in result['provider_budgets']}, 'returned': len(items),
            'limit': query.max_items, 'recommendation': rec, 'collections': collections,
            'query': query.model_dump(mode='json'),
            'applied_recommendation': card['id'] if card else None,
            'applied_conditions': card['search_conditions'] if card else None,
            'ranking': '센서 그룹은 목적별 고정 탐색 순서입니다. 영상 순위는 그룹과 독립적으로 필수 밴드 확인 → AOI 기하 중첩 내림차순 → 장면 구름량 오름차순 → 제공 해상도 최솟값 → 시작일 차이 → 컬렉션·ID 순입니다. 누락값은 각 기준에서 마지막입니다. 후보 탐색 규칙이며 픽셀 품질·과학적 적합성 점수가 아닙니다.',
            'notice': f'동일 AOI·UTC 기간으로 제공처를 독립 병렬 검색하고 제공처별 결과를 번갈아 총 {query.max_items}건까지 반환합니다. Earth Search 최대12회, 다른 제공처 각4회; 제공처별45초·회당10초·페이지25건, 재시도 없음. NOAA는 공식 공개 객체 목록을 사용합니다. 미조회 페이지·전역 한도로 미반환한 후보를 상태에 표시합니다. source live-stac은 호환 값이며 STAC 외 결과도 포함할 수 있습니다.'}
    if result['outcome'] == 'failed':
        response['error'] = {'code': 'STAC_ERROR', 'message': '모든 컬렉션 검색에 실패했습니다. 영상 0건으로 확인된 것이 아닙니다.'}
        return JSONResponse(status_code=504 if all(s['reason'] == 'timeout' for s in result['collection_statuses']) else 502, content=response)
    return response
