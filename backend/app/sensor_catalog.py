"""Small reviewed reference catalog; data only, no second recommendation engine."""
RULE_VERSION = 'sensor-purpose-2026-10-30.2'
CHECKED_ON = '2026-10-30'
SOURCES = {
 's2': {'title':'ESA Sentinel-2 facts', 'url':'https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2/Facts_and_figures'},
 's2_l2a': {'title':'Copernicus Sentinel-2 L2A bands', 'url':'https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html'},
 's1': {'title':'ESA Sentinel-1 C-SAR instrument', 'url':'https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-1/Instrument'},
 's1_product': {'title':'Copernicus Sentinel-1 products', 'url':'https://sentiwiki.copernicus.eu/web/s1-products'},
 'l8': {'title':'USGS Landsat 8 OLI / TIRS', 'url':'https://www.usgs.gov/landsat-missions/landsat-8'},
 'l9': {'title':'NASA Landsat 9 OLI-2 / TIRS-2', 'url':'https://www.nasa.gov/wp-content/uploads/2015/04/landsat_9_fast_facts.pdf'},
 'lst': {'title':'USGS Collection 2 Surface Temperature', 'url':'https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature'},
 'eros': {'title':'USGS EROS Landsat 8/9 Level-2 제품·격자·야간 제약', 'url':'https://www.usgs.gov/centers/eros/science/usgs-eros-archive-landsat-archives-landsat-8-9-olitirs-collection-2-level-2'},
 'l2': {'title':'USGS Collection 2 Level-2 products', 'url':'https://www.usgs.gov/landsat-missions/landsat-collection-2-level-2-science-products'},
}
SOURCES.update({
 'cdse_stac': {'title':'CDSE 공식 STAC 및 Sentinel-1 GRD 컬렉션', 'url':'https://documentation.dataspace.copernicus.eu/APIs/STAC.html'},
 'viirs_sr': {'title':'NASA VIIRS Land Surface Reflectance 제품·플랫폼', 'url':'https://viirsland.gsfc.nasa.gov/Products/NASA/ReflectanceESDR.html'},
 'viirs_guide': {'title':'NASA VIIRS Surface Reflectance V2 User Guide', 'url':'https://lpdaac.usgs.gov/documents/1657/VNP09_User_Guide_V2.pdf'},
 'cmr': {'title':'NASA CMR Search API', 'url':'https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html'},
})
CATALOG = {
 's2_msi': {
  'observation':'광학 다중분광', 'payload':'MSI', 'platform_label':'Sentinel-2 A/B/C (기간별 자료)',
  'platforms':['sentinel-2a','sentinel-2b','sentinel-2c'], 'collection':'sentinel-2-l2a',
  'product':'Level-2A 지표반사도', 'levels':['S2MSI2A','L2A'],
  'bands':{'red':'B04 (10 m)','nir':'B08 (10 m)','green':'B03 (10 m)','swir16':'B11 (20 m)','swir22':'B12 (20 m)'},
  'quality':['SCL'], 'quality_keys':['scl'], 'native_resolution':'MSI 10 / 20 / 60 m (밴드별)', 'output_grid':'L2A 밴드별 10 / 20 / 60 m; SCL 기본 20 m',
  'native_m':{'red':10,'nir':10,'green':10,'swir16':20,'swir22':20},
  'limitations':['구름·그림자·눈의 영향을 받으며 주간 반사도 관측이 필요합니다.','열적외선 탑재체가 없어 직접 지표온도를 관측하지 않습니다.'],
  'sources':['s2','s2_l2a'], 'search_supported':True,
 },
 'landsat_oli': {
  'observation':'광학 다중분광', 'payload':'Landsat 8 OLI / Landsat 9 OLI-2', 'platform_label':'Landsat 8 / 9',
  'platforms':['landsat-8','landsat-9'], 'collection':'landsat-c2-l2',
  'product':'Collection 2 Level-2 지표반사도 (L2SR/L2SP)', 'levels':['L2SR','L2SP'],
  'bands':{'red':'SR_B4 (30 m)','nir':'SR_B5 (30 m)','green':'SR_B3 (30 m)','swir16':'SR_B6 (30 m)','swir22':'SR_B7 (30 m)'},
  'quality':['QA_PIXEL','QA_RADSAT'], 'quality_keys':['qa_pixel','qa_radsat'], 'native_resolution':'OLI/OLI-2 다중분광 30 m; 전정색 15 m (추천 지수에는 미사용)', 'output_grid':'Level-2 지표반사도 30 m',
  'native_m':{'red':30,'nir':30,'green':30,'swir16':30,'swir22':30},
  'limitations':['구름·그림자 영향과 혼합 픽셀을 검토해야 합니다.','Level-2 반사도에 전정색 15 m 해상도를 적용했다고 간주하지 않습니다.'],
  'sources':['l8','l9','eros','l2'], 'search_supported':True,
 },
 'landsat_tirs': {
  'observation':'열적외선', 'payload':'Landsat 8 TIRS / Landsat 9 TIRS-2', 'platform_label':'Landsat 8 / 9',
  'platforms':['landsat-8','landsat-9'], 'collection':'landsat-c2-l2',
  'product':'Collection 2 Level-2 Surface Temperature (L2SP)', 'levels':['L2SP'],
  'bands':{'thermal':'ST_B10 / Earth Search lwir11'}, 'quality':['QA_PIXEL','QA_RADSAT','ST_QA'], 'quality_keys':['qa_pixel','qa_radsat','qa'],
  'native_resolution':'TIRS/TIRS-2 열관측 100 m', 'output_grid':'ST 출력 격자 30 m (재표본화; 30 m 원관측 아님)',
  'native_m':{'thermal':100},
  'limitations':['지표온도는 지표면의 온도이며 기온이 아닙니다.','구름·방사율·ASTER 보조자료 누락으로 유효 지표온도가 없을 수 있습니다.','선택한 Level-2 ST는 주간 제품 후보입니다. 야간 요구를 충족하는 제품으로 추천하지 않습니다.'],
  'sources':['l8','l9','eros','lst'], 'search_supported':True,
 },
 's1_csar': {
  'observation':'SAR', 'payload':'C-SAR', 'platform_label':'Sentinel-1 A/B/C (검색 장면의 플랫폼 확인)',
  'platforms':['sentinel-1a','sentinel-1b','sentinel-1c'], 'collection':'sentinel-1-grd',
  'product':'Level-1 GRD / GRD COG · SAR 전처리·침수 분석 미지원', 'levels':['L1','GRD'],
  'bands':{'backscatter':'편파별 GRD 디지털 값 · 보정된 후방산란/침수 결과 아님'},
  'quality':['궤도·입사각·편파·관측모드 메타데이터'],
  'native_resolution':'관측모드·GRD 해상도 등급별 상이; IW 센서 약 5 × 20 m와 GRD 유효 해상도를 구별',
  'output_grid':'장면 sar:pixel_spacing_range/azimuth를 별도 표시; 출력 격자는 유효 해상도가 아님', 'native_m':{},
  'limitations':['주야간·구름 조건의 관측에 유리하지만 수목·도시의 산란, 지형 왜곡과 스펙클을 검토해야 합니다.','원시 GRD를 바로 침수 결과로 사용할 수 없습니다.'],
  'sources':['s1','s1_product','cdse_stac'], 'search_supported':True, 'metadata_search':True,
 },
}

CATALOG['viirs_sr'] = {
 'observation':'광학 광역 지표반사도', 'payload':'VIIRS', 'platform_label':'Suomi NPP (NOAA는 기관명)',
 'platforms':['suomi-npp'], 'collection':'viirs-vnp09ga-002', 'product':'VNP09GA.002 일별 L2G 지표반사도', 'levels':['L2G'],
 'bands':{'red':'I1 0.64 μm (500 m 출력)', 'nir':'I2 0.86 μm (500 m 출력)'},
 'quality':['QF·관측 수·관측 기하 (앱에서 픽셀 미검사)'],
 'native_resolution':'VIIRS I 밴드 nadir 375 m / M 밴드 750 m; 스캔 위치에 따라 변화',
 'output_grid':'VNP09GA SIN 일별 500 m (I) / 1 km (M)', 'native_m':{'red':375,'nir':375},
 'limitations':['광역 식생의 시간 추적 참고 후보이며 Sentinel-2 10 m 상세도 대안이 아닙니다.',
                '일별 집계 제품: 단일 순간의 촬영이 아닙니다. 구름·그림자·혼합 픽셀·관측 수를 별도 확인해야 합니다.',
                'HDF5 granule 검색만 지원합니다. 개별 밴드 존재·픽셀 QA·NDVI·합성·ML은 앱 내 미지원입니다.'],
 'sources':['viirs_sr','viirs_guide','cmr'], 'search_supported':True, 'metadata_search':True,
}

for _profile_id, _profile in CATALOG.items():
    _profile['original_access'] = 'authentication_required' if _profile_id in ('s1_csar','viirs_sr') else 'asset_dependent'
    _profile['pixel_processing_supported'] = _profile_id == 's2_msi'

# New provider paths reuse the SAME reviewed sensor/product facts. They do not
# silently extend the Earth Search-only A2/A3/A4 pixel engine to another source.
SOURCES.update({
 'pc':{'title':'Microsoft Planetary Computer public STAC and anonymous SAS','url':'https://planetarycomputer.microsoft.com/docs/concepts/sas/'},
 'noaa_ndvi':{'title':'NOAA NCEI NDVI Climate Data Record / 0.05 degree grid','url':'https://www.ncei.noaa.gov/products/climate-data-records/normalized-difference-vegetation-index'},
 'noaa_nodd':{'title':'NOAA NODD terrestrial CDR public access and terms','url':'https://registry.opendata.aws/noaa-cdr-terrestrial/'},
})
from copy import deepcopy
for _base in ('s2_msi','landsat_oli','landsat_tirs'):
    _clone=deepcopy(CATALOG[_base]);_clone['collection']='pc-'+_clone['collection']
    _clone['sources'].append('pc');_clone['pixel_processing_supported']=False;_clone['original_access']='anonymous_sas'
    _clone['limitations'].append('Planetary Computer 공개 STAC/서버 단기 SAS 경로. 현재 이 경로의 A2~A4·픽셀 QA는 미지원입니다.')
    CATALOG['pc_'+_base]=_clone
CATALOG['noaa_viirs_ndvi']={
 'observation':'광학 NDVI 기후자료레코드','payload':'VIIRS','platform_label':'NOAA-20 / JPSS-1',
 'platforms':['noaa-20'],'collection':'noaa-viirs-ndvi-cdr','product':'VIIRS NDVI CDR v1 / JP113C1 v001','levels':['daily_CDR'],
 'bands':{'ndvi':'가공된 일별 NDVI 및 품질 변수: 원본 NetCDF 내부 변수'},'quality':['원본 NetCDF 품질 플래그 (앱 내 픽셀 미검사)'],
 'native_resolution':'VIIRS 375/750 m 관측 기반의 집계·파생 제품; 출력 상세도는 0.05° 격자로 제한',
 'output_grid':'전 지구 0.05° 경위도 (남북 약 5.56 km, 동서 크기는 위도별 상이)',
 'native_m':{},'coarse_reference':True,'limitations':['광역 식생 장기 변화 참고용. 농지 필지·도시 상세 분석이나 Sentinel-2 10 m 대안이 아닙니다.',
 '단일 순간의 원관측 영상이 아닌 일별 NDVI 파생 CDR입니다. 제품 격자 포함은 픽셀 유효률이 아닙니다.',
 '이번 연결은 2023년 이후 NOAA-20 JP113C1 v001뿐입니다. NetCDF 원본 다운로드를 지원하며 미리보기·QA·재계산/합성/ML은 미지원입니다.'],
 'sources':['noaa_ndvi','noaa_nodd'],'search_supported':True,'metadata_search':True,'pixel_processing_supported':False,'original_access':'public_https',
}

SOURCES['hls']={'title':'NASA HLS L30/S30 product content, bands, scale and 30 m grid',
                'url':'https://hls.gsfc.nasa.gov/products-description/'}
for _family,_collection,_payload,_platforms in (
    ('l30','hls-l30-002','OLI / OLI-2 원자료 계열',['landsat-8','landsat-9']),
    ('s30','hls-s30-002','MSI 원자료 계열',['sentinel-2a','sentinel-2b','sentinel-2c'])):
    CATALOG['hls_'+_family]={
      'observation':'광학 조화 지표반사도 시계열','payload':_payload,
      'platform_label':'Landsat 8/9 HLS L30' if _family=='l30' else 'Sentinel-2 HLS S30',
      'platforms':_platforms,'collection':_collection,'product':'HLS'+_family.upper()+' v2.0 NBAR 지표반사도',
      'levels':['HLS v2.0 NBAR'],
      'bands':{'red':'B04 적색 반사도','nir':'B05 (L30) / B8A (S30) 조화 NIR 반사도',
               'green':'B03 녹색 반사도','swir16':'B06 (L30) / B11 (S30) SWIR1','swir22':'B07 (L30) / B12 (S30) SWIR2'},
      'quality':['Fmask 비트 품질 마스크 · 앱 내 픽셀 검사 미지원'],
      'native_resolution':'OLI 반사도 30 m 원자료' if _family=='l30' else 'MSI 밴드별 10/20/60 m 원자료 → 30 m',
      'output_grid':'HLS UTM/MGRS 30 m',
      'native_m':{'red':30,'nir':30,'green':30,'swir16':30,'swir22':30} if _family=='l30' else {'red':10,'nir':20,'green':10,'swir16':20,'swir22':20},
      'limitations':['30 m 광학 시계열 후보이며 구름 아래 복원 결과나 지표면온도 제품이 아닙니다.',
        '반사도 scale=0.0001, Fmask 비트 QA는 Sentinel-2 SCL과 다릅니다. 기존 A2~A4·합성·ML 엔진은 연결하지 않습니다.',
        '원본은 Earthdata 권한·대상 제품 이용 조건 확인 후 서버에서 명시 다운로드합니다. 개별 입력 플랫폼 누락은 미제공으로 유지합니다.'],
      'sources':['hls','cmr'],'search_supported':True,'pixel_processing_supported':False,'original_access':'authentication_required'}
