"""TEST ONLY provider fixtures. No actual Kakao or OpenAI keys/calls."""
import asyncio
from copy import deepcopy
import json
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import place_search as geo, ai_interpretation as ai

DOC={'address_type':'REGION','address_name':'경기도 연천군','x':'127.0746','y':'38.0964',
     'address':{'region_1depth_name':'경기도','region_2depth_name':'연천군','region_3depth_name':'','b_code':'4180000000'}}

def test_province_abbreviation_and_village_match():
    doc=deepcopy(DOC)
    doc.update(address_name='충남 청양군 화성면 장계리',x='126.702371',y='36.409288')
    doc['address'].update(region_1depth_name='충남',region_2depth_name='청양군',region_3depth_name='화성면 장계리')
    assert geo.candidate(doc,'충청남도 청양군 화성면 장계리','TEST') is not None
    assert geo.candidate(doc,'충청남도 보령시','TEST') is None

@pytest.fixture(autouse=True)
def clean(monkeypatch):
    monkeypatch.setenv('GEOCODER_ENABLED','1');monkeypatch.setenv('KAKAO_LOCAL_REST_API_KEY','TEST_ONLY_NOT_A_KEY')
    geo.recent.clear();geo.calls=0

def call(place='연천군',text='2026년 7월 연천군의 지표면온도 분석'):
    return TestClient(app).post('/places/search',json={'text':text,'place':place})

def payload(docs=None,end=True):return {'documents':docs if docs is not None else [deepcopy(DOC)],'meta':{'is_end':end}}

def test_real_schema_center_only_and_not_aoi(monkeypatch):
    async def fake(p):return 200,payload()
    monkeypatch.setattr(geo,'_request',fake)
    r=call();d=r.json();assert r.status_code==200 and d['status']=='resolved'
    assert d['name']=='경기도 연천군' and d['parent']=='경기도' and d['admin_level']=='시·군·구'
    assert d['center']==[127.0746,38.0964] and d['role']=='camera_only'
    assert 'bbox' not in d and 'view_bbox' not in d and d['checked_at']
    assert 'TEST_ONLY_NOT_A_KEY' not in json.dumps(d)

def test_unconfigured_makes_no_request_and_preserves_mention(monkeypatch):
    monkeypatch.delenv('KAKAO_LOCAL_REST_API_KEY')
    async def forbidden(p):raise AssertionError('No request when key is missing')
    monkeypatch.setattr(geo,'_request',forbidden)
    d=call().json();assert d['status']=='not_configured' and d['mentioned_text']=='연천군'
    c=TestClient(app).get('/places/config').json();assert c['ready'] is False and c['missing_settings']==['KAKAO_LOCAL_REST_API_KEY']

@pytest.mark.parametrize('status,expected',[(401,'authentication_failed'),(403,'authentication_failed'),(429,'limited'),(500,'failed'),(302,'failed')])
def test_failures_are_separate(monkeypatch,status,expected):
    async def fake(p):return status,None
    monkeypatch.setattr(geo,'_request',fake)
    d=call().json();assert d['status']==expected and d['http_status']==status and d['mentioned_text']=='연천군'

def test_duplicate_names_and_incomplete_list_need_selection(monkeypatch):
    a=deepcopy(DOC);a.update(address_name='서울특별시 중구');a['address'].update(region_1depth_name='서울특별시',region_2depth_name='중구',b_code='1114000000')
    b=deepcopy(a);b.update(address_name='인천광역시 중구');b['address'].update(region_1depth_name='인천광역시',b_code='2811000000')
    async def fake(p):return 200,payload([a,b,a])
    monkeypatch.setattr(geo,'_request',fake)
    d=call('중구','2026년 중구 분석').json();assert d['status']=='ambiguous' and len(d['candidates'])==2 and 'center' not in d
    async def incomplete(p):return 200,payload(end=False)
    monkeypatch.setattr(geo,'_request',incomplete)
    assert call().json()['status']=='ambiguous'

def test_no_fuzzy_parent_or_poi_substitution(monkeypatch):
    wrong=deepcopy(DOC);wrong['address_name']='경기도';wrong['address']['region_2depth_name']=''
    poi=deepcopy(DOC);poi['address_type']='ROAD_ADDR'
    async def fake(p):return 200,payload([wrong,poi])
    monkeypatch.setattr(geo,'_request',fake)
    assert call().json()['status']=='no_results'

@pytest.mark.parametrize('mode,expected',[('timeout','timeout'),('network','failed'),('schema','invalid_response'),('coordinates','invalid_response')])
def test_invalid_provider_data(monkeypatch,mode,expected):
    async def fake(p):
        if mode=='timeout':raise TimeoutError()
        if mode=='network':raise httpx.ConnectError('TEST ONLY')
        d=payload()
        if mode=='coordinates':d['documents'][0]['x']='999'
        else:d={}
        return 200,d
    monkeypatch.setattr(geo,'_request',fake)
    assert call().json()['status']==expected

def test_grounding_and_extra_urls_rejected_without_request():
    assert call('서울').status_code==422
    assert call('https://example.test','https://example.test').status_code==422
    assert TestClient(app).post('/places/search',json={'text':'연천군','place':'연천군','url':'https://example.test'}).status_code==422

def test_limits_and_no_invented_extent(monkeypatch):
    geo.calls=100;assert call().json()['status']=='limited'
    geo.calls=0;assert call('연천 일대','연천 일대의 온도').json()['status']=='needs_confirmation'

def test_transport_key_in_header_only_no_redirect_no_persistence(monkeypatch):
    seen=[];client_type=httpx.AsyncClient
    async def handler(request):
        seen.append(request)
        return httpx.Response(200,json=payload())
    monkeypatch.setattr(geo.httpx,'AsyncClient',lambda **kw:client_type(transport=httpx.MockTransport(handler),**kw))
    assert call().json()['status']=='resolved'
    assert seen[0].headers['Authorization']=='KakaoAK TEST_ONLY_NOT_A_KEY'
    assert 'TEST_ONLY_NOT_A_KEY' not in str(seen[0].url)
    assert seen[0].url.host=='dapi.kakao.com' and seen[0].url.params['analyze_type']=='similar'

def test_yeoncheon_ai_is_extraction_not_location_success(monkeypatch):
    from test_ai_interpretation import envelope,VALID
    value=deepcopy(VALID);value.update(purpose_type='thermal',purpose_evidence='지표면온도',analysis_target='지표면온도',temporal_evidence='분석')
    value['dates']=[{'year':2026,'month':7,'day':None,'evidence':'2026년 7월'}];value['places']=[{'text':'연천군','ambiguous':False}]
    p=ai._conditions(ai.Extraction.model_validate_json(envelope(value)['output'][0]['content'][0]['text']),'2026년 7월 연천군의 지표면온도를 분석하고 싶어',None)
    assert p['period']['start']=='2026-07-01' and p['period']['end']=='2026-07-31'
    assert p['extraction']['purpose_type']=='thermal' and p['extraction']['places'][0]['text']=='연천군'
    assert p['region']['status']=='lookup_required' and 'center' not in p['region']

def test_ai_cannot_invent_place_or_analysis_target():
    from test_ai_interpretation import VALID,envelope
    value=deepcopy(VALID);value['analysis_target']='기온 (invented)'
    with pytest.raises(ValueError):ai._conditions(ai.Extraction.model_validate_json(envelope(value)['output'][0]['content'][0]['text']),'영천군의 2025년 8월 식생상태 확인',None)

@pytest.mark.parametrize('text',[ '올해 7월 연천군의 식생상태','최근 연천군의 식생상태','지난 장마 연천군의 식생상태 전후'])
def test_relative_and_event_criteria_remain_unconfirmed(text):
    from test_ai_interpretation import VALID,envelope
    # AI marks uncertainty; the server never reparses the whole input with rules.
    value=deepcopy(VALID);value.update(dates=[],relative_date=True,temporal_mode='change' if '전후' in text else 'unspecified',temporal_evidence='전후' if '전후' in text else None)
    value['places']=[{'text':'연천군','ambiguous':False}]
    p=ai._conditions(ai.Extraction.model_validate_json(envelope(value)['output'][0]['content'][0]['text']),text,None)
    assert p['period']['status']=='needs_confirmation' and 'start' not in p['period'] and 'reference_date' not in p
    if '전후' in text:assert p['event_reference_required'] is True

def test_no_date_and_uncertain_area_never_invent_extent():
    from test_ai_interpretation import VALID,envelope
    value=deepcopy(VALID);value.update(dates=[],temporal_mode='unspecified',temporal_evidence=None)
    value['places']=[{'text':'연천','ambiguous':True}]
    p=ai._conditions(ai.Extraction.model_validate_json(envelope(value)['output'][0]['content'][0]['text']),'연천 일대 식생상태',None)
    assert p['period']['status']=='absent' and p['region']['status']=='lookup_required' and 'center' not in p['region']
