"""Official local boundary validation + TEST ONLY Kakao transport. No live calls."""
from copy import deepcopy
import json
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import shape
from app import admin_boundaries as ab, place_search as ps
from app.main import app
from app.condition_proposals import propose_conditions,extract_places

SEOUL={'name':'서울','center':[126.978,37.5665],'parent':'','admin_level':'시·도','region_code':'1100000000'}

def test_official_geometry_bbox_axis_area_and_provenance():
    r=ab.propose(SEOUL);assert r['status']=='proposed'
    g=shape(r['geometry']);assert g.is_valid and g.bounds==tuple(r['bbox'])
    assert r['bbox']==pytest.approx([126.76448395994285,37.42829747715147,127.18379492887969,37.70145527232949])
    assert r['boundary_area_km2']==pytest.approx(605.3012246338355)
    assert 1100<r['bbox_area_km2']<1150 and r['pixel_area_exceeded'] is True
    assert r['original_crs']=='EPSG:5179' and r['crs']=='EPSG:4326'
    assert r['polygon_clipping'] is False and r['year'].startswith('2025-06-30')
    assert r['code']=='11' and r['source_url']=='https://www.data.go.kr/data/15129688/fileData.do'

@pytest.mark.parametrize('field,value',[('region_code','2600000000'),('region_code','1111000000'),('admin_level','시·군·구'),('parent','경기도'),('center',[129.0,35.0])])
def test_no_wrong_region_or_parent_substitution(field,value):
    d={**SEOUL,field:value};assert ab.propose(d)['status']=='mismatch'

def test_unsupported_boundary_and_broken_source(monkeypatch):
    assert ab.propose({**SEOUL,'name':'경기도 연천군'})['status']=='unsupported'
    def broken(*args):raise ValueError('TEST ONLY wrong hash')
    monkeypatch.setattr(ab,'load_boundary',broken);assert ab.propose(SEOUL)['status']=='failed'

@pytest.mark.parametrize('alias',['서울','서울시','서울특별시'])
def test_alias_and_rule_example_without_ai(alias):
    p=propose_conditions(f'2025년 8월 {alias} 지표면 온도 알고싶음')
    assert p['period']['start']=='2025-08-01' and p['period']['end']=='2025-08-31'
    assert p['extraction']['purpose_type']=='thermal'
    assert p['extraction']['places']==[{'text':alias,'ambiguous':False}]
    assert 'boundary' not in p['region'] # place extraction is not a geometry generator

def test_finer_and_multiple_place_strings_remain_separate():
    assert extract_places('서울시 중구의 온도')[0]['text']=='서울시 중구'
    assert [p['text'] for p in extract_places('서울시 또는 부산시 온도')]==['서울시','부산시']
    assert not extract_places('지표면 온도 알고싶음')

def test_kakao_region_is_camera_only_without_automatic_boundary(monkeypatch):
    monkeypatch.setenv('GEOCODER_ENABLED','1');monkeypatch.setenv('KAKAO_LOCAL_REST_API_KEY','TEST_ONLY_NOT_A_KEY');ps.recent.clear();ps.calls=0
    seen=[]
    async def fake(query):
        seen.append(query)
        return 200,{'documents':[{'address_name':'서울','address_type':'REGION','x':'126.978','y':'37.5665',
            'address':{'region_1depth_name':'서울','region_2depth_name':'','region_3depth_name':'','b_code':'1100000000'}}], 'meta':{'is_end':True}}
    monkeypatch.setattr(ps,'_request',fake)
    r=TestClient(app).post('/places/search',json={'place':'서울시'})
    assert r.status_code==200
    p=r.json();assert p['status']=='resolved' and p['name']=='서울특별시' and 'boundary' not in p and 'bbox' not in p
    assert seen==['서울시'] and 'TEST_ONLY_NOT_A_KEY' not in json.dumps(p)
