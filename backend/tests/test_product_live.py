"""Explicit public metadata/COG Range only, no provider credentials/paid AI."""
import asyncio,hashlib,json,os,pathlib,zipfile
from uuid import uuid4
from datetime import datetime,timezone
import pytest
import rasterio
from app.processing_models import ProcessingRequest
from app import product_processing,artifact_store
from app.product_policy import products,QA_VERSION
from app.raster_source import open_sources

pytestmark=pytest.mark.skipif(os.getenv('LIVE_STAC')!='1' or os.getenv('LIVE_PROCESSING')!='1',reason='Explicit public LIVE_STAC + LIVE_PROCESSING only')
CASES=[('es_s2',m) for m in ('ndvi','mndwi','mndwi_change','ndbi')]+[('pc_landsat',m) for m in ('ndvi','mndwi','mndwi_change','ndbi','surface_temperature','hotspots','temperature_comparison')]

@pytest.mark.parametrize('profile,method',CASES)
def test_actual_public_product_pixels_files_and_reopen(tmp_path,monkeypatch,profile,method):
    p=next(p for p in products(method) if p['profile_id']==profile);thermal=method in ('surface_temperature','hotspots','temperature_comparison')
    # The first Korean coastal ST trial had no valid ST (reflectance access
    # was not temperature availability). Keep that failure in the report. This
    # explicitly different land sample does not replace a user's selected AOI.
    bbox=[126.7,36.4,126.71,36.41] if profile=='es_s2' else [-115.15,36.16,-115.14,36.17]
    ids=(['S2B_52SBF_20210716_0_L2A','S2B_52SBF_20210726_0_L2A'] if method=='mndwi_change' else ['S2B_52SBF_20210716_0_L2A']) if profile=='es_s2' else ['LC08_L2SP_039035_20250719_02_T1']
    if profile=='pc_landsat' and method=='mndwi_change':ids=['LC08_L2SP_039035_20250703_02_T1','LC08_L2SP_039035_20250719_02_T1'] # confirmed by actual PC search, no fabricated candidates
    q={'purpose_type':'thermal' if thermal else 'urban' if method=='ndbi' else 'flood' if method.startswith('mndwi') else 'vegetation',
       'analysis_id':{'ndvi':'vegetation_index','mndwi':'water_extent','mndwi_change':'water_change','ndbi':'urban_index'}.get(method,method),'method_id':method,
       'roi':{'confirmed':True,'mode':'bbox','bbox':bbox,'source':'manual_bbox'},'start_date':'2021-07-01' if profile=='es_s2' else '2025-07-01',
       'end_date':'2021-07-31' if profile=='es_s2' else '2025-07-31',
       'scenes':[{'provider_id':p['provider_id'],'collection':p['collection'],'id':id,'asset_keys':p['required_keys']} for id in ids],'qa_policy_version':QA_VERSION}
    if method in ('mndwi','mndwi_change','hotspots'):q.update(threshold=20 if thermal else 0,threshold_basis='Explicit LIVE test criterion only; not a universal water/heat threshold')
    if method=='temperature_comparison':
        w,s,e,n=bbox;q.update(comparison_regions=[{'confirmed':True,'mode':'bbox','source':'manual_bbox','bbox':[w,s,w+.004,n]},{'confirmed':True,'mode':'bbox','source':'manual_bbox','bbox':[w+.006,s,e,n]}],comparison_labels=['LIVE test west region','LIVE test east region'])
    payload,grid=asyncio.run(product_processing.prepare(ProcessingRequest.model_validate(q)))
    monkeypatch.setattr(artifact_store,'ROOT',tmp_path/'actual_public_files');identifier=uuid4().hex;store=open_sources(payload)
    try:result=product_processing.execute(payload,identifier,store)
    finally:store.close()
    file=artifact_store.verified_download(identifier,result['artifact'])
    with zipfile.ZipFile(file) as z:
        m=json.loads(z.read('manifest.json'));assert m['verified_after_disk_write']
        for name,record in m['files'].items():
            assert hashlib.sha256(z.read(name)).hexdigest()==record['sha256']
            if name.endswith('.tif'):
                with rasterio.io.MemoryFile(z.read(name)) as mem:
                    with mem.open() as ds:assert ds.crs and ds.nodata is not None and ds.read().size
    evidence={'checked_at':datetime.now(timezone.utc).isoformat(),'profile':profile,'method':method,'items':ids,'bbox':bbox,'grid':grid,
        'statistics':result['result']['statistics'],'valid_percent_aoi':result['result']['common_valid_percent_aoi'],
        'input_range_bytes':store.bytes,'range_requests':store.requests,'transport_requests':store.client.requests,'zip_bytes':file.stat().st_size,
        'zip_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'stored_and_reopened':True,'scope':'actual public canonical/COG Range/calculation/file save/reopen; no full originals/browse/GIS GUI'}
    out=os.getenv('PROCESSING_EVIDENCE_DIR') or pathlib.Path('../test-results/active-product-engines.txt').read_text(encoding='utf-8');folder=pathlib.Path(out)/'live';folder.mkdir(exist_ok=True)
    (folder/(profile+'-'+method+'.json')).write_text(json.dumps(evidence,indent=2),encoding='utf-8');(folder/(profile+'-'+method+'.zip')).write_bytes(file.read_bytes())
