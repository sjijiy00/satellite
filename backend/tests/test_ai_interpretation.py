"""TEST ONLY OpenAI transport. Never uses real keys/provider calls."""
import asyncio
from copy import deepcopy
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import ai_interpretation as ai

TEXT='영천군의 2025년 8월 식생상태 확인'
VALID={'purpose_type':'vegetation','purpose_evidence':'식생상태','analysis_target':'식생상태','temporal_mode':'single','temporal_evidence':'상태',
       'dates':[{'evidence':'2025년 8월','year':2025,'month':8,'day':None}],
       'relative_date':False,'places':[{'text':'영천군','ambiguous':False}],'uncertainties':[]}

def envelope(value):
    value=deepcopy(value)
    for key,default in {'request_summary':None,'domain_candidates':[],'detail_intent':None,'detail_evidence':None,'detail_basis':'unspecified'}.items():value.setdefault(key,default)
    for name in ('purpose','analysis_target','temporal','observation','resolution','target_size','cloud'):
        field={'purpose':'purpose_type','temporal':'temporal_mode','observation':'observation_need','cloud':'max_cloud_cover','resolution':'resolution_m','target_size':'target_size_m'}.get(name,name)
        if name in ('observation','resolution','target_size','cloud'):
            value.setdefault(field,'unspecified' if name=='observation' else None)
            value.setdefault(name+'_evidence',None)
        value.setdefault(name+'_basis','explicit' if value.get(field) not in (None,'unspecified') else 'unspecified')
    value.setdefault('reference_date',None);value.setdefault('comparison_periods',[])
    first_year=next((str(d['year']) for d in value.get('dates',[]) if str(d['year']) in d['evidence']),None)
    for d in value.get('dates',[]):d.setdefault('basis','explicit');d.setdefault('year_evidence',first_year)
    for p in value.get('places',[]):
        for k,v in {'evidence':p['text'],'kind':'administrative','spatial_scope':'boundary','radius_m':None,'radius_evidence':None,'basis':'explicit'}.items():p.setdefault(k,v)
    return {'status':'completed','usage':{'input_tokens':100,'output_tokens':50},'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(value,ensure_ascii=False)}]}]}

@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    monkeypatch.setenv('AI_NL_ENABLED','1');monkeypatch.setenv('AI_NL_PROVIDER','openai');monkeypatch.setenv('AI_NL_MODEL','TEST_ONLY_MODEL');monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY_NOT_A_KEY')
    ai.cache.clear();ai.recent.clear()
    for key in ai.stats:ai.stats[key]='not_called' if key=='last_status' else 0


def call(text=TEXT):return TestClient(app).post('/request/interpret',json={'purpose':text,'resolve_conditions':True,'interpretation_mode':'ai'}).json()['condition_proposals']


def test_schema_grounding_month_camera_and_cache(monkeypatch):
    sent=[]
    async def fake(payload,key):sent.append(payload);return envelope(VALID)
    monkeypatch.setattr(ai,'_send',fake)
    p=call();assert p['engine']['status']=='succeeded'
    assert p['period']['start']=='2025-08-01' and p['period']['end']=='2025-08-31'
    assert p['region']['status']=='lookup_required' and p['region']['mentioned_text']=='영천군' and 'bbox' not in p['region']
    assert sent[0]['store'] is False and 'tools' not in sent[0] and sent[0]['text']['format']['strict'] is True
    assert call()['engine']['status']=='cached' and len(sent)==1
    config=TestClient(app).get('/request/config').json()
    assert config['usage']['requests']==1 and config['usage']['input_tokens']==100
    assert 'TEST_ONLY_NOT_A_KEY' not in json.dumps(config)


def test_ai_short_range_uses_grounded_rule_period(monkeypatch):
    value=deepcopy(VALID)
    value['dates']=[{'evidence':'2025년 8/15','year':2025,'month':8,'day':15},
                    {'evidence':'8/30','year':2025,'month':8,'day':30}]
    value['places']=[{'text':'서울시','ambiguous':False}]
    value['purpose_type']='thermal';value['purpose_evidence']='지표면온도'
    value['analysis_target']='지표면온도'
    value['temporal_mode']='single';value['temporal_evidence']='알고 싶어'
    async def fake(*args):return envelope(value)
    monkeypatch.setattr(ai,'_send',fake)
    p=call('2025년 8/15~8/30까지 서울시의 지표면온도를 알고 싶어')
    assert p['engine']['status']=='succeeded'
    assert p['period']['start']=='2025-08-15' and p['period']['end']=='2025-08-30'


def test_ai_short_range_rejects_invented_end_year(monkeypatch):
    value=deepcopy(VALID)
    value['dates']=[{'evidence':'2025년 8/15','year':2025,'month':8,'day':15},
                    {'evidence':'8/30','year':2026,'month':8,'day':30}]
    value['places']=[{'text':'서울시','ambiguous':False}]
    async def fake(*args):return envelope(value)
    monkeypatch.setattr(ai,'_send',fake)
    assert call('2025년 8/15~8/30까지 서울시의 식생상태 확인')['engine']['status']=='invalid_response'


@pytest.mark.parametrize('change',[
    lambda d:d.update(coordinates=[128,36]),
    lambda d:d.update(purpose_type='anything'),
    lambda d:d['dates'][0].update(month=9),
    lambda d:d['dates'][0].update(day=32),
    lambda d:d['places'][0].update(text='서울'),
    lambda d:d.pop('temporal_mode'),
    lambda d:d['dates'][0].update(basis='unspecified'),
    lambda d:d.update(temporal_evidence='없는 원문'),
])
def test_invalid_ai_output_never_applies_fields(monkeypatch,change):
    value=deepcopy(VALID);change(value)
    async def fake(*args):return envelope(value)
    monkeypatch.setattr(ai,'_send',fake)
    p=call();assert p['status']=='failed' and p['engine']['status']=='invalid_response'
    assert p['period']['status']=='absent' and p['region']['status']=='absent'


@pytest.mark.parametrize('mode',['timeout','http','missing','refusal'])
def test_failure_is_explicit_no_rule_fallback(monkeypatch,mode):
    async def fake(*args):
        if mode=='timeout':raise TimeoutError('TEST ONLY')
        if mode=='http':raise RuntimeError('TEST ONLY secret must never be returned')
        if mode=='missing':return {'status':'completed','output':[]}
        return {'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'TEST ONLY'}]}]}
    monkeypatch.setattr(ai,'_send',fake)
    p=call();assert p['status']=='failed' and p['period']['status']=='absent'
    assert 'secret' not in json.dumps(p)


def test_unconfigured_and_limits_make_no_call(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY');assert call()['engine']['status']=='not_configured'
    monkeypatch.setenv('OPENAI_API_KEY','TEST_ONLY');ai.stats['requests']=100
    assert call()['engine']['status']=='limited'


def test_relative_and_event_dates_are_not_invented(monkeypatch):
    value=deepcopy(VALID);value.update(dates=[],relative_date=True,temporal_mode='change',temporal_evidence='전후')
    async def fake(*args):return envelope(value)
    monkeypatch.setattr(ai,'_send',fake)
    p=call('최근 영천군의 식생상태 전후');assert p['period']['status']=='needs_confirmation'
    assert p['event_reference_required'] and 'reference_date' not in p


def test_english_explicit_month_and_unknown_place(monkeypatch):
    value=deepcopy(VALID);value['dates'][0]={'evidence':'August 2025','year':2025,'month':8,'day':None};value['places'][0]['text']='Atlantis'
    async def fake(*args):return envelope(value)
    monkeypatch.setattr(ai,'_send',fake)
    p=call('Atlantis August 2025 식생상태');assert p['period']['end']=='2025-08-31'
    assert p['region']['status'] =='lookup_required' and p['region']['mentioned_text']=='Atlantis'


def test_cancellation_stops_transport_and_marks_unknown_usage(monkeypatch):
    async def scenario():
        started=asyncio.Event()
        async def fake(*args):started.set();await asyncio.Event().wait()
        monkeypatch.setattr(ai,'_send',fake)
        task=asyncio.create_task(ai.propose_with_ai(TEXT));await started.wait();task.cancel()
        with pytest.raises(asyncio.CancelledError):await task
        assert ai.stats['cancelled']==1 and ai.stats['unknown_usage_calls']==1 and not ai.lock.locked()
    asyncio.run(scenario())


def test_busy_and_rate_limit_without_network(monkeypatch):
    async def scenario():
        async with ai.lock:
            assert (await ai.propose_with_ai(TEXT))['engine']['status']=='busy'
        import time
        ai.recent.extend([time.monotonic()]*6)
        assert (await ai.propose_with_ai(TEXT))['engine']['status']=='limited'
    asyncio.run(scenario())


def test_wrong_outer_envelope_is_safe(monkeypatch):
    async def fake(*args):return []
    monkeypatch.setattr(ai,'_send',fake)
    assert call()['engine']['status']=='invalid_response'


def test_config_lists_only_missing_names_without_calling_openai(monkeypatch):
    monkeypatch.setenv('AI_NL_ENABLED','0');monkeypatch.setenv('AI_NL_PROVIDER','unsupported')
    monkeypatch.setenv('AI_NL_MODEL','');monkeypatch.delenv('OPENAI_API_KEY')
    config=TestClient(app).get('/request/config').json()
    assert config['ready'] is False
    assert config['missing_settings']==['AI_NL_ENABLED','AI_NL_PROVIDER','AI_NL_MODEL','OPENAI_API_KEY']
    assert config['usage']['requests']==0


def test_ready_means_configuration_only_and_never_returns_key(monkeypatch):
    monkeypatch.setenv('AI_NL_MODEL','gpt-5.6-luna')
    async def forbidden(*args):raise AssertionError('status endpoint must never invoke OpenAI')
    monkeypatch.setattr(ai,'_send',forbidden)
    config=TestClient(app).get('/request/config').json()
    assert config['ready'] is True and config['missing_settings']==[]
    assert config['provider']=='openai' and config['model']=='gpt-5.6-luna'
    assert config['usage']['requests']==0 and 'TEST_ONLY_NOT_A_KEY' not in json.dumps(config)


def test_selected_low_cost_model_disables_reasoning_with_mock_transport(monkeypatch):
    monkeypatch.setenv('AI_NL_MODEL','gpt-5.6-luna');sent=[]
    async def fake(payload,key):sent.append(payload);return envelope(VALID)
    monkeypatch.setattr(ai,'_send',fake)
    assert call()['engine']['status']=='succeeded'
    assert sent[0]['reasoning']=={'effort':'none'} and sent[0]['max_output_tokens']==2000
    assert sent[0]['text']['format']['strict'] is True


def test_gpt_4o_uses_structured_outputs_without_reasoning_setting(monkeypatch):
    monkeypatch.setenv('AI_NL_MODEL','gpt-4o');sent=[]
    async def fake(payload,key):sent.append(payload);return envelope(VALID)
    monkeypatch.setattr(ai,'_send',fake)
    assert call()['engine']['status']=='succeeded'
    assert sent[0]['model']=='gpt-4o'
    assert 'reasoning' not in sent[0]
    assert sent[0]['text']['format']['strict'] is True
