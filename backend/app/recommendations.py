from .purposes import classify, LABELS
from .purpose_plan import RULES, scene_matches_profile, required_for
from .provider_registry import COLLECTION_REGISTRY
from .sensor_catalog import CATALOG, SOURCES, CHECKED_ON, RULE_VERSION
from .analysis_catalog import BY_ID, ANALYSES, REQUIREMENTS, METHODS

def processing_note(profile_id,purpose):
    collection=CATALOG[profile_id]['collection']
    candidates=[m['label'] for m in METHODS.values() if purpose in m['domains'] and collection in m['collections']]
    return ('제품별 조건 확인 후 '+', '.join(candidates)+' 후보 · 실제 QA/접근/보정은 실행 시 검사') if candidates else '이 제공처·제품의 래스터 처리·픽셀 QA 미지원'


def recommend(text, explicit=None, *, target_size_m=None, observation_need='unspecified', temporal_mode='unspecified', detail_intent=None, requested_resolution_m=None):
    """Existing deterministic rule engine, extended with reviewed instrument/product facts."""
    purpose, matched = classify(text, explicit)
    result = {'purpose_type':purpose, 'label':LABELS.get(purpose,'목적 선택 필요'), 'matched':matched,
              'collections':[], 'reasons':[], 'future':[], 'cards':[], 'assumptions':[],
              'rule_version':RULE_VERSION, 'checked_on':CHECKED_ON, 'observation_requirement':None}
    if purpose is None:
        result['reasons']=['식생·수역·도시·열환경 중 어떤 분석인가요? 목적 직접 선택에서 하나를 골라 주세요.']
        return result
    rule = RULES[purpose]
    result['reasons'] = [rule['reason']]
    detail=BY_ID.get(detail_intent)
    if detail and detail['domain']!=purpose:detail=None
    result['detail_intent']=detail['id'] if detail else None
    result['detail_label']=detail['label'] if detail else None
    if detail:
        result['reasons'].append(f"보존한 세부 의도: {detail['label']} · 필요한 시점 {detail['minimum_scenes']}개 이상. {detail['engine_note']}")
        if detail['comparison'] and temporal_mode=='unspecified':temporal_mode='change'
    result['observation_requirement'] = rule['observation']
    if temporal_mode == 'unspecified':
        temporal_mode = 'change' if any(w in text.lower() for w in ('변화','전후','change')) else 'single'
        result['assumptions'].append('관측 시점 선택 미입력: '+('전후 변화' if temporal_mode=='change' else '한 시점 상태')+'로 가정합니다.')
    if observation_need == 'unspecified':
        if any(w in text.lower() for w in ('야간','밤','night')):
            observation_need = 'night'
            result['assumptions'].append('목적 문구의 야간 표현을 관측 필수 조건으로 반영합니다.')
        else:
            result['assumptions'].append('구름·야간 조건 미입력: 광학·지표온도 후보는 맑은 주간 관측을 가정합니다. 장마·홍수에서는 SAR를 우선 검토합니다.')
    if target_size_m is None:
        result['assumptions'].append('대상 크기 미입력: 객체 식별 가능 크기를 판정하지 않습니다.')
    for profile_id in rule['profiles']:
        profile=CATALOG[profile_id]
        sar=profile['observation']=='SAR'
        required=required_for(purpose, profile_id)
        fit='conditional' if purpose=='flood' and not sar else 'met'
        reason=rule['reason'] if sar or purpose!='flood' else '맑은 시기의 수역 변화 보완 후보입니다. 장마 중 SAR와 동등한 대안이 아닙니다.'
        constraints=list(profile['limitations'])
        if profile_id=='viirs_sr' or profile.get('coarse_reference'):
            fit='conditional'
            if profile.get('coarse_reference'):reason='0.05° 광역 NDVI CDR 참고 후보. 상세 영상·지표온도·침수 관측의 대안이 아닙니다.'
            reason='광역 식생 추적용 일별 반사도 후보입니다. 수백 m 관측이며 상세 식생의 동등 대안이 아닙니다.'
        if observation_need in ('all_weather','night') and not sar:
            fit='not_met'
            constraints.insert(0,'요청한 '+('구름 중' if observation_need=='all_weather' else '야간')+' 관측 필수 조건을 이 제품이 충족하지 못합니다.')
        if temporal_mode=='change':
            constraints.append('전후 촬영일·계절·센서·제품·관측 조건을 맞춰야 하며, 두 시점의 실제 가용성은 아직 확인하지 않았습니다.')
        if target_size_m is not None:
            if profile.get('coarse_reference'):constraints.append('운영 가정: 0.05° 격자의 광역 제품은 작은 대상의 세부 식생 식별에 적합하다고 판단하지 않습니다. 경도 방향 격자 크기는 위도별로 다릅니다.')
            native=max((profile['native_m'].get(b,0) for b in required), default=0)
            if native:
                constraints.append(f'대상 약 {target_size_m:g} m / 필수 밴드 원관측 간격 최대 {native} m. 앱 운영 가정: 대상 폭이 3개 원관측 간격 미만이면 세부 구분을 조건부로 안내합니다. 보편적 식별 기준이 아니며 한 픽셀=객체 식별 가능 크기가 아닙니다.')
                if target_size_m < 3*native and fit=='met': fit='conditional'
            elif not profile.get('coarse_reference'):
                constraints.append('대상 크기와 제품 유효 해상도 비교는 미확인입니다. 관측 모드 해상도를 객체 식별 한계로 간주하지 않습니다.')
        required_bands=[{'name':name,'description':profile['bands'][name]} for name in required]
        if requested_resolution_m is not None:
            native=max((profile['native_m'].get(b,0) for b in required),default=0)
            if native and native>requested_resolution_m:
                fit='not_met';constraints.insert(0,f'요청 해상도 {requested_resolution_m:g}m보다 필수 원관측 간격 {native:g}m가 큽니다. 출력 격자 재표본화로 관측 상세도가 늘지 않습니다.')
            elif not native:constraints.append('요청 해상도와 원관측 간격 비교 미확인. 출력 격자를 원래 해상도로 간주하지 않습니다.')
        card={k:profile[k] for k in ('observation','payload','platform_label','product','collection','native_resolution','output_grid')}
        card.update(id=profile_id, fit={'status':fit,'reason':reason}, required_bands=required_bands,
            provider_id=COLLECTION_REGISTRY[profile['collection']]['provider_id'],
            quality_materials=profile['quality'], constraints=constraints,
            app_support={'search':profile['search_supported'],'processing':processing_note(profile_id,purpose),
                         'download':'원본 Asset 링크 제공 시 연결; 인증·요청자 비용·파일 접근은 별도 확인' if profile['search_supported'] else '미지원: 검색 및 Asset 연결 없음'},
            availability={'status':'unsearched','message':'현재 AOI·기간은 미검색입니다. 영상 존재를 확인하지 않았습니다.','count':None},
            pixel_quality={'status':'not_checked','message':'장면 픽셀 QA 미검사'},
            sources=[SOURCES[key]|{'checked_on':'2026-11-02' if key in ('pc','noaa_ndvi','noaa_nodd','hls') else CHECKED_ON} for key in profile['sources']],rule_version=RULE_VERSION,
            search_enabled=profile['search_supported'] and fit!='not_met',
            search_conditions={'collections':[profile['collection']], 'platforms':profile['platforms'], 'product_levels':profile['levels'], 'required_bands':required} if profile['search_supported'] else None)
        result['cards'].append(card)
        card['analysis_options']=[{'id':a['id'],'label':a['label'],'minimum_scenes':a['minimum_scenes'],
            'data_candidate':all(b in profile['bands'] for b in a['required_variables']),
            'engine_supported':bool(a['engine']) and profile['collection'] in METHODS[a['engine']]['collections'],
            'note':a['engine_note']+' · '+ ' '.join(REQUIREMENTS[a['id']])+(' · 실제 장면/필수 밴드/QA/접근은 검색·검사 후 확인' if a['engine'] else '')}
            for a in ANALYSES if a['domain']==purpose]
        if card['search_enabled'] and profile['collection'] not in result['collections']:result['collections'].append(profile['collection'])
    if purpose=='flood':result['future']=['Sentinel-1 GRD는 실제 검색 지원; SAR 보정·지형 처리·침수 분석은 미지원']
    return result


def update_availability(rec, search_result):
    """Availability is query evidence, independent of purpose suitability and QA."""
    for card in rec['cards']:
        status=next((s for s in search_result['collection_statuses'] if s['collection']==card['collection'] and s.get('provider_id',card['provider_id'])==card['provider_id']),None)
        if status is None:continue
        count=sum(scene_matches_profile(i,rec['purpose_type'],card['id']) for i in search_result['items'])
        if count:
            availability={'status':'searched','count':count,'message':f'조회 범위에서 제품·필수 밴드 메타데이터가 맞는 후보 {count}건. 파일 접근·픽셀 유효성은 미확인입니다.'}
            if not status['complete']:availability['message']+=' 일부 조회는 미완료입니다.'
        elif status['status'] in ('failed','partial'):
            availability={'status':'failed','count':None,'message':'검색/처리 실패로 이 조건의 영상 가용성을 확인하지 못했습니다.'}
        elif status['status']=='outside_scope':
            availability={'status':'outside_scope','count':None,'message':'등록된 기간/목적 지원 범위 밖이어서 조회하지 않았습니다. 영상 0건으로 확인한 것이 아닙니다.'}
        elif status['complete']:
            availability={'status':'none','count':0,'message':'현재 AOI·기간에 제품·필수 밴드 메타데이터가 맞는 후보가 없습니다. 목적을 유지하며 기간을 조정하거나 다른 적합 후보를 검토하세요.'}
        else:
            availability={'status':'unsearched','count':None,'message':'조회 한도·미조회 범위로 이 제품의 가용성은 아직 미확인입니다.'}
        card['availability']=availability
