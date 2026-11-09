"""Reviewed task choices; scientific band/product facts stay in purpose_plan/CATALOG.

This is an input/engine contract, not an AI-generated implementation or a quality
score. Actual processing endpoints still validate canonical data and pixels.
"""
from typing import Literal
from .purpose_plan import RULES

AnalysisId = Literal['vegetation_index','vegetation_change','surface_temperature','hotspots',
                     'temperature_comparison','water_extent','water_change','flood_extent',
                     'landcover_change','urban_index']


def _task(identifier, domain, label, question, count, output, engine=None):
    return dict(id=identifier, domain=domain, label=label, question=question,
                minimum_scenes=count, required_variables=RULES[domain]['required'],
                output=output, engine=engine,
                engine_note='기존 동일 플랫폼·기준선 Sentinel-2 L2A 두 날짜 NDVI 엔진' if engine else '앱 내부 계산 엔진 미구현 · 자료 수집과 외부 GIS 활용만 가능',
                comparison=count>1)


ANALYSES = [
    _task('vegetation_index','vegetation','식생지수 계산 (NDVI)','한 시점의 적색·근적외선 식생 상태는 어떤가요?',1,'단일 시점 지수 지도·GeoTIFF (현재 독립 계산 미지원)'),
    _task('vegetation_change','vegetation','시기별 식생 변화 (NDVI)','두 날짜의 공통 유효 영역에서 NDVI가 얼마나 달라졌나요?',2,'전후·차이 3밴드 GeoTIFF, 공통 유효 마스크, 평균 통계, 처리 JSON ZIP','ndvi_change'),
    _task('surface_temperature','thermal','지표면 온도 분포','관측 시점의 지표면 온도 분포는 어떤가요?',1,'온도 지도·온도 GeoTIFF (앱 계산 미지원)'),
    _task('hotspots','thermal','고온 지역 탐색','어느 곳이 상대적으로 더 뜨거운가요?',1,'온도/기준별 고온 영역·통계 (앱 계산 미지원)'),
    _task('temperature_comparison','thermal','도시·주변 지역 온도 비교','같은 관측의 도시와 주변 지역 지표면 온도는 어떻게 다른가요?',1,'영역별 온도 비교 지도·통계 (앱 계산 미지원)'),
    _task('water_extent','flood','수체 추출','맑은 관측에서 수체 후보가 어디인가요?',1,'수체 지수·마스크 (앱 계산 미지원)'),
    _task('water_change','flood','시기별 수체 변화','두 관측 시점의 수체 범위가 어떻게 달라졌나요?',2,'수체 변화 지도·통계 (앱 계산 미지원)'),
    _task('flood_extent','flood','침수 범위 분석','사건 전후 관측으로 침수 후보를 구분할 수 있나요?',2,'침수 후보·면적·출처 (SAR/침수 계산 미지원)'),
    _task('landcover_change','urban','토지피복·도시 변화','여러 시점의 토지피복이 어떻게 달라졌나요?',2,'피복 분류·변화 지도 (앱 분류 엔진 미구현)'),
    _task('urban_index','urban','도시 지수 검토 (NDBI)','단파적외선·근적외선의 도시 지수 후보는 어떤가요?',1,'NDBI 지도 (앱 계산 미지원, 시가지 확정 분류 아님)'),
]
BY_ID={a['id']:a for a in ANALYSES}
REQUIREMENTS={
 'vegetation_index':['한 시점의 적색·근적외선 반사도와 해당 제품 품질 자료. 단독 NDVI 파일 계산 엔진은 아직 없습니다.'],
 'vegetation_change':['같은 S2 플랫폼·제품 기준선·확인된 보정 계수와 두 날짜 공통 유효 영역. NDVI 차이는 벌채 면적이나 변화 원인의 확정이 아닙니다.'],
 'surface_temperature':['지표온도 처리제품·단위/스케일·품질 자료가 필요합니다. 기온과 다른 관측량입니다.'],
 'hotspots':['온도 제품 외에 고온의 기준·비교 영역/시점을 정해야 합니다. 임계값을 임의 생성하지 않습니다.'],
 'temperature_comparison':['서로 구분되는 도시/주변 비교 영역을 정해야 합니다. 같은 관측의 온도 제품 한 장으로 영역을 비교할 수 있으며 두 촬영일을 강제하지 않습니다. 다중 AOI 통계 엔진은 미구현입니다.'],
 'water_extent':['광학 수체 지수와 추출 기준을 확인해야 합니다. 지수 후보만으로 침수를 확정하지 않습니다.'],
 'water_change':['동일 관측량·호환 제품의 다른 날짜와 공통 영역/품질 조건이 필요합니다.'],
 'flood_extent':['사건 기준일 또는 전·후 기간 확인이 필요합니다. SAR 후방산란은 광학 반사도와 다르며 SAR 보정·침수 엔진은 미연결입니다.'],
 'landcover_change':['분류 체계·학습/검증용 정답 자료·시기별 호환 입력을 정해야 합니다. 기본 도시 밴드 후보만으로 피복 분류를 완성하지 않습니다.'],
 'urban_index':['NDBI와 시가지/토지피복 분류는 다릅니다. 나지 혼동과 계절/품질 검토가 필요합니다.'],
}


def catalog():
    return {'version':'detail-flow-2','processing_contract_version':'products-2','domains':[{'id':k,'label':v['label']} for k,v in RULES.items()],
            'analyses':[{**a,'additional_requirements':REQUIREMENTS[a['id']],'preprocessing':preprocessing(a),'execution':execution(a)} for a in ANALYSES],
            'processing_methods':list(METHODS.values()),'product_matrix':PRODUCT_MATRIX,'product_sources':PRODUCT_SOURCES,'checked_on':PRODUCT_CHECKED_ON,
            'notice':'계산 엔진 지원과 메타데이터 후보 적합성은 별개입니다. 원본/품질/보정/격자 조건은 실행 서버가 다시 검사합니다.'}


def preprocessing(task):
    """Explain method-specific existing operations; do not enqueue any work."""
    domain=task['domain'];change=task['comparison'];supported=bool(task['engine'])
    def step(id,label,need,reason,engine=None):
        return dict(id=id,label=label,requirement=need,reason=reason,engine=engine)
    return [
        step('crop','관심지역 범위 읽기','required','확정 AOI를 서버에서 범위 읽기합니다. 공통 처리의 명시 확인한 polygon 클리핑을 지원하며, 기존 경로는 bbox 처리입니다. 임의 제품의 독립 자르기 도구는 없습니다.',task['engine'] if supported else None),
        step('qa','구름·그림자·NoData 마스킹','required','가려진 픽셀을 제외하며 원래 지표를 복원하지 않습니다. S2는 SCL, 다른 제품 QA를 SCL로 대체하지 않습니다.',task['engine'] if supported else 's2_single_quality' if domain=='vegetation' and not change else None),
        step('scale','제품별 scale·offset·단위 확인','required','제공처의 보정 계수만 검증해 적용합니다. 이미 L2 보정된 제품에 대기 보정을 반복하지 않습니다.',task['engine'] if supported else None),
        step('grid','좌표계·공통 격자 정렬','required' if change else 'unnecessary','비교 날짜의 공통 격자를 맞춥니다. 임의 CRS/해상도 변환 도구는 없습니다.' if change else '독립적인 격자 변경을 강제하지 않습니다. 실행하는 QA/합성 엔진의 고정 격자·재표본화는 해당 처리 계획에서 확인합니다.',task['engine'] if supported else None),
        step('thermal_ml','ML 구름 결측 추정 · 실측 아님','optional' if task['id']=='surface_temperature' else 'unnecessary','맑은 영역의 공간 검증과 기준선 개선을 통과할 때만 추정합니다. 추정·실측·미해결 픽셀과 검증 오차를 분리합니다.','thermal_ml' if task['id']=='surface_temperature' else None),
        step('thermal_cloud','구름 제거 전처리 · 다른 날짜 관측 보충','optional' if task['id']=='surface_temperature' else 'unnecessary','같은 Landsat L2SP 두 날짜의 실제 QA를 적용해 구름·그림자·구름 인접 결측만 보충합니다. 원래 날짜의 온도 복원이 아닙니다.','thermal_gapfill' if task['id']=='surface_temperature' else None),
        step('composite','다중 시기 실제 관측 합성','optional' if domain=='vegetation' and not change else 'unnecessary','식생 한 시점·동일 S2 플랫폼의 제한된 관측 선택 ZIP만 지원합니다. 날짜/출처를 남기며 두 시점 변화 입력으로 자동 연결하지 않습니다.','observed_composite' if domain=='vegetation' and not change else None),
        step('ml','ML 추정 (실측 아님)','optional' if domain=='vegetation' and not change else 'unnecessary','실측 합성 뒤 확인된 결측이 남고 기존 검증 조건을 통과할 때만 명시 선택합니다. 범용 복원/자동 실행은 없습니다.','local_ridge' if domain=='vegetation' and not change else None),
    ]


# Runtime contracts, not a second recommendation system. Scientific variables
# still come from RULES; provider paths are deliberately narrower than products.
QA_VERSION='s2-l2a-qa-2026-10-29.1'
def _method(id,label,engine,domains,minimum,maximum,area,keys,artifacts):
    return dict(id=id,label=label,engine=engine,domains=domains,
        providers=['earth-search'],collections=['sentinel-2-l2a'],levels=['S2MSI2A','L2A'],
        required_variables=keys,required_qa=['scl'],qa_policy_version=QA_VERSION,
        minimum_scenes=minimum,maximum_scenes=maximum,
        temporal={'utc':True,'maximum_days':31 if maximum==4 else 366,'distinct_dates':minimum>1,
                  'same_platform':id!='s2_quality','same_baseline':id!='s2_quality'},
        spatial={'maximum_aoi_km2':area,'resolution_m':20,'maximum_grid_pixels':150000 if area>25 else 100000,
                 'polygon':id in ('s2_quality','ndvi_change'),'tile_edge':160 if area>25 else None,'maximum_tiles':16 if area>25 else 1},
        artifacts=artifacts,artifact_specs={name:artifact_spec(name) for name in artifacts if name.endswith('.tif')},unsupported_reason='다른 제공처·제품의 QA/보정/처리 엔진은 검증되지 않았습니다.',
        source_mode='canonical_server_range',browser_download_required=False)

def artifact_spec(name):
    if name in ('valid_mask.tif','exclusion_mask.tif','pixel_status.tif'):
        return {'bands':1,'dtype':'uint8','nodata':0,'unit':'1'}
    if name in ('source_index.tif','donor_index.tif'):
        return {'bands':1,'dtype':'uint16','nodata':0,'unit':'1'}
    if name in ('source_date.tif','donor_date.tif'):
        return {'bands':1,'dtype':'int32','nodata':-2147483648,'unit':'UTC days since 1970-01-01'}
    return {'bands':3,'dtype':'float32','nodata':-9999,'unit':'1'}

METHODS={m['id']:m for m in [
 _method('s2_quality','실제 AOI 품질·마스크 내보내기','s2_quality',['vegetation','flood','urban'],1,2,50,
         {'vegetation':RULES['vegetation']['required'],'flood':RULES['flood']['required'],'urban':RULES['urban']['required']},
         ['valid_mask.tif','exclusion_mask.tif','manifest.json']),
 _method('ndvi_change','두 날짜 NDVI 변화','ndvi_change',['vegetation'],2,2,50,RULES['vegetation']['required'],
         ['ndvi_change.tif','valid_mask.tif','exclusion_mask.tif','manifest.json']),
 _method('observed_composite','실제 관측 픽셀 합성','observed_composite',['vegetation'],2,4,25,['red','nir','green'],
         ['analysis_bands.tif','valid_mask.tif','source_index.tif','source_date.tif','exclusion_mask.tif','manifest.json']),
 _method('local_ridge','제한 ML 추정 · 실측 아님','local_ridge',['vegetation'],2,4,25,['red','nir','green'],
         ['target_observed.tif','estimated_only.tif','estimate_with_observed.tif','pixel_status.tif','donor_index.tif','donor_date.tif','valid_mask.tif','exclusion_mask.tif','manifest.json'])]}

def execution(task):
    methods=['s2_quality'] if task['domain']!='thermal' else []
    if task['id']=='surface_temperature':methods+=['thermal_gapfill','thermal_ml']
    if task['id']=='vegetation_change':methods+=['ndvi_change']
    if task['id']=='vegetation_index':methods+=['observed_composite','local_ridge']
    if task['id'] in TASK_METHODS:methods.insert(0,TASK_METHODS[task['id']])
    return {'analysis_engine':task['engine'],'analysis_supported':bool(task['engine']),
            'legacy_spatial':{'maximum_aoi_km2':25,'resolution_m':20},
            'method_ids':methods,'methods':[METHODS[id] for id in methods],'required_variables':task['required_variables'],
            'required_qa':['scl'] if methods and task['id'] not in TASK_METHODS else [],'minimum_scenes':task['minimum_scenes'],
            'providers':list(dict.fromkeys(p for id in methods for p in METHODS[id]['providers'])) if task['engine'] else [],
            'collections':list(dict.fromkeys(p for id in methods for p in METHODS[id]['collections'])) if task['engine'] else [],
            'unsupported_reason':None if task['engine'] else task['engine_note'],
            'additional_inputs':REQUIREMENTS[task['id']]}

# Product eligibility is declared once here and revalidated by product_policy.
from .product_policy import products,VARIABLES,THERMAL,SOURCES as PRODUCT_SOURCES,CHECKED_ON as PRODUCT_CHECKED_ON,QA_VERSION as PRODUCT_QA
TASK_METHODS={'vegetation_index':'ndvi','water_extent':'mndwi','water_change':'mndwi_change','urban_index':'ndbi',
              'surface_temperature':'surface_temperature','hotspots':'hotspots','temperature_comparison':'temperature_comparison'}
PRODUCT_MATRIX={id:products(method) for id,method in TASK_METHODS.items()}
for _task_id,_method_id in TASK_METHODS.items():
    _thermal=_method_id in THERMAL;_many=_method_id=='mndwi_change';_products=products(_method_id)
    _files=[('temperature.tif' if _thermal else _method_id+'.tif'),'valid_mask.tif','exclusion_mask.tif','manifest.json']
    if _thermal:_files+=['temperature_quality.tif']
    if _method_id=='hotspots':_files+=['hotspots.tif']
    if _method_id in ('mndwi','mndwi_change'):_files+=['water_change.tif' if _many else 'water_candidates.tif']
    _specs={f:artifact_spec(f) for f in _files if f.endswith('.tif')}
    for _name in _specs:
        if _name in ('water_candidates.tif','water_change.tif','hotspots.tif'):_specs[_name]={'bands':1,'dtype':'uint8','nodata':0,'unit':'1'}
        elif _name=='temperature.tif':_specs[_name]={'bands':2,'dtype':'float32','nodata':-9999,'units':['K','degC']}
        elif _name=='temperature_quality.tif':_specs[_name]={'bands':2,'dtype':'float32','nodata':-9999,'units':['K','km']}
        elif _name not in ('valid_mask.tif','exclusion_mask.tif'):_specs[_name]={'bands':3 if _many else 1,'dtype':'float32','nodata':-9999,'unit':'1'}
    METHODS[_method_id]=dict(id=_method_id,label=BY_ID[_task_id]['label'],engine=_method_id,domains=[BY_ID[_task_id]['domain']],
        providers=list(dict.fromkeys(p['provider_id'] for p in _products)),collections=[p['collection'] for p in _products],
        levels=['L2SP'] if _thermal else ['S2MSI2A','L2A','L2SR','L2SP'],products=_products,required_variables=VARIABLES[_method_id],
        required_qa=[],qa_policy_version=PRODUCT_QA,minimum_scenes=2 if _many else 1,maximum_scenes=2 if _many else 1,
        temporal={'utc':True,'maximum_days':366,'distinct_dates':_many,'same_platform':_many,'same_baseline':_many},
        spatial={'maximum_aoi_km2':50 if _many else 200,'resolution_m':30 if _thermal else 20,'resolution_by_collection':{p['collection']:p['resolution_m'] for p in _products},
                 'maximum_grid_pixels':150000 if _many else 600000,'polygon':True,'tile_edge':None if _many else 160,'maximum_tiles':1 if _many else 36},
        artifacts=_files,artifact_specs=_specs,unsupported_reason='제품별 allowlist·필수 밴드/QA·보정값을 확인하세요. PC S2/HLS/VIIRS/SAR는 이 계산의 실행 대상이 아닙니다.',
        source_mode='canonical_server_range',browser_download_required=False,
        inputs={'threshold':_method_id in ('mndwi','mndwi_change','hotspots'),'threshold_unit':'degC' if _method_id=='hotspots' else '1',
                'comparison_regions':2 if _method_id=='temperature_comparison' else 0,'thermal_qa':_thermal},
        caveats=['수역 후보이며 침수 확정이 아닙니다. 임계값 민감도/현장 검증이 필요합니다.'] if _method_id.startswith('mndwi') else
            ['나지/시가지가 혼동되며 토지피복 확정 분류가 아닙니다.'] if _method_id=='ndbi' else
            ['지표면 온도이며 기온이 아닙니다. 구름 주변 오차·ASTER 방사율 결측이 남을 수 있습니다. 100 m 열관측을 30 m 상세 관측으로 해석하지 않습니다.'] if _thermal else ['식생지수이며 식생 종류/원인 확정이 아닙니다.'])
    BY_ID[_task_id].update(engine=_method_id,engine_note='제품별 canonical 범위 읽기·실제 QA 후 공통 GeoTIFF/마스크/manifest 출력',
        required_variables=VARIABLES[_method_id],output='실제 '+('Kelvin/섭씨 온도·품질' if _thermal else _method_id.upper())+' GeoTIFF·유효/제외 마스크·manifest·지도')
    REQUIREMENTS[_task_id]=METHODS[_method_id]['caveats']+(['사용자가 확정한 임계값과 근거가 필요합니다.'] if METHODS[_method_id]['inputs']['threshold'] else [])+(['서로 겹치지 않는 확정 비교 영역 두 개가 필요합니다.'] if _method_id=='temperature_comparison' else [])


from copy import deepcopy
METHODS['thermal_gapfill']=deepcopy(METHODS['surface_temperature'])
_fill=METHODS['thermal_gapfill']
_fill.update(id='thermal_gapfill',engine='thermal_gapfill',label='구름 제거 전처리 · 다른 날짜 관측으로 채우기',minimum_scenes=2,maximum_scenes=2,
    temporal={'utc':True,'maximum_days':31,'distinct_dates':True,'same_platform':True,'same_baseline':True},
    caveats=['영상 1은 대상 날짜, 영상 2는 보충 날짜입니다. 같은 Landsat 위성·L2SP, 31일 이내만 지원합니다.',
             '구름·그림자·구름 거리 기준으로 제외된 곳만 보충 날짜의 QA 통과 온도로 채웁니다. 대상 날짜의 구름 아래 온도 복원이 아니며 날짜가 혼합됩니다. 남은 결측은 유지합니다.'])
_fill['artifacts']=['target_temperature.tif','filled_only.tif','multi_date_temperature.tif','pixel_status.tif','source_index.tif','source_date.tif','valid_mask.tif','exclusion_mask.tif','manifest.json']
_fill['artifact_specs']={f:({'bands':2,'dtype':'float32','nodata':-9999,'units':['K','degC']} if f in ('target_temperature.tif','filled_only.tif','multi_date_temperature.tif') else artifact_spec(f)) for f in _fill['artifacts'] if f.endswith('.tif')}


METHODS['thermal_ml']=deepcopy(METHODS['thermal_gapfill'])
_ml=METHODS['thermal_ml']
_ml.update(id='thermal_ml',engine='thermal_ml',label='ML 구름 결측 추정 · 검증 통과 시만 생성',
    caveats=['대상 영상과 같은 위성의 참조 영상이 필요합니다. 맑은 공통 픽셀로 국소 ridge 모델을 학습합니다.',
             '공간 4분할·120m 완충 검증: RMSE ≤2K, MAE ≤1.5K, 절대오차 95백분위 ≤4K. 단순 복사보다 RMSE 10%, 편향 보정 복사보다 5% 이상 개선해야 합니다.',
             '맑은 검증 픽셀의 오차이며 구름 아래 실제 정확도 보장이 아닙니다. 검증 실패·학습 부족이면 추정 파일을 만들지 않습니다.'])
_ml['spatial'].update(maximum_aoi_km2=25,maximum_grid_pixels=100000,tile_edge=None,maximum_tiles=16)
_ml['artifacts']=['target_temperature.tif','estimated_only.tif','estimate_with_observed.tif','pixel_status.tif','donor_index.tif','donor_date.tif','valid_mask.tif','exclusion_mask.tif','manifest.json']
_ml['artifact_specs']={f:({'bands':2,'dtype':'float32','nodata':-9999,'units':['K','degC']} if f in ('target_temperature.tif','estimated_only.tif','estimate_with_observed.tif') else artifact_spec(f)) for f in _ml['artifacts'] if f.endswith('.tif')}
