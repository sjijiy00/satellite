"""Single source of purpose requirements for sensor cards and actual asset selection."""
from .sensor_catalog import CATALOG, RULE_VERSION
from .provider_registry import COLLECTION_REGISTRY
RULES = {
    'vegetation': {
        'label': '식생 분석', 'required': ['red', 'nir'],
        'analysis': 'NDVI = (NIR − Red) / (NIR + Red)',
        'visual': ['nir', 'red', 'green'], 'visual_title': '식생 강조 가색상',
        'visual_note': 'QGIS/ArcGIS RGB 채널에 NIR → Red → Green 순서로 지정합니다. NDVI 계산 결과는 별도로 단일밴드 의사색상으로 표시할 수 있습니다.',
    },
    'flood': {
        'label': '침수·수역 분석', 'required': ['green', 'swir16'],
        'analysis': 'MNDWI = (Green − SWIR1) / (Green + SWIR1)',
        'visual': ['green', 'swir16'], 'visual_title': 'MNDWI 수역지수 색상도',
        'visual_note': '두 반사도 밴드로 MNDWI를 계산한 뒤 단일밴드 의사색상으로 표시합니다. 고정 임계값으로 침수를 확정하지 않으며 전후 영상·구름·그림자 검사가 필요합니다.',
    },
    'urban': {
        'label': '도시·토지피복 변화', 'required': ['swir16', 'nir'],
        'analysis': 'NDBI = (SWIR1 − NIR) / (SWIR1 + NIR), 전후 영상 비교 후보',
        'visual': ['swir22', 'swir16', 'red'], 'visual_title': '도시 강조 가색상',
        'visual_note': 'QGIS/ArcGIS RGB 채널에 SWIR2 → SWIR1 → Red 순서로 지정합니다. 나지와 시가지의 혼동, 계절 차이는 별도 검사가 필요합니다.',
    },
    'thermal': {
        'label': '열환경 분석', 'required': ['thermal'],
        'analysis': '열적외선/지표온도 제품 후보 — 제품 유형과 scale·offset 확인 필요',
        'visual': ['thermal'], 'visual_title': '온도 단일밴드 색상도',
        'visual_note': 'Landsat Level-2 지표온도 제품인지 확인하고 scale·offset 및 단위를 적용한 뒤 단일밴드 의사색상으로 표시합니다. 자연색 visual로 온도를 판독하지 않습니다.',
    },
}
ALIASES = {'nir': ['nir', 'nir08'], 'thermal': ['lwir11']}
RULES['vegetation'].update(profiles=['s2_msi','landsat_oli'], preferred='sentinel-2-l2a', observation='광학 다중분광 지표반사도', reason='적색·근적외선으로 식생 상태와 변화 후보를 살펴봅니다.')
RULES['flood'].update(profiles=['s1_csar','s2_msi','landsat_oli'], preferred='sentinel-2-l2a', observation='장마·홍수는 SAR 우선 검토; 맑은 시기의 광학은 보완 관측', reason='SAR의 주야간·구름 관측 특성을 먼저 검토합니다. 광학 수역지수는 맑은 시기의 보완 자료입니다.')
RULES['urban'].update(profiles=['s2_msi','landsat_oli'], preferred='sentinel-2-l2a', observation='광학 다중분광 지표반사도', reason='근적외선·단파적외선으로 토지피복 변화 후보를 비교합니다.')
RULES['thermal'].update(profiles=['landsat_tirs'], preferred='landsat-c2-l2', observation='열적외선 기반 실제 지표온도 제품', reason='Landsat 8/9 L2SP 지표온도 제품을 검토합니다. 지표온도와 기온은 다릅니다.')
RULES['vegetation']['profiles'].append('viirs_sr')
RULES['flood']['preferred'] = 'sentinel-1-grd'
for _rule in RULES.values():
    _rule['profiles'] += ['pc_'+p for p in list(_rule['profiles']) if 'pc_'+p in CATALOG]
RULES['vegetation']['profiles'].append('noaa_viirs_ndvi')
for _purpose in ('vegetation','flood','urban'):
    RULES[_purpose]['profiles'] += ['hls_l30','hls_s30']


def required_for(purpose, profile_id):
    return ['backscatter'] if profile_id=='s1_csar' else ['ndvi'] if profile_id=='noaa_viirs_ndvi' else RULES[purpose]['required']


def product_status(item, profile_id):
    profile = CATALOG[profile_id]
    if item.get('collection') != profile['collection']:
        return 'not_met'
    if profile_id in ('hls_l30','hls_s30'):
        return 'met' if (item.get('hls') or {}).get('version')=='2.0' and item.get('processing_level') in profile['levels'] else 'unknown'
    if not item.get('platform') or not item.get('processing_level'):
        return 'unknown'
    if item['platform'] not in profile['platforms'] or item['processing_level'] not in profile['levels']:
        return 'not_met'
    return 'met'


def scene_matches_profile(item, purpose, profile_id):
    if product_status(item, profile_id) != 'met': return False
    if profile_id == 's1_csar':
        return bool(item.get('product_type') and 'GRD' in item['product_type'] and
                    (item.get('sar') or {}).get('sar:instrument_mode') and (item.get('sar') or {}).get('sar:polarizations'))
    return CATALOG[profile_id].get('metadata_search') or not item['purpose_plan']['missing_bands']


def purpose_plan(item, purpose):
    """Select actual assets, avoiding visual composites and duplicate JP2/COG copies."""
    rule = RULES[purpose]
    assets = item['download_assets']

    def pick(name):
        aliases = ALIASES.get(name, [name])
        if item.get('collection')=='hls-s30-002' and name=='nir':aliases=['nir08','nir']
        candidates = [a for a in assets if len(a['common_names']) == 1 and a['common_names'][0] in aliases
                      and 'visual' not in a['roles']]
        candidates.sort(key=lambda a: (a['direct_url'] is None, aliases.index(a['common_names'][0]),
                                       'tiff' not in a['media_type'], a['key']))
        return candidates[0]['key'] if candidates else None

    profile_id = next((p for p in rule['profiles'] if CATALOG[p]['collection'] and CATALOG[p]['collection'] == item.get('collection')), None)
    product = product_status(item, profile_id) if profile_id else 'not_met'
    if profile_id and CATALOG[profile_id].get('metadata_search'):
        profile = CATALOG[profile_id]
        keys = [a['key'] for a in assets if 'data' in a['roles']]
        return {'purpose': purpose, 'label': rule['label'], 'analysis': '등록 제품의 메타데이터 검색 후보 · 앱 내 지수·SAR 전처리·픽셀 QA 미지원',
                'metadata_only': True,
                'product_status': product, 'profile_id': profile_id, 'rule_version': RULE_VERSION,
                'analysis_keys': [], 'default_keys': keys, 'visual_keys': [], 'visual_mapping': {},
                'visual_title': '제공처 미리보기만 사용', 'visual_note': '미리보기는 정량 분석 결과가 아닙니다.',
                'missing_bands': [], 'visual_missing': [], 'group': 'primary' if item['collection'] == rule['preferred'] else 'other',
                'group_reason': 'SAR 관측 후보: 광학 수역지수와 다른 관측량' if profile_id == 's1_csar' else '광역 식생 참고 후보: 상세 광학과 다른 공간 규모',
                'preprocessing': ' '.join(profile['limitations'])}
    required = {name: pick(name) for name in rule['required']}
    if purpose == 'thermal' and product != 'met':
        required = {'thermal': None}
    visual = {name: pick(name) for name in rule['visual']}
    if purpose == 'thermal' and product != 'met':
        visual = {'thermal': None}
    # QA is optional for selection, never interpreted as an executed quality check.
    quality = [a['key'] for a in assets if a['key'] in ('scl','SCL','qa_pixel','qa_radsat','Fmask')]
    analysis_keys = list(dict.fromkeys([k for k in required.values() if k] + quality))
    visual_keys = list(dict.fromkeys([k for k in visual.values() if k] + quality))
    missing = [name for name, key in required.items() if key is None]
    preferred = rule['preferred']
    primary = COLLECTION_REGISTRY.get(item['collection'],{}).get('base_collection',item['collection']) == preferred
    if missing:
        group_reason = '필수 밴드 메타데이터 미확인: ' + ', '.join(missing)
    elif primary:
        group_reason = ('열적외선 제품을 제공하는 Landsat 우선' if purpose == 'thermal' else
                        '현재 지원 광학 센서 중 공간 세부 관측을 위한 Sentinel-2 우선')
    else:
        group_reason = '다른 위성의 대안 후보' if purpose != 'thermal' else '열적외선이 없는 광학 참고 자료'
    return {'purpose': purpose, 'label': rule['label'], 'analysis': rule['analysis'],
            'product_status': product, 'profile_id': profile_id, 'rule_version': RULE_VERSION,
            'analysis_keys': analysis_keys, 'default_keys': list(dict.fromkeys(analysis_keys + visual_keys)),
            'visual_keys': visual_keys, 'visual_mapping': visual, 'visual_title': rule['visual_title'],
            'visual_note': rule['visual_note'], 'missing_bands': missing,
            'visual_missing': [name for name, key in visual.items() if key is None],
            'group': 'primary' if primary else 'other', 'group_reason': group_reason,
            'preprocessing': '반사도/온도 scale·offset, NoData·품질 마스크를 확인하고 서로 다른 해상도의 격자를 맞춘 뒤 계산하세요. 여기서는 조합만 추천하며 지수·합성영상은 생성하지 않습니다.'}
