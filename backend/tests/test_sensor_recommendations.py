"""Instrument recommendation contract tests. Fixtures never used in the service."""
import copy
import httpx
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app import stac
from app.recommendations import recommend
from app.purpose_plan import purpose_plan,RULES,required_for
from app.metadata import normalize
from app.sensor_catalog import CATALOG,RULE_VERSION,CHECKED_ON
from test_core import QUERY
from test_purpose_plan import item

client=TestClient(app)

def raw(profile='s2_msi',names=None):
    p=CATALOG[profile]
    r=item(p['collection'],names or ('green','red','nir','swir16','swir22','lwir11'))
    r['properties'].update({'platform':p['platforms'][0],'processing:level':p['levels'][0],'datetime':'2025-07-01T02:00:00Z'})
    return r

@pytest.mark.parametrize('text,purpose,ids',[
 ('녹지 변화','vegetation',['s2_msi','landsat_oli','viirs_sr']),('장마 침수','flood',['s1_csar','s2_msi','landsat_oli']),
 ('도시 변화','urban',['s2_msi','landsat_oli']),('열환경','thermal',['landsat_tirs'])])
def test_deterministic_single_rules(text,purpose,ids):
    a=recommend(text);b=recommend(text)
    assert a==b and a['rule_version']==RULE_VERSION
    assert [c['id'] for c in a['cards']]==ids+['pc_'+i for i in ids if i in ('s2_msi','landsat_oli','landsat_tirs')]+(['noaa_viirs_ndvi'] if purpose=='vegetation' else [])+(['hls_l30','hls_s30'] if purpose!='thermal' else [])
    for c in a['cards']:
        assert c['availability']['status']=='unsearched' and c['availability']['count'] is None
        assert c['pixel_quality']['status']=='not_checked'
        assert c['sources'] and all(s['checked_on'] in (CHECKED_ON,'2026-11-02') and s['url'].startswith('https://') for s in c['sources'])
        if c['app_support']['search']:
            assert [b['name'] for b in c['required_bands']]==required_for(purpose,c['id'])
            plan=purpose_plan(normalize(raw(c['id'])),purpose)
            assert not plan['missing_bands']
            assert CATALOG[c['id']].get('metadata_search') or len(plan['analysis_keys'])>=len(c['required_bands'])

def test_sar_search_connected_and_optical_conditional():
    r=recommend('장마')
    assert r['cards'][0]['fit']['status']=='met'
    assert r['cards'][0]['search_enabled'] and r['cards'][0]['collection']=='sentinel-1-grd'
    assert all(c['fit']['status']=='conditional' for c in r['cards'][1:])

@pytest.mark.parametrize('need',['all_weather','night'])
def test_hard_observation_requirements_not_silently_changed(need,monkeypatch):
    r=recommend('침수',observation_need=need)
    assert r['collections']==['sentinel-1-grd']
    assert all(c['fit']['status']=='not_met' and not c['search_enabled'] for c in r['cards'][1:])
    async def empty(*args):return {'features':[],'links':[]}
    monkeypatch.setattr(stac,'request_page',empty)
    d=client.post('/search',json=QUERY|{'collections':None,'observation_need':need}).json()
    assert d['collections']==['sentinel-1-grd'] and d['outcome']=='empty'


def test_thermal_excludes_s2_and_night_st():
    r=recommend('열환경')
    assert r['collections']==['landsat-c2-l2','pc-landsat-c2-l2']
    c=r['cards'][0]
    assert 'L2SP' in c['product'] and 'TIRS-2' in c['payload']
    assert '100' in c['native_resolution'] and '30' in c['output_grid']
    assert '기온' in ' '.join(c['constraints'])
    assert not recommend('야간 열환경')['cards'][0]['search_enabled']
    assert client.post('/search',json=QUERY|{'purpose':'열환경','purpose_type':'thermal','recommendation_id':'s2_msi'}).status_code==422

@pytest.mark.parametrize('mutation',[
 {'properties':{'platform':'landsat-8','processing:level':'L2SR'}},
 {'properties':{'platform':'landsat-8'}},
 {'properties':{'platform':'landsat-7','processing:level':'L2SP'}},
 {'assets':{}},
])
def test_missing_product_or_thermal_band_never_selected(mutation):
    r=raw('landsat_tirs');r.update(mutation)
    plan=purpose_plan(normalize(r),'thermal')
    assert plan['missing_bands']==['thermal']
    assert 'lwir11' not in plan['default_keys']

def test_missing_input_and_ambiguous_purpose():
    r=recommend('녹지 변화')
    assert any('크기 미입력' in a for a in r['assumptions'])
    assert any('전후 변화' in a for a in r['assumptions'])
    for text in ('','알 수 없는 질문','식생 열환경'):
        assert recommend(text)['cards']==[]
    assert recommend('식생 열환경','vegetation')['cards']
    r=recommend('식생',target_size_m=5)
    assert all(c['fit']['status']=='conditional' for c in r['cards'])
    assert all('운영 가정' in ' '.join(c['constraints']) for c in r['cards'])
    assert client.post('/recommend',json={'purpose':'식생','purpose_type':'vegetation','target_size_m':-1}).status_code==422

def test_recommendation_search_preserves_aoi_dates_and_filters_product(monkeypatch):
    calls=[]
    async def fake(client,req,seconds):
        calls.append(req['body'])
        good=raw('landsat_tirs');good['id']='TEST_GOOD'
        sr=copy.deepcopy(good);sr['id']='TEST_NO_ST';sr['properties']['processing:level']='L2SR'
        missing=copy.deepcopy(good);missing['id']='TEST_NO_BAND';missing['assets'].pop('lwir11')
        return {'features':[good,sr,missing],'links':[]}
    monkeypatch.setattr(stac,'request_page',fake)
    q=QUERY|{'purpose':'열환경','purpose_type':'thermal','recommendation_id':'landsat_tirs','collections':['sentinel-2-l2a']}
    d=client.post('/search',json=q).json()
    assert calls[0]['collections']==['landsat-c2-l2']
    assert calls[0]['bbox']==q['bbox'] and calls[0]['datetime'].startswith(q['start_date'])
    assert [i['id'] for i in d['items']]==['TEST_GOOD']
    assert d['collection_statuses'][0]['filtered']==2
    assert d['recommendation']['cards'][0]['availability']['status']=='searched'
    assert d['items'][0]['pixel_quality']['status']=='not_checked'
    assert d['applied_conditions']['product_levels']==['L2SP']

@pytest.mark.parametrize('state,expected',[('empty','none'),('failed','failed'),('limited','unsearched')])
def test_zero_failure_unqueried_are_distinct(monkeypatch,state,expected):
    async def fake(*args):
        if state=='failed':raise httpx.ReadTimeout('TEST ONLY')
        return {'features':[],'links':[]}
    monkeypatch.setattr(stac,'request_page',fake)
    if state=='limited':monkeypatch.setattr(stac,'MAX_REQUESTS',0)
    d=client.post('/search',json=QUERY|{'recommendation_id':'s2_msi'}).json()
    assert d['recommendation']['cards'][1]['availability']['status']==expected
    assert d['recommendation']['cards'][0]['availability']['status']=='unsearched'


def test_invalid_dates_checked_before_card_search():
    r=client.post('/search',json=QUERY|{'recommendation_id':'s2_msi','start_date':'2025-08-01'})
    assert r.status_code==422


def test_filtered_page_does_not_consume_result_quota(monkeypatch):
    calls=[]
    async def fake(client,request,timeout):
        calls.append(request)
        if len(calls)==1:
            wrong=raw('landsat_tirs');wrong['properties']['processing:level']='L2SR'
            return {'features':[wrong],'links':[{'rel':'next','href':stac.STAC_URL+'/search?page=2'}]}
        good=raw('landsat_tirs');good['id']='TEST_NEXT_PAGE'
        return {'features':[good],'links':[]}
    monkeypatch.setattr(stac,'request_page',fake)
    r=client.post('/search',json=QUERY|{'purpose':'열환경','purpose_type':'thermal','recommendation_id':'landsat_tirs','max_items':1})
    assert r.status_code==200
    d=r.json()
    assert len(calls)==2 and d['items'][0]['id']=='TEST_NEXT_PAGE'
    assert d['collection_statuses'][0]['filtered']==1
