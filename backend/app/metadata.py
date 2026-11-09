import math
from urllib.parse import urlparse
from .assets import raster_assets
from .safe_urls import safe_url
from .provider_registry import PROVIDERS, COLLECTION_REGISTRY, PLATFORMS, PRODUCTS
from .access_paths import identity


def number(value):
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def web_url(value):
    return safe_url(value)

def execution_candidates(item):
    # Display candidates from the same server catalog; actual access/QA remains pending.
    from .analysis_catalog import METHODS
    p=item.get('properties') or {};level=p.get('s2:product_type') or p.get('landsat:processing_level') or p.get('landsat:correction') or p.get('processing:level')
    found=[m for m in METHODS.values() if any(v['collection']==item.get('collection') and level in v['levels'] and p.get('platform') in v['platforms'] and set(v['required_keys'])<=set(item.get('assets',{})) for v in m.get('products',[]))]
    return [m['id'] for m in found],('제품별 조건 확인 후 '+', '.join(m['label'] for m in found)+' 후보 · 실제 파일/QA/범위는 미검사') if found else None


def normalize(item):
    """Preserve missing fields; derive band resolutions only from supplied metadata."""
    p, assets = item.get('properties') or {}, item.get('assets') or {}
    registration = COLLECTION_REGISTRY.get(item.get('collection'), {})
    methods,processing_candidate=execution_candidates(item)
    provider_id = registration.get('provider_id', 'earth-search')
    auth = PRODUCTS.get(registration.get('product_id'), {}).get('file_access') == 'authentication_required'
    resolutions, bands = set(), set()
    if (gsd := number(p.get('gsd'))) is not None and gsd > 0:
        resolutions.add(gsd)
    band_details = []
    for key, asset in assets.items():
        values = [number(asset.get('gsd'))] + [number(b.get('spatial_resolution')) for b in asset.get('raster:bands', [])]
        values = sorted({v for v in values if v is not None and v > 0})
        resolutions.update(values)
        names = [b.get('common_name') for b in asset.get('eo:bands', []) if b.get('common_name')]
        bands.update(names)
        if names:
            band_details.append({'asset': key, 'bands': names, 'resolution_m': values})
    cloud = number(p.get('eo:cloud_cover'))
    if provider_id == 'copernicus' or (cloud is not None and not 0 <= cloud <= 100):
        cloud = None
    links = item.get('links') or []
    thumbnail = next((web_url(a.get('href')) for a in assets.values()
                      if 'thumbnail' in a.get('roles', []) and a.get('type') in ('image/jpeg', 'image/png', 'image/webp') and web_url(a.get('href'))), None)
    previews=[(k,a) for k,a in assets.items() if any(r in a.get('roles',[]) for r in ('thumbnail','overview','browse','visual')) or any(w in k.lower() for w in ('thumb','browse'))]
    image_previews=[a for _,a in previews if a.get('type','').split(';')[0] in ('image/jpeg','image/png','image/webp')]
    preview_status=('missing_asset' if not previews else 'unsupported_format' if not image_previews else
        'requester_pays' if all(a.get('storage:requester_pays') for a in image_previews) else 'unchecked')
    source = next((web_url(link.get('href')) for link in links if link.get('rel') == 'self' and web_url(link.get('href'))), None)
    return {'id': item['id'], 'collection': item.get('collection'), 'geometry': item.get('geometry'),'source_product':identity(item),
            'datetime': p.get('datetime'), 'platform': p.get('platform'),'source_platform':p.get('app:source_platform'), 'instruments': p.get('instruments') or [],
            'resolution_m': sorted(resolutions), 'band_details': band_details, 'bands': sorted(bands),
            'scene_cloud_cover': cloud, 'processing_level': p.get('processing:level') or p.get('landsat:processing_level') or p.get('landsat:correction') or p.get('s2:product_type'),
            'provider': PROVIDERS[provider_id]['name'], 'provider_id': provider_id,
            'product_id': registration.get('product_id'), 'remote_collection': registration.get('remote_id'),
            'sensor_ids': PLATFORMS.get(p.get('platform'), {}).get('sensor_ids', []),
            'product_type': p.get('product:type') or p.get('s2:product_type'),
            'end_datetime': p.get('end_datetime'),'geometry_role':p.get('app:geometry_role','scene_footprint'),'temporal_role':p.get('app:temporal_role'),
            'sar': {k: p.get(k) for k in ('sar:instrument_mode','sar:polarizations','sat:orbit_state','sat:relative_orbit',
                    'sar:resolution_range','sar:resolution_azimuth','sar:pixel_spacing_range','sar:pixel_spacing_azimuth')} if provider_id == 'copernicus' else None,
            'output_grid': p.get('app:output_grid'), 'native_resolution': p.get('app:native_resolution'), 'hls':p.get('app:hls'),
            'support': {'search': True,'analysis_methods':methods, 'processing': processing_candidate or ('S2 전용 조건 검사 후 지원' if item.get('collection') == 'sentinel-2-l2a' else '검색·메타데이터만 지원; 앱 내 픽셀 처리 미지원'),
                        'file_access': 'authentication_required' if auth else 'asset_dependent', 'access_verified': False},
            'source_url': source, 'thumbnail': thumbnail,
            'preview_diagnostic': {'status':preview_status,'has_candidate':bool(image_previews),
                'message':{'missing_asset':'미리보기 Asset 없음 · 실제 자료 부재와 별개',
                    'unsupported_format':'visual/browse는 있으나 현재 미리보기 형식 미지원',
                    'requester_pays':'미리보기 Asset은 requester-pays S3에 있음 · 제공처의 다른 경로 확인 필요',
                    'unchecked':'미리보기 링크 있음 · 실제 접근은 미검사'}[preview_status]},
            'download_assets': raster_assets(assets,authentication_required=auth,signing_required=registration.get('access')=='anonymous_sas',provider=PROVIDERS[provider_id]['name'])}
