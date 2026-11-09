"""AI-only contract and real local boundary + mock provider. Never real paid AI."""
import asyncio
from copy import deepcopy
import json
import math
import pytest
from fastapi.testclient import TestClient
from pyproj import Geod
from shapely.geometry import shape
from app import main,ai_interpretation as ai,condition_proposals as legacy,admin_boundaries as ab,place_search as geo
from app.ai_conditions import Extraction,conditions
from app.spatial_extent import radius_bbox
from test_ai_interpretation import envelope,VALID

TEXT='2025년 8/15~8/30까지 제주도의 지표면 온도를 알고 싶어'
def value():
    v=deepcopy(VALID);v.update(purpose_type='thermal',purpose_evidence='지표면 온도',analysis_target='지표면 온도',temporal_mode='unspecified',temporal_evidence=None)
    v['dates']=[{'year':2025,'month':8,'day':15,'evidence':'2025년 8/15'},{'year':2025,'month':8,'day':30,'evidence':'8/30'}]
    v['places']=[{'text':'제주도','ambiguous':False}]
    return json.loads(envelope(v)['output'][0]['content'][0]['text'])

@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.setenv('AI_NL_ENABLED','1');monkeypatch.setenv('AI_NL_PROVIDER','openai');monkeypatch.setenv('AI_NL_MODEL','TEST_ONLY_MODEL');monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY_NOT_A_KEY')
    ai.cache.clear();ai.recent.clear();geo.recent.clear();geo.calls=0
    for key in ai.stats:ai.stats[key]='not_called' if key=='last_status' else 0

@pytest.mark.parametrize('mode',[None,'ai','rules'])
def test_default_and_legacy_mode_are_ai_only_without_any_rule_call(monkeypatch,mode):
    def forbidden(*args,**kwargs):raise AssertionError('Legacy parsing must not run')
    for name in ('propose_conditions','proposed_period','proposed_region','extract_places'):monkeypatch.setattr(legacy,name,forbidden)
    monkeypatch.setattr(main,'interpret',forbidden)
    async def send(payload,key):
        assert payload['input']==TEXT and payload['store'] is False and payload['text']['format']['strict']
        assert 'tools' not in payload
        return envelope(value())
    monkeypatch.setattr(ai,'_send',send)
    body={'purpose':TEXT,'resolve_conditions':True}
    if mode:body['interpretation_mode']=mode
    r=TestClient(main.app).post('/request/interpret',json=body)
    p=r.json()['condition_proposals'];assert p['engine']['mode']=='ai' and p['engine']['status']=='succeeded'
    assert p['period']['start']=='2025-08-15' and p['period']['end']=='2025-08-30'
    assert p['fields']['purpose_type']['value']=='thermal' and p['fields']['purpose_type']['evidence']=='지표면 온도'
    assert p['region']['mentioned_text']=='제주도' and 'bbox' not in p['region'] and 'center' not in p['region']

def test_ai_failure_never_fills_or_classifies_text(monkeypatch):
    async def failure(*args):raise TimeoutError()
    monkeypatch.setattr(ai,'_send',failure)
    p=TestClient(main.app).post('/request/interpret',json={'purpose':TEXT,'resolve_conditions':True}).json()['condition_proposals']
    assert p['status']=='failed' and p['period']['status']=='absent' and p['region']['status']=='absent'
    assert 'fields' not in p
    assert TestClient(main.app).post('/recommend',json={'purpose':TEXT}).json()['purpose_type'] is None
    assert TestClient(main.app).post('/search',json={'purpose':TEXT,'bbox':[126.7,36.4,126.71,36.41],'start_date':'2025-08-15','end_date':'2025-08-30'}).json()['error']['code']=='PURPOSE_REQUIRED'

@pytest.mark.parametrize('mutation',[
    lambda v:v.update(coordinates=[126,33]),lambda v:v['places'][0].update(text='서울시'),
    lambda v:v['dates'][1].update(year=2026),lambda v:v['dates'][1].update(day=32),
    lambda v:v.update(resolution_m=-1),lambda v:v.update(max_cloud_cover=101),
])
def test_invalid_schema_dates_source_and_limits_are_rejected(mutation):
    v=value();mutation(v)
    with pytest.raises(ValueError):conditions(Extraction.model_validate(v),TEXT)

def test_relative_and_missing_year_stay_unresolved_and_absent_values_are_null():
    v=value();v['dates']=[{'year':None,'year_evidence':None,'month':7,'day':None,'evidence':'7월','basis':'explicit'}]
    p=conditions(Extraction.model_validate(v),'7월 제주도 지표면 온도')
    assert p['period']['status']=='needs_confirmation' and 'start' not in p['period']
    assert p['fields']['resolution_m']=={'value':None,'evidence':None,'basis':'unspecified'}
    assert p['fields']['target_size_m']['value'] is None and p['fields']['reference_date']['value'] is None
    v['dates']=[];v['relative_date']=True
    assert conditions(Extraction.model_validate(v),'최근 제주도 지표면 온도')['period']['status']=='needs_confirmation'

def test_cloud_resolution_target_and_comparison_have_independent_provenance():
    text=TEXT+' 해상도10m 대상크기50m 구름20% 전후';v=value()
    v.update(resolution_m=10,resolution_evidence='해상도10m',resolution_basis='explicit',target_size_m=50,target_size_evidence='대상크기50m',target_size_basis='explicit',max_cloud_cover=20,cloud_evidence='구름20%',cloud_basis='explicit',temporal_mode='change',temporal_evidence='전후',temporal_basis='explicit')
    p=conditions(Extraction.model_validate(v),text)
    assert p['fields']['resolution_m']['value']==10 and p['fields']['target_size_m']['value']==50
    assert p['event_reference_required'] and p['fields']['reference_date']['value'] is None

@pytest.mark.parametrize('name,code,center',[('서울시','1100000000',[126.978,37.5665]),('제주도','5000000000',[126.53,33.49])])
def test_real_official_boundary_bbox_not_kakao_point(name,code,center):
    p=ab.propose({'name':name,'region_code':code,'admin_level':'시·도','parent':'','center':center})
    assert p['status']=='proposed' and p['polygon_clipping'] is False and p['pixel_area_exceeded'] is True
    meta,raw,g=ab.load_boundary(ab.canonical_name(name))
    assert p['bbox']==list(g.bounds) and shape(raw['geometry']).is_valid
    assert meta['original_crs']=='EPSG:5179' and meta['crs']=='EPSG:4326' and meta['always_xy']
    assert meta['year'].startswith('2025-06-30') and p['bbox'][0]<center[0]<p['bbox'][2]
    if name=='제주도':assert meta['code']=='39' and meta['mois_prefix']=='50' and 1800<meta['area_km2']<1900

@pytest.mark.parametrize('name',['제주','제주도','제주특별자치도'])
def test_jeju_alias_and_wrong_district_not_entire_province(name):
    assert ab.canonical_name(name)=='제주특별자치도'
    assert ab.propose({'name':name,'region_code':'5011000000','admin_level':'시·군·구','parent':'제주특별자치도','center':[126.53,33.49]})['status']=='mismatch'
    assert ab.canonical_name('제주시')=='제주시' and ab.propose({'name':'제주시'})['status']=='unsupported'

def test_parent_query_does_not_accept_first_child_district_as_whole_region():
    doc={'address_name':'제주특별자치도 제주시','address_type':'REGION','x':'126.53','y':'33.49',
        'address':{'region_1depth_name':'제주특별자치도','region_2depth_name':'제주시','region_3depth_name':'','b_code':'5011000000'}}
    assert geo.candidate(doc,'제주도','TEST ONLY') is None

def test_radius_bbox_is_geodesic_with_explicit_extent_and_rejects_invalid_values():
    b=radius_bbox([126.53,33.49],1000);g=Geod(ellps='WGS84')
    for angle in [0,45,90,135,180,225,270,315]:
        x,y,_=g.fwd(126.53,33.49,angle,1000);assert b[0]<=x<=b[2] and b[1]<=y<=b[3]
    for radius in [0,-1,float('nan'),100001]:
        with pytest.raises(ValueError):radius_bbox([126.53,33.49],radius)

def test_point_provider_uses_existing_key_header_and_never_creates_default_radius(monkeypatch):
    monkeypatch.setenv('GEOCODER_ENABLED','1');monkeypatch.setenv('KAKAO_LOCAL_REST_API_KEY','TEST_ONLY_NOT_A_KEY')
    seen=[]
    async def request(place,kind):
        seen.append((place,kind));return 200,{'meta':{'is_end':True},'documents':[{'id':'TEST_ONLY','place_name':'제주공항','address_name':'제주특별자치도 제주시','x':'126.53','y':'33.49'}]}
    monkeypatch.setattr(geo,'_request',request)
    client=TestClient(main.app);p=client.post('/places/search',json={'place':'제주공항','kind':'place'}).json()
    assert p['status']=='resolved' and 'extent' not in p and p['boundary']['status']=='unsupported'
    p=client.post('/places/search',json={'place':'제주공항','kind':'place','radius_m':1000}).json()
    assert p['extent']['bbox']==radius_bbox([126.53,33.49],1000) and seen==[('제주공항','place')]*2
    assert 'TEST_ONLY_NOT_A_KEY' not in json.dumps(p)

@pytest.mark.parametrize('status,expected',[(401,'authentication_failed'),(403,'authentication_failed'),(429,'limited'),(400,'request_rejected'),(503,'provider_unavailable')])
def test_provider_http_reason_is_safe_and_distinct(monkeypatch,status,expected):
    async def rejected(*args):raise ai.ProviderError(status)
    monkeypatch.setattr(ai,'_send',rejected)
    p=asyncio.run(ai.propose_with_ai(TEXT));assert p['engine']['status']==expected and p['status']=='failed'
    assert 'TEST_ONLY_NOT_A_KEY' not in json.dumps(p)
