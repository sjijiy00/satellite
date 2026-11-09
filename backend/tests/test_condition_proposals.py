"""Calendar/date and sourced geographic extent tests. No imagery/provider requests."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import condition_proposals as cp


@pytest.mark.parametrize('text,start,end',[
    ('2026년 7월 충남의 집중호우 전후 침수범위를 분석하고 싶어.','2026-07-01','2026-07-31'),
    ('2024년 2월 식생','2024-02-01','2024-02-29'),
    ('2026년 2월','2026-02-01','2026-02-28'),
    ('1900년 2월','1900-02-01','1900-02-28'),
    ('2000년 2월','2000-02-01','2000-02-29'),
    ('2100년 2월','2100-02-01','2100-02-28'),
    ('2026-07','2026-07-01','2026-07-31'),
    ('2026년 4월','2026-04-01','2026-04-30'),
    ('2026년 12월','2026-12-01','2026-12-31'),
    ('2026년 7월 9일','2026-07-09','2026-07-09'),
    ('2026-07-02부터 2026-07-14까지','2026-07-02','2026-07-14'),
    ('2025년 12월부터 2026년 2월까지','2025-12-01','2026-02-28'),
    ('2025년 8/15~8/30까지 서울시의 지표면온도를 알고 싶어','2025-08-15','2025-08-30'),
    ('2025년 8월 15일부터 9월 2일까지','2025-08-15','2025-09-02'),
    ('2024년 2/28~2/29까지','2024-02-28','2024-02-29'),
])
def test_calendar_without_timezone_conversion(text,start,end):
    p=cp.proposed_period(text)
    assert p['status']=='resolved' and (p['start'],p['end'])==(start,end)


@pytest.mark.parametrize('text',['7월 식생','2026년 2월 30일','2026년 13월','최근 2026년 7월',
    '2026년 7월 12일부터 2026년 7월 1일까지','2024년 1월부터 2026년 7월까지','2026년 7월 1일부터 31일까지',
    '2026년 6월과 2026년 7월 비교','2026년 7월부터','2026-07-01 ~','2026년 7월 999일','2026년 7월 12',
    '2025년 12/30~1/2까지','2025년 8/30~8/15까지','2025년 8/15~2/30까지','2025년 8/15~8/30~9/2'])
def test_uncertain_dates_never_partially_apply(text):
    p=cp.proposed_period(text)
    assert p['status']=='needs_confirmation' and 'start' not in p


def test_condition_api_no_longer_uses_legacy_rules(monkeypatch):
    from app import ai_interpretation as ai
    monkeypatch.setenv('AI_NL_ENABLED','0')
    def forbidden(*args,**kw):raise AssertionError('Legacy rules must not run')
    monkeypatch.setattr(cp,'propose_conditions',forbidden)
    p=TestClient(app).post('/request/interpret',json={'purpose':'2026년 7월 충남의 집중호우 전후 침수범위를 분석하고 싶어.','resolve_conditions':True,'interpretation_mode':'rules'}).json()['condition_proposals']
    assert p['status']=='failed' and p['engine']['mode']=='ai' and p['period']['status']=='absent'


def test_short_range_api_requires_ai_not_rule_fallback(monkeypatch):
    monkeypatch.setenv('AI_NL_ENABLED','0')
    p=TestClient(app).post('/request/interpret',json={'purpose':'2025년 8/15~8/30까지 서울시의 지표면온도를 알고 싶어','resolve_conditions':True}).json()['condition_proposals']
    assert p['status']=='failed' and p['region']['status']=='absent'


def test_absent_fields_are_not_proposed():
    assert cp.propose_conditions('2026년 7월 식생')['region']['status']=='absent'
    assert cp.propose_conditions('충남의 식생')['period']['status']=='absent'
    assert cp.proposed_region('충남 도시 변화')['name']=='충청남도'


def test_ambiguous_candidates_and_explicit_selection():
    p=cp.proposed_region('충남 또는 상주시의 식생')
    assert p['status']=='ambiguous' and len(p['candidates'])==2 and 'bbox' not in p
    assert cp.proposed_region('충남 또는 상주시의 식생','sangju')['id']=='sangju'
    assert cp.proposed_region('광주의 식생')['status']=='ambiguous'
    assert cp.proposed_region('광주의 식생','gwangju-gyeonggi')['status']=='unsupported'
    assert cp.proposed_region('충남의 식생','sangju')['status']=='unsupported'


@pytest.mark.parametrize('text',['충남 천안시 침수','충남 태안의 식생','서울의 식생','아틀란티스 침수'])
def test_unsupported_place_never_uses_parent_or_example(text):
    r=cp.proposed_region(text)
    assert r['status']=='unsupported' and 'bbox' not in r


def test_catalog_failure_is_not_a_mock_region(monkeypatch):
    def broken():raise OSError('TEST ONLY unreadable catalog')
    monkeypatch.setattr(cp,'load_catalog',broken)
    p=cp.propose_conditions('2026년 7월 충남')
    assert p['period']['status']=='resolved' and p['region']['status']=='failed'
    assert 'bbox' not in p['region'] and p['status']=='partial'


def test_invalid_camera_extent_is_not_clipped(monkeypatch):
    original=cp.load_catalog();original['regions'][0]['extents_dms'][0]=[190,0,0]
    monkeypatch.setattr(cp,'load_catalog',lambda:original)
    r=cp.proposed_region('충남')
    assert r['status']=='unsupported' and 'bbox' not in r


def test_yeongcheon_historic_name_only_proposes_camera():
    p=cp.propose_conditions('영천군의 2025년 8월 식생상태 확인')
    assert p['period']['start']=='2025-08-01' and p['period']['end']=='2025-08-31'
    assert p['region']['id']=='yeongcheon' and p['region']['role']=='camera_only'
    assert 'bbox' not in p['region'] and '1995' in p['region']['note']
    assert p['region']['view_bbox']==[128.694722,35.834166,129.145,36.181667]
