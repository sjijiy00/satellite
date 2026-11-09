"""Reviewed connections, not a claim to cover every satellite or discovered collection."""
PROVIDERS = {
    'earth-search': {'name': 'Element 84 Earth Search / AWS', 'endpoint': 'https://earth-search.aws.element84.com/v1',
                     'format': 'STAC', 'metadata_auth': False, 'max_requests': 12},
    'copernicus': {'name': 'Copernicus Data Space', 'endpoint': 'https://stac.dataspace.copernicus.eu/v1',
                   'format': 'STAC', 'metadata_auth': False, 'max_requests': 4},
    'nasa-cmr': {'name': 'NASA CMR / LP DAAC', 'endpoint': 'https://cmr.earthdata.nasa.gov/search',
                 'format': 'CMR JSON', 'metadata_auth': False, 'max_requests': 4},
}
PROVIDERS.update({
 'planetary-computer':{'name':'Microsoft Planetary Computer','endpoint':'https://planetarycomputer.microsoft.com/api/stac/v1','format':'STAC','metadata_auth':False,'max_requests':4},
 'noaa-nodd':{'name':'NOAA NODD / NCEI','endpoint':'https://noaa-cdr-ndvi-pds.s3.amazonaws.com','format':'S3 public object listing','metadata_auth':False,'max_requests':4},
})
# Internal collection keys are unambiguous; remote collection/concept IDs are separate.
COLLECTION_REGISTRY = {
    'sentinel-2-l2a': {'provider_id': 'earth-search', 'remote_id': 'sentinel-2-l2a', 'product_id': 's2_l2a'},
    'landsat-c2-l2': {'provider_id': 'earth-search', 'remote_id': 'landsat-c2-l2', 'product_id': 'landsat_c2_l2'},
    'sentinel-1-grd': {'provider_id': 'copernicus', 'remote_id': 'sentinel-1-grd', 'product_id': 's1_grd'},
    'viirs-vnp09ga-002': {'provider_id': 'nasa-cmr', 'remote_id': 'C2631841556-LPCLOUD', 'product_id': 'vnp09ga_002'},
}
COLLECTION_REGISTRY.update({
 'pc-sentinel-2-l2a':{'provider_id':'planetary-computer','remote_id':'sentinel-2-l2a','product_id':'s2_l2a','base_collection':'sentinel-2-l2a','version':'L2A/processing baseline per Item','access':'anonymous_sas','checked_on':'2026-11-02','source':'https://planetarycomputer.microsoft.com/dataset/sentinel-2-l2a','start':'2015-06-27','bbox':[-180,-90,180,90]},
 'pc-landsat-c2-l2':{'provider_id':'planetary-computer','remote_id':'landsat-c2-l2','product_id':'landsat_c2_l2','base_collection':'landsat-c2-l2','version':'Collection 2 Level 2, Landsat 8/9 only','access':'anonymous_sas','checked_on':'2026-11-02','source':'https://planetarycomputer.microsoft.com/dataset/landsat-c2-l2','start':'2013-03-18','bbox':[-180,-90,180,90]},
 'noaa-viirs-ndvi-cdr':{'provider_id':'noaa-nodd','remote_id':'noaa-cdr-ndvi-pds/data/VIIRS-Land_v001_JP113C1_NOAA-20','product_id':'noaa_viirs_ndvi_v1','version':'VIIRS NDVI CDR v1 / filename v001','access':'public_https','checked_on':'2026-11-02','source':'https://www.ncei.noaa.gov/products/climate-data-records/normalized-difference-vegetation-index','start':'2023-01-01','bbox':[-180,-90,180,90],'scope':'NOAA-20 JP113C1 v001 only; connection range starts 2023, not the entire CDR history','grid_extent_not_observed_coverage':True},
})
PLATFORMS = {
    # Product families are registered separately from actual input platforms.
    **{f'sentinel-2{x}': {'name':f'Sentinel-2{x.upper()}', 'sensor_ids':['msi']} for x in 'abc'},
    **{f'sentinel-1{x}': {'name':f'Sentinel-1{x.upper()}', 'sensor_ids':['c-sar']} for x in 'abc'},
    'landsat-8': {'name':'Landsat 8', 'sensor_ids':['oli','tirs']},
    'landsat-9': {'name':'Landsat 9', 'sensor_ids':['oli-2','tirs-2']},
    'suomi-npp': {'name':'Suomi NPP', 'sensor_ids':['viirs']},
}
from .hls import COLLECTIONS as HLS_COLLECTIONS
for _key,_hls in HLS_COLLECTIONS.items():
    COLLECTION_REGISTRY[_key]={'provider_id':'nasa-cmr','remote_id':_hls['concept'],'product_id':_key,
        'short_name':_hls['short_name'],'version':'2.0','access':'authentication_required',
        'checked_on':'2026-11-02','source':'https://cmr.earthdata.nasa.gov/search/collections.umm_json?concept_id='+_hls['concept'],
        'doi':_hls['doi'],'start':_hls['start'],'scope':'HLS optical NBAR; search/browse/download only. No app pixel processing.'}
PLATFORMS['noaa-20']={'name':'NOAA-20 / JPSS-1','sensor_ids':['viirs']}
SENSORS = {
    'msi': {'name':'MSI','observation':'optical-multispectral'},
    'c-sar': {'name':'C-SAR','observation':'radar'},
    'oli': {'name':'OLI','observation':'optical-multispectral'},
    'oli-2': {'name':'OLI-2','observation':'optical-multispectral'},
    'tirs': {'name':'TIRS','observation':'thermal-infrared'},
    'tirs-2': {'name':'TIRS-2','observation':'thermal-infrared'},
    'viirs': {'name':'VIIRS','observation':'visible-infrared-radiometer'},
}
# Product identity is not the provider's collection ID or the actual granule ID.
# Detailed specs and purpose rules remain in sensor_catalog / purpose_plan.
PRODUCTS = {
    's2_l2a': {'profiles':['s2_msi'],'search_supported':True,'file_access':'asset_dependent','pixel_processing':'S2 limited A3/A4/observed-composite/local-estimate gates'},
    'landsat_c2_l2': {'profiles':['landsat_oli','landsat_tirs'],'search_supported':True,'file_access':'asset_dependent','pixel_processing':'unsupported'},
    's1_grd': {'profiles':['s1_csar'],'search_supported':True,'file_access':'authentication_required','pixel_processing':'unsupported'},
    'vnp09ga_002': {'profiles':['viirs_sr'],'search_supported':True,'file_access':'authentication_required','pixel_processing':'unsupported'},
}
PRODUCTS['noaa_viirs_ndvi_v1']={'profiles':['noaa_viirs_ndvi'],'search_supported':True,'file_access':'public_https','pixel_processing':'unsupported; NetCDF download only, no browser raster preview/QA'}
for _key in HLS_COLLECTIONS:
    PRODUCTS[_key]={'profiles':['hls_l30' if _key=='hls-l30-002' else 'hls_s30'],'search_supported':True,
        'file_access':'authentication_required','pixel_processing':'unsupported; HLS Fmask/scale differ from S2 SCL'}
PRODUCTS['s2_l2a']['profiles'].append('pc_s2_msi')
PRODUCTS['landsat_c2_l2']['profiles'] += ['pc_landsat_oli','pc_landsat_tirs']
for _key,_registration in COLLECTION_REGISTRY.items():
    # Product capability is NOT a claim that every provider path can run A2-A4.
    _registration.update(search_supported=True,
        pixel_processing='limited_S2_A3_A4' if _key=='sentinel-2-l2a' else 'unsupported',
        preview_access='not_provided' if _key=='noaa-viirs-ndvi-cdr' else 'asset_dependent',
        original_access=_registration.get('access','authentication_required' if _key in ('sentinel-1-grd','viirs-vnp09ga-002') else 'asset_dependent'))
CANDIDATES = [
    {'provider': 'NOAA NODD', 'platforms': ['GOES-18', 'GOES-19'], 'sensor': 'ABI', 'product': 'L1b RadF / L2 LSTF',
     'search_supported': False, 'access': '제품별 공개 S3 목록·NetCDF. 앱 내 미연결; 미국 중심 관측 범위와 fixed-grid 투영 검사 필요. 클라우드 연산 비용 별도.',
     'source': 'https://www.noaa.gov/nodd/datasets'},
    {'provider': '기상청', 'platforms': ['GK2A'], 'sensor': 'AMI', 'product': 'LE1B / L2 지표면온도',
     'search_supported': False, 'access': '앱 내 미연결. API 활용신청·authKey 필요. 전구/동아시아/한반도 영역·채널별 NetCDF/미리보기 확인 필요.',
     'source': 'https://apihub.kma.go.kr/apiList.do?seqApi=6'},
    {'provider': 'NASA CMR', 'platforms': ['NOAA-20', 'NOAA-21'], 'sensor': 'VIIRS', 'product': 'VJ109GA / VJ209GA 후보',
     'search_supported': False, 'access': '앱 내 미연결. 각 버전·보유기간·컬렉션·밴드 검토 후 별도 등록; VNP09GA를 다른 플랫폼으로 간주하지 않음.',
     'source': 'https://viirsland.gsfc.nasa.gov/Products/NASA/ReflectanceESDR.html'},
    {'provider': 'Copernicus / NASA', 'platforms': ['Sentinel-3', 'Sentinel-2', 'Landsat-8', 'Landsat-9'], 'sensor': 'SLSTR / MSI / OLI',
     'product': 'SLSTR L2 LST', 'search_supported': False,
     'access': '앱 내 미연결. 처리 수준·열 해상도·권한·버전별 반사도/QA 검토 후 연결. 기존 A3/A4 자동 적용 금지.',
     'source': 'https://documentation.dataspace.copernicus.eu/APIs/STAC.html'},
]
