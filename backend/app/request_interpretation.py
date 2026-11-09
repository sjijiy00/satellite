"""Bounded intent extraction. Existing purpose rules remain the single classifier."""
import re
from .purposes import LABELS


VERSION='workflow-intent-2026-10-29.3'
CLOUD=re.compile(r'구름|흐린|흐림|cloud',re.I)
THIS_SCENE=re.compile(r'이\s*(?:영상|장면)|선택한\s*(?:영상|장면)|this\s+(?:image|scene)',re.I)
COMPARE=re.compile(r'선택한\s*두\s*(?:날짜|영상|장면).*비교|두\s*(?:날짜|영상|장면).*비교',re.I)
MOVE_AOI=re.compile(r'이\s*지역으로\s*이동|선택\s*(?:지역|영역)으로\s*이동',re.I)
SEARCH=re.compile(r'검색|찾아|search|find\s+(?:images|scenes)',re.I)
UNSUPPORTED=re.compile(r'원인|예보|예측|완벽|GAN|침수\s*면적.*계산|지표온도.*계산|산불.*복원',re.I)


def interpret(query):
    text=' '.join(filter(None,(query.purpose,query.followup))).strip()
    purpose,matched=query.purpose_type,[] # initial natural-language extraction is AI-only
    supported_followup=not query.followup.strip() or (not UNSUPPORTED.search(query.followup) and any(
        pattern.search(query.followup) for pattern in (COMPARE,MOVE_AOI,CLOUD,SEARCH)))
    intent=('clarify' if not supported_followup else 'compare' if COMPARE.search(query.followup) else 'move_aoi' if MOVE_AOI.search(query.followup)
            else 'cloud_help' if CLOUD.search(query.followup) else 'search' if purpose else 'clarify')
    temporal=query.temporal_mode
    questions=[];notes=[]
    if not purpose:questions.append('식생·침수/수역·도시·열환경 중 목적을 직접 선택해 주세요.')
    if query.bbox is None:questions.append('지도에서 관심 지역 AOI를 확정해 주세요. 지명은 자동 좌표로 바꾸지 않습니다.')
    if not query.start_date or not query.end_date:questions.append('UTC 시작일과 종료일을 확정해 주세요.')
    if THIS_SCENE.search(query.followup) and not query.selected_scene:questions.append('“이 영상”으로 검사할 장면을 검색 결과에서 선택해 주세요.')
    mentions=[] # no date parsing in command routing
    if query.allow_date_change:notes.append('날짜 변경 허용 표시가 있어도 자동으로 기간을 넓히지 않습니다. 변경 후 다시 확인해야 합니다.')
    else:notes.append('날짜 변경 미허용: 현재 확정 기간 밖 자료를 사용하지 않습니다.')
    if not supported_followup:
        notes.append('이 요청은 지원하지 않습니다. 현재 조건 검색, 선택한 두 날짜 비교, 확정 AOI로 이동, 구름 대응 안내를 사용할 수 있습니다. 분석 목적은 유지합니다.')
    if query.bbox is not None:notes.append('지명과 좌표의 동일성은 자동 검증하지 않습니다. 지도에서 확인한 AOI를 기준으로 합니다.')
    if purpose in ('flood','thermal') and intent=='cloud_help':
        notes.append('현재 실제 합성은 식생 Sentinel-2 L2A 한 시점 기간 요약만 지원합니다. 원래 목적을 바꾸지 않습니다.')
    actions=['search'] if supported_followup and purpose and query.bbox and query.start_date and query.end_date else []
    if intent=='compare' and actions:actions.append('compare')
    if intent=='move_aoi' and query.bbox:actions.append('move_aoi')
    if intent=='cloud_help' and query.selected_scene and actions:
        s2_context = query.selected_scene.collection=='sentinel-2-l2a' and query.selected_scene.provider_id in (None,'earth-search')
        actions.append('cloud_plan' if purpose=='vegetation' and temporal=='single' and s2_context else 'unsupported_cloud_processing')
    result = {'version':VERSION,'intent':intent,'followup_supported':bool(supported_followup),'purpose_type':purpose,'purpose_label':LABELS.get(purpose,'목적 확인 필요'),
            'purpose_evidence':matched,'aoi':list(query.bbox) if query.bbox else None,
            'period':{'start':str(query.start_date) if query.start_date else None,'end':str(query.end_date) if query.end_date else None,'timezone':'UTC'},
            'reference_date':str(query.reference_date) if query.reference_date else None,
            'target_size_m':query.target_size_m,'temporal_mode':query.temporal_mode,'effective_temporal_mode':temporal,
            'observation_need':query.observation_need,'allow_date_change':query.allow_date_change,
            'selected_scene':query.selected_scene.model_dump() if query.selected_scene else None,
            'selected_datetime':query.selected_datetime.isoformat() if query.selected_datetime else None,
            'text_date_mentions':mentions,'questions':questions,'notes':notes,'available_actions':actions,
            'parser_scope':'이미 확정한 목적·기간·AOI를 그대로 사용. 지원하는 후속 작업 명령만 연결하며 날짜·지역·목적을 자유문에서 규칙 추출하지 않음.'}
    return result
