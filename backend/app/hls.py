"""Reviewed HLS v2 CMR assets. Product facts never come from natural-language AI.

Sources: CMR UMM collections C2021957657/7295-LPCLOUD and NASA HLS L30/S30
product descriptions, checked 2026-11-02. Asset URLs MUST occur in the granule.
"""
import math
import re
from urllib.parse import urlsplit
from .safe_urls import safe_url

COLLECTIONS = {
    'hls-l30-002': {'concept': 'C2021957657-LPCLOUD', 'short_name': 'HLSL30', 'family': 'L30',
                    'doi': '10.5067/HLS/HLSL30.002', 'start': '2013-04-11'},
    'hls-s30-002': {'concept': 'C2021957295-LPCLOUD', 'short_name': 'HLSS30', 'family': 'S30',
                    'doi': '10.5067/HLS/HLSS30.002', 'start': '2015-11-28'},
}
COMMON = {'B01':'coastal', 'B02':'blue', 'B03':'green', 'B04':'red'}
L30_BANDS = {**COMMON, 'B05':'nir', 'B06':'swir16', 'B07':'swir22'}
S30_BANDS = {**COMMON, 'B05':'rededge', 'B06':'rededge', 'B07':'rededge',
             'B08':'nir', 'B8A':'nir08', 'B11':'swir16', 'B12':'swir22'}
KEYS = {'L30': {f'B{i:02}' for i in range(1,12)},
        'S30': {f'B{i:02}' for i in range(1,13)} | {'B8A'}}
ANGLES = {'SAA','SZA','VAA','VZA'}


def assets(entry, collection):
    spec = COLLECTIONS[collection]
    title = entry.get('title', '')
    if not re.fullmatch(r'HLS\.'+spec['family']+r'\.T[0-9A-Z]{5}\.\d{7}T\d{6}\.v2\.0', title):
        raise ValueError('HLS product identity mismatch')
    result = {}
    for link in entry.get('links', []):
        href = safe_url(link.get('href'), ('https',))
        if not href or link.get('inherited'): continue
        u = urlsplit(href)
        if u.hostname != 'data.lpdaac.earthdatacloud.nasa.gov' or u.query: continue
        parts = u.path.split('/')
        if len(parts) != 5 or parts[1] not in ('lp-prod-public','lp-prod-protected') or parts[2] != spec['short_name']+'.020' or parts[3] != title:
            continue
        name = parts[4]
        rel = link.get('rel','')
        if rel.endswith('/browse#') and name == title+'.jpg':
            result['browse'] = {'href':href,'type':'image/jpeg','roles':['thumbnail'],
                                'title':'NASA HLS 제공처 true-color browse · 분석 원본 아님'}
            continue
        if not rel.endswith('/data#') or not name.startswith(title+'.') or not name.endswith('.tif'): continue
        key = name[len(title)+1:-4]
        if key not in KEYS[spec['family']] | ANGLES | {'Fmask'}: continue
        common = (L30_BANDS if spec['family']=='L30' else S30_BANDS).get(key)
        quality = key == 'Fmask'
        brightness = spec['family']=='L30' and key in ('B10','B11')
        description = ('Fmask 비트 품질 마스크 · S2 SCL과 다른 스키마, 앱 미검사' if quality else
                       'TOA 밝기온도 · 지표면온도 제품 아님' if brightness else
                       '관측 기하 각도' if key in ANGLES else 'HLS 30 m 반사도/광학 밴드')
        asset = {'href':href,'type':'image/tiff','roles':['quality'] if quality else ['metadata'] if key in ANGLES else ['data'],
                 'title':key+' · '+description,'gsd':30}
        if common: asset['eo:bands']=[{'common_name':common,'name':key}]
        if common:
            asset['raster:bands']=[{'scale':0.0001,'offset':0,'unit':'unitless'}]
        if brightness:asset['raster:bands']=[{'scale':0.01,'unit':'Celsius (TOA BT)'}]
        result[key]=asset
    return result


def properties(entry, collection):
    spec=COLLECTIONS[collection]
    try: cloud=float(entry['cloud_cover'])
    except (KeyError,TypeError,ValueError):cloud=None
    if cloud is not None and (not math.isfinite(cloud) or not 0<=cloud<=100):cloud=None
    return {'datetime':entry.get('time_start'),'end_datetime':entry.get('time_end'),
        # CMR JSON granules do not identify the individual input platform here.
        'platform':None,'instruments':['OLI / OLI-2 input family' if spec['family']=='L30' else 'MSI input family'],
        'processing:level':'HLS v2.0 NBAR','product:type':spec['short_name']+' v2.0 · 광학 NBAR 지표반사도',
        'eo:cloud_cover':cloud,'gsd':30,'app:geometry_role':'product_tile_extent',
        'app:native_resolution': 'Landsat OLI 반사도 30 m 원자료 계열; 개별 입력 플랫폼은 CMR JSON 미제공' if spec['family']=='L30' else 'MSI 원자료 밴드별 10/20/60 m → HLS 30 m 재격자화',
        'app:output_grid':'HLS UTM/MGRS 30 m · 경계 내 유효 픽셀 보장 아님',
        'app:hls':{'short_name':spec['short_name'],'version':'2.0','original_id':entry['title'],
            'doi':spec['doi'],'source':'https://hls.gsfc.nasa.gov/products-description/'+spec['family'].lower()+'/',
            'scale_note':'반사도 scale=0.0001. Fmask 비트 QA는 S2 SCL과 다름; 픽셀 QA·분석·합성·ML 미지원.',
            'temporal_note':'CMR 관측 시작/종료 메타데이터. 파일명 시각을 타일 내 모든 픽셀의 촬영시각으로 간주하지 않음.',
            'not_surface_temperature':True}}
