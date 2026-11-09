"""Synthetic metadata only: verify scientific band matching and grouping invariants."""
import pytest
from app.metadata import normalize
from app.purpose_plan import purpose_plan
from app.main import app
from app import stac
from fastapi.testclient import TestClient


def item(collection='sentinel-2-l2a', names=('red','green','blue','nir','swir16','swir22')):
    assets={name:{'href':f'https://example.test/{name}.tif','type':'image/tiff','eo:bands':[{'common_name':name}]} for name in names}
    assets['visual']={'href':'https://example.test/visual.tif','type':'image/tiff','roles':['visual'],'eo:bands':[{'common_name':n} for n in ('red','green','blue')]}
    assets['scl']={'href':'https://example.test/scl.tif','type':'image/tiff'}
    return {'id':'TEST_ONLY_'+collection,'collection':collection,'properties':{'platform':'landsat-8' if collection=='landsat-c2-l2' else 'sentinel-2b','processing:level':'L2SP' if collection=='landsat-c2-l2' else 'S2MSI2A'},'assets':assets}


@pytest.mark.parametrize('purpose,required', [('vegetation',{'red','nir'}),('flood',{'green','swir16'}),('urban',{'nir','swir16'})])
def test_purpose_defaults_never_use_rgb_composite_as_band(purpose,required):
    plan=purpose_plan(normalize(item()),purpose)
    assert required.issubset(plan['default_keys'])
    assert 'visual' not in plan['default_keys']
    assert not plan['missing_bands']
    assert plan['group']==('other' if plan['purpose']=='flood' else 'primary')
    assert 'scl' in plan['default_keys']


def test_missing_required_and_visual_bands_are_explicit():
    plan=purpose_plan(normalize(item(names=('green','red'))),'flood')
    assert plan['missing_bands']==['swir16']
    assert plan['visual_missing']==['swir16']
    assert plan['group']==('other' if plan['purpose']=='flood' else 'primary')
    assert 'swir16' not in plan['default_keys']
    visual_only=purpose_plan(normalize(item(names=())),'vegetation')
    assert set(visual_only['missing_bands'])=={'red','nir'}


def test_thermal_prefers_real_thermal_asset_and_other_satellite_is_reference():
    plan=purpose_plan(normalize(item('landsat-c2-l2',('lwir11','red'))),'thermal')
    assert 'lwir11' in plan['analysis_keys']
    assert plan['group']==('other' if plan['purpose']=='flood' else 'primary')
    assert 'visual' not in plan['default_keys']
    optical=purpose_plan(normalize(item()),'thermal')
    assert optical['group']=='other'
    assert optical['missing_bands']==['thermal']


def test_cog_is_preferred_over_duplicate_jp2():
    raw=item()
    raw['assets']['nir-jp2']={'href':'s3://test/nir.jp2','type':'image/jp2','eo:bands':[{'common_name':'nir'}]}
    plan=purpose_plan(normalize(raw),'vegetation')
    assert 'nir' in plan['default_keys']
    assert 'nir-jp2' not in plan['default_keys']


def test_manual_reference_search_includes_alternative_and_respects_total_cap(monkeypatch):
    calls=[]
    async def fake(client, request, seconds):
        collection=request['body']['collections'][0]
        calls.append(collection)
        rows=[item(collection,('lwir11','red') if collection=='landsat-c2-l2' else ('red','green')) for _ in range(6)]
        for i,row in enumerate(rows): row['id']=f'TEST_{i}'
        return {'features':rows,'links':[]}
    monkeypatch.setattr(stac,'request_page',fake)
    result=TestClient(app).post('/search',json={'purpose':'열환경','purpose_type':'thermal','collections':['landsat-c2-l2','sentinel-2-l2a'],'bbox':[126.5,36.3,127,36.8],'start_date':'2025-07-01','end_date':'2025-07-31','max_items':5}).json()
    assert calls==['landsat-c2-l2','sentinel-2-l2a']
    assert result['returned']==5
    assert [s['returned'] for s in result['collection_statuses']]==[3,2]
    assert result['items'][0]['purpose_plan']['group']=='primary'
    assert result['items'][-1]['purpose_plan']['group']=='other'
