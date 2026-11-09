"""TEST ONLY task contract and mock AI extraction; no provider requests/credentials."""
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import ai_interpretation as ai
from app.analysis_catalog import catalog, BY_ID
from app.purpose_plan import RULES
from app.recommendations import recommend
from test_ai_interpretation import envelope, VALID
from copy import deepcopy


def test_task_catalog_is_explicit_about_missing_engines_and_same_band_rules():
    body=TestClient(app).get('/analysis/catalog')
    assert body.status_code==200
    tasks=body.json()['analyses'];assert len(tasks)==10
    assert next(a for a in tasks if a['id']=='temperature_comparison')['minimum_scenes']==1
    assert [a['id'] for a in tasks if not a['engine']]==['flood_extent','landcover_change']
    assert next(a for a in tasks if a['id']=='water_extent')['required_variables']==['green','swir16']
    assert next(a for a in tasks if a['id']=='urban_index')['required_variables']==['swir16','nir']
    temp=next(a for a in tasks if a['id']=='surface_temperature')
    assert next(p for p in temp['preprocessing'] if p['id']=='grid')['requirement']=='unnecessary'
    change=next(a for a in tasks if a['id']=='vegetation_change')
    assert next(p for p in change['preprocessing'] if p['id']=='grid')['requirement']=='required'
    assert next(p for p in change['preprocessing'] if p['id']=='composite')['engine'] is None


@pytest.mark.parametrize('detail,domain',[('surface_temperature','thermal'),('vegetation_change','vegetation'),('flood_extent','flood')])
def test_recommendation_keeps_detail_and_product_limits(detail,domain):
    r=recommend('',domain,detail_intent=detail)
    assert r['detail_intent']==detail and any(BY_ID[detail]['label'] in s for s in r['reasons'])
    assert all(any(o['id']==detail for o in c['analysis_options']) for c in r['cards'])
    if domain=='thermal':assert not any(c['id']=='s2_msi' and c['search_enabled'] for c in r['cards'])
    if detail=='vegetation_change':assert any('전후' in s for c in r['cards'] for s in c['constraints'])


def test_requested_detail_resolution_and_domain_conflicts():
    r=TestClient(app).post('/recommend',json={'purpose_type':'vegetation','detail_intent':'vegetation_change','requested_resolution_m':10}).json()
    coarse=next(c for c in r['cards'] if c['id']=='viirs_sr')
    assert coarse['fit']['status']=='not_met' and not coarse['search_enabled']
    assert TestClient(app).post('/recommend',json={'purpose_type':'vegetation','detail_intent':'surface_temperature'}).status_code==422
    assert TestClient(app).post('/recommend',json={'purpose_type':'vegetation','detail_intent':'invented_engine'}).status_code==422


@pytest.mark.parametrize('text,domain,detail,evidence',[
    ('더운 곳을 보고 싶어','thermal',None,'더운'),
    ('지표면 온도를 보고 싶어','thermal','surface_temperature','지표면 온도'),
    ('식생 변화를 보고 싶어','vegetation','vegetation_change','식생 변화'),
    ('NDVI를 보고 싶어','vegetation','vegetation_index','NDVI'),
    ('무엇을 할 수 있나요',None,None,None),
])
def test_mock_ai_broad_domain_preserves_optional_specific_goal(monkeypatch,text,domain,detail,evidence):
    monkeypatch.setenv('AI_NL_ENABLED','1');monkeypatch.setenv('AI_NL_PROVIDER','openai');monkeypatch.setenv('AI_NL_MODEL','TEST_ONLY_MODEL');monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY_NOT_A_KEY')
    ai.cache.clear();ai.recent.clear()
    for key in ai.stats:ai.stats[key]='not_called' if key=='last_status' else 0
    v=deepcopy(VALID);v.update(purpose_type=domain,purpose_evidence=evidence,purpose_basis='explicit' if domain else 'unspecified',analysis_target=None,analysis_target_basis='unspecified',temporal_mode='unspecified',temporal_evidence=None,temporal_basis='unspecified',dates=[],places=[],request_summary='TEST ONLY 사용자 요청 요약',domain_candidates=[],detail_intent=detail,detail_evidence=evidence if detail else None,detail_basis='explicit' if detail else 'unspecified')
    if detail=='vegetation_change':v.update(temporal_mode='change',temporal_evidence='변화',temporal_basis='explicit')
    async def mock(*args):return envelope(v)
    monkeypatch.setattr(ai,'_send',mock)
    p=TestClient(app).post('/request/interpret',json={'purpose':text,'resolve_conditions':True}).json()['condition_proposals']
    assert p['engine']['status']=='succeeded'
    assert p['fields']['purpose_type']['value']==domain and p['fields']['detail_intent']['value']==detail
    assert p['period']['status']=='absent' and p['request_summary']==v['request_summary']
    if detail=='vegetation_change':assert p['event_reference_required'] is False


def test_detail_grounding_and_domain_validation():
    from app.ai_conditions import Extraction,conditions
    v=json.loads(envelope(VALID)['output'][0]['content'][0]['text'])
    v.update(detail_intent='surface_temperature',detail_evidence='식생상태',detail_basis='explicit')
    with pytest.raises(ValueError):conditions(Extraction.model_validate(v),'영천군의 2025년 8월 식생상태 확인')
    v.update(purpose_type='thermal',detail_evidence='invented substring')
    with pytest.raises(ValueError):conditions(Extraction.model_validate(v),'영천군의 2025년 8월 식생상태 확인')
