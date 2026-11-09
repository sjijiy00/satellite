"""A2 synthetic metadata/transport only. Never used by application fallback paths."""
import asyncio
import copy
import json
from time import monotonic
import httpx
import pytest
from fastapi.testclient import TestClient
from shapely.geometry import box,mapping
from app.main import app
from app import analysis_conditions as a2
from app.grid_metadata import grid_metadata
from app.selection import footprint_metrics
from test_purpose_plan import item

client=TestClient(app)
QUERY={'bbox':[126.5,36.3,127,36.8],'start_date':'2025-07-01','end_date':'2025-07-31',
       'purpose_type':'vegetation','reference_date':'2025-07-15',
       'scene_a':{'collection':'sentinel-2-l2a','id':'TEST_A'},'scene_b':{'collection':'sentinel-2-l2a','id':'TEST_B'}}


def raw(id,date):
    r=item(names=('red','nir'))
    r.update(id=id,geometry=mapping(box(126.4,36.2,127.1,36.9)))
    r['properties'].update(datetime=date+'T02:00:00Z',instruments=['msi'])
    r['properties']['proj:epsg']=32652
    for key,a in r['assets'].items():
        a.update({'href':f'https://sentinel-cogs.s3.us-west-2.amazonaws.com/TEST_ONLY/{id}/{key}.tif',
                  'proj:shape':[100,100],'proj:transform':[10,0,200000,0,-10,4100000]})
    return r


@pytest.fixture
def transport(monkeypatch):
    rows={'TEST_A':raw('TEST_A','2025-07-05'),'TEST_B':raw('TEST_B','2025-07-20')}
    calls=[]
    async def request(c,method,url,budget):
        calls.append((method,url));budget['requests']+=1
        if method=='GET':return 200,{},copy.deepcopy(rows[url.rsplit('/',1)[1]])
        return 200,{'content-type':'image/tiff','content-length':'100'},None
    monkeypatch.setattr(a2,'request_metadata',request)
    return rows,calls


def inspect(**updates):
    r=client.post('/analysis-conditions',json=QUERY|updates)
    assert r.status_code==200,r.text
    d=r.json();return d,{c['id']:c for c in d['checks']}


def test_a2_reuses_rules_fetches_canonical_items_and_never_passes_pixels(transport):
    d,c=inspect()
    assert c['product']['status']==c['reference']['status']==c['grid']['status']=='pass'
    assert d['status']=='conditional' and c['pixel-quality']['status']=='unknown'
    assert d['pixel_quality']=='not_checked' and d['file_headers_read'] is False
    assert d['coverage']['common_percent']==100
    assert [a['key'] for a in d['assets']]==['red','nir','scl']*2
    assert len(transport[1])==8 and sum(m=='GET' for m,_ in transport[1])==2
    assert all(c['next_action'] and c['reason'] for c in d['checks'])


@pytest.mark.parametrize('change,key,status',[
    ('duplicate','identity','blocked'),('reversed','dates','blocked'),('same_date','dates','blocked'),
    ('date_missing','dates','unknown'),('date_naive','dates','unknown'),('outside_period','period','blocked'),
    ('product','product','conditional'),('product_missing','product','unknown'),
    ('band_missing','bands-0','blocked'),('quality_missing','quality-0','blocked'),
    ('crs_missing','grid','unknown'),('grid_different','grid','conditional'),
    ('shape_missing','grid','unknown'),('geometry_missing','coverage','unknown'),
    ('no_common','coverage','blocked'),('reference_wrong','reference','blocked'),
])
def test_a2_condition_boundaries(transport,change,key,status):
    rows,_=transport;a,b=rows.values();updates={}
    if change=='duplicate':updates['scene_b']=QUERY['scene_a']
    if change=='reversed':updates.update(scene_a=QUERY['scene_b'],scene_b=QUERY['scene_a'])
    if change=='same_date':b['properties']['datetime']=a['properties']['datetime']
    if change=='date_missing':a['properties']['datetime']=None
    if change=='date_naive':a['properties']['datetime']='2025-07-05T02:00:00'
    if change=='outside_period':a['properties']['datetime']='2025-06-01T00:00:00Z'
    if change=='product':b['properties']['instruments']=['other']
    if change=='product_missing':b['properties'].pop('processing:level')
    if change=='band_missing':a['assets'].pop('nir')
    if change=='quality_missing':a['assets'].pop('scl')
    if change=='crs_missing':a['properties'].pop('proj:epsg')
    if change=='grid_different':b['assets']['scl']['proj:transform']=[20,0,200000,0,-20,4100000]
    if change=='shape_missing':a['assets']['red'].pop('proj:shape')
    if change=='geometry_missing':a['geometry']=None
    if change=='no_common':
        a['geometry']=mapping(box(126.5,36.3,126.7,36.8));b['geometry']=mapping(box(126.8,36.3,127,36.8))
    if change=='reference_wrong':updates['reference_date']='2025-07-25'
    d,c=inspect(**updates)
    assert c[key]['status']==status
    assert d['pixel_quality']=='not_checked'
    if change=='no_common':
        assert d['coverage']['common_area_m2']==0 and d['coverage']['scene_a_percent']>0 and d['coverage']['scene_b_percent']>0
    if change=='geometry_missing':assert d['coverage']['common_area_m2'] is None


def test_missing_reference_and_bad_requests(transport):
    d,c=inspect(reference_date=None)
    assert c['reference']['status']=='unknown'
    for updates in [{'reference_date':'2025-08-01'},{'start_date':'2025-08-01'},
                    {'scene_a':{'collection':'sentinel-1','id':'a'}},{'scene_a':{'collection':'sentinel-2-l2a','id':'../private'}}]:
        assert client.post('/analysis-conditions',json=QUERY|updates).status_code==422


@pytest.mark.parametrize('code,mime,expected',[(403,'image/tiff','blocked'),(404,'image/tiff','blocked'),
    (302,'text/html','unknown'),(405,'text/html','unknown'),(200,'text/html','unknown'),(200,'image/tiff','pass')])
def test_http_access_status_not_pixel_status(monkeypatch,code,mime,expected):
    async def fake(*args):return code,{'content-type':mime,'content-length':'100'},None
    monkeypatch.setattr(a2,'request_metadata',fake)
    status,reason,evidence=asyncio.run(a2.inspect_asset(None,{'href':'https://sentinel-cogs.s3.us-west-2.amazonaws.com/TEST.tif'},{}))
    assert status==expected and evidence['pixel_read'] is False and evidence['file_header_read'] is False


@pytest.mark.parametrize('url',[
    'http://127.0.0.1/private','https://example.test/a.tif','https://sentinel-cogs.s3.us-west-2.amazonaws.com/a?secret=TEST_SECRET',
    'https://user:TEST_SECRET@sentinel-cogs.s3.us-west-2.amazonaws.com/a','https://sentinel-cogs.s3.us-west-2.amazonaws.com:bad/a',
])
def test_no_arbitrary_url_or_auth_access(monkeypatch,url):
    async def never(*args):raise AssertionError('must not access')
    monkeypatch.setattr(a2,'request_metadata',never)
    status,_,evidence=asyncio.run(a2.inspect_asset(None,{'href':url},{}))
    assert status=='unknown' and 'TEST_SECRET' not in json.dumps(evidence)


def test_canonical_failure_and_asset_timeout_are_unknown(monkeypatch,transport):
    async def failed(*args):raise httpx.ReadTimeout('TEST ONLY')
    monkeypatch.setattr(a2,'request_metadata',failed)
    d,c=inspect()
    assert c['item-0']['status']=='unknown' and d['coverage']['common_area_m2'] is None
    assert d['status']=='unknown'
    result=asyncio.run(a2.inspect_asset(None,{'href':'https://sentinel-cogs.s3.us-west-2.amazonaws.com/a.tif'},{}))
    assert result[0]=='unknown'


def test_transport_budget_size_cap_and_head_only(monkeypatch):
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda r:httpx.Response(200,json={'too':'large'}))) as c:
            with pytest.raises(TimeoutError):await a2.request_metadata(c,'GET','https://example.test',{'started':monotonic()-100,'requests':0})
            with pytest.raises(TimeoutError):await a2.request_metadata(c,'GET','https://example.test',{'started':monotonic(),'requests':a2.MAX_REQUESTS})
            monkeypatch.setattr(a2,'MAX_ITEM_BYTES',2)
            with pytest.raises(ValueError):await a2.request_metadata(c,'GET','https://example.test',{'started':monotonic(),'requests':0})
            code,_,data=await a2.request_metadata(c,'HEAD','https://example.test',{'started':monotonic(),'requests':0})
            assert code==200 and data is None
    asyncio.run(run())


def test_projection_precedence_null_and_resolution_units():
    r=raw('TEST_A','2025-07-05')
    r['assets']['red']['proj:code']=None
    assert grid_metadata(r,'red')['crs'] is None
    r['assets']['red']['proj:code']='EPSG:4326'
    g=grid_metadata(r,'red')
    assert g['crs']=='EPSG:4326' and g['units']==['degree','degree']
    assert g['shape']==[100,100] and g['extent']==[200000,4099000,201000,4100000]
    r['assets']['red']['proj:transform']=[0]*6
    assert grid_metadata(r,'red')['transform'] is None


def test_common_area_distinct_from_individual_and_boundary_contact():
    bbox=[126,36,127,37]
    d=footprint_metrics(bbox,mapping(box(126,36,126.75,37)),mapping(box(126.25,36,127,37)))
    assert d['scene_a_percent']==pytest.approx(75,abs=.02)
    assert d['common_percent']==pytest.approx(50,abs=.02)
    assert 0<d['common_area_m2']<d['aoi_area_m2']
    d=footprint_metrics(bbox,mapping(box(126,36,126.5,37)),mapping(box(126.5,36,127,37)))
    assert d['common_area_m2']==0 and d['geometry'] is None


def test_thermal_quality_catalog_and_requester_pays_are_checked(transport):
    rows,calls=transport
    for r in rows.values():
        r['collection']='landsat-c2-l2'
        r['properties'].update(platform='landsat-8',instruments=['oli','tirs'])
        r['properties']['processing:level']='L2SP'
        r['assets']['lwir11']=copy.deepcopy(r['assets']['red'])
        r['assets']['lwir11']['eo:bands']=[{'common_name':'lwir11'}]
        for k in ('qa_pixel','qa_radsat','qa'):
            r['assets'][k]=copy.deepcopy(r['assets']['scl'])
        for asset in r['assets'].values():asset['storage:requester_pays']=True
    rows['TEST_A']['assets'].pop('qa')
    d,c=inspect(purpose_type='thermal',scene_a={'collection':'landsat-c2-l2','id':'TEST_A'},scene_b={'collection':'landsat-c2-l2','id':'TEST_B'})
    assert c['quality-0']['status']=='blocked' and c['quality-0']['evidence']['missing']==['qa']
    assert c['quality-1']['status']=='pass'
    assert c['access-1-qa']['status']=='unknown'
    assert all(method=='GET' for method,_ in calls)


def test_asset_legacy_crs_override_and_multiband_grid_not_guessed():
    r=raw('TEST_A','2025-07-05');r['properties']['proj:code']='EPSG:32652'
    r['assets']['red']['proj:epsg']=32651
    assert grid_metadata(r,'red')['crs']=='EPSG:32651'
    r['assets']['red']['raster:bands']=[{'proj:shape':[1,1]},{'proj:shape':[2,2]}]
    assert grid_metadata(r,'red')['shape'] is None
