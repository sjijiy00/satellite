"""Rule-scoped request interpretation; TEST_ONLY context never changes the AOI or dates."""
from fastapi.testclient import TestClient
from app.main import app

BASE={'purpose_type':'vegetation','temporal_mode':'single','purpose':'2021년 7월 식생 상태를 확인하고 싶다','followup':'이 영상은 구름이 너무 많아. 분석할 수 있게 해줘',
      'bbox':[126.70,36.40,126.71,36.41],'start_date':'2021-07-01','end_date':'2021-07-31',
      'selected_scene':{'collection':'sentinel-2-l2a','id':'TEST_ONLY_1'},
      'selected_datetime':'2021-07-16T02:00:00Z'}


def test_cloud_intent_keeps_confirmed_context_and_default_date_rule():
    d=TestClient(app).post('/request/interpret',json=BASE).json()
    assert d['intent']=='cloud_help' and d['purpose_type']=='vegetation'
    assert d['aoi']==BASE['bbox'] and d['period']=={'start':'2021-07-01','end':'2021-07-31','timezone':'UTC'}
    assert d['selected_scene']['id']=='TEST_ONLY_1' and d['effective_temporal_mode']=='single'
    assert d['allow_date_change'] is False and 'cloud_plan' in d['available_actions']
    assert d['questions']==[]


def test_relative_date_and_missing_scene_require_clarification():
    d=TestClient(app).post('/request/interpret',json=BASE|{'followup':'최근 이 영상의 구름을 줄여줘','selected_scene':None}).json()
    assert len(d['questions'])==1 and 'cloud_plan' not in d['available_actions']
    assert d['period']['start']=='2021-07-01'


def test_named_region_without_map_never_geocodes_and_ambiguous_purpose():
    d=TestClient(app).post('/request/interpret',json={'purpose':'충남의 상태를 보고 싶다','followup':'구름이 많아'}).json()
    assert d['purpose_type'] is None and d['aoi'] is None and d['available_actions']==[]
    assert any('AOI' in q for q in d['questions'])


def test_date_conflict_and_change_analysis_do_not_silently_switch():
    d=TestClient(app).post('/request/interpret',json=BASE|{'purpose':'2025년 7월 식생 변화','temporal_mode':'unspecified'}).json()
    assert d['effective_temporal_mode']=='unspecified' and 'cloud_plan' not in d['available_actions']
    assert d['text_date_mentions']==[] # no hidden regex date extraction
    assert d['period']['start']=='2021-07-01'


def test_flood_request_is_not_rewritten_as_vegetation():
    d=TestClient(app).post('/request/interpret',json=BASE|{'purpose':'홍수 지역을 분석','purpose_type':'flood','followup':'이 영상 구름 줄여줘'}).json()
    assert d['purpose_type']=='flood' and 'unsupported_cloud_processing' in d['available_actions']
    assert 'cloud_plan' not in d['available_actions']


def test_bad_confirmed_period_rejected():
    assert TestClient(app).post('/request/interpret',json=BASE|{'start_date':'2021-08-01'}).status_code==422


def test_supported_navigation_intents_keep_confirmed_aoi_and_period():
    client=TestClient(app)
    for text,intent in [('선택한 두 날짜를 비교해','compare'),('이 지역으로 이동해','move_aoi')]:
        result=client.post('/request/interpret',json=BASE|{'followup':text}).json()
        assert result['intent']==intent and intent in result['available_actions']
        assert result['aoi']==BASE['bbox']
        assert result['period']['start']=='2021-07-01'
        assert result['period']['end']=='2021-07-31'


def test_unsupported_followup_never_executes_or_changes_original_purpose():
    client=TestClient(app)
    for text in ['홍수 원인을 AI로 분석해','지표온도 계산해','완벽하게 구름을 복원해','보고서를 이메일로 보내줘']:
        result=client.post('/request/interpret',json=BASE|{'followup':text}).json()
        assert result['followup_supported'] is False and result['intent']=='clarify'
        assert result['available_actions']==[] and result['purpose_type']=='vegetation'
        assert any('지원하지 않습니다' in note for note in result['notes'])


def test_explicit_supported_search_reuses_confirmed_conditions():
    result=TestClient(app).post('/request/interpret',json=BASE|{'followup':'현재 조건으로 검색해'}).json()
    assert result['followup_supported'] and result['intent']=='search'
    assert 'search' in result['available_actions'] and result['aoi']==BASE['bbox']
