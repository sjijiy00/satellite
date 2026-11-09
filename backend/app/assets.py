from urllib.parse import urlparse
from .safe_urls import safe_url


def raster_assets(assets, *, authentication_required=False,signing_required=False,provider=None):
    """Expose original raster URLs without inventing HTTPS replacements for S3 assets."""
    result = []
    for key, asset in assets.items():
        href, media_type = asset.get('href'), asset.get('type') or ''
        if not safe_url(href, ('https', 'http', 's3')):
            continue
        if not (media_type.startswith(('image/tiff','image/vnd.stac.geotiff')) or media_type in ('image/jp2', 'image/geotiff', 'application/zip', 'application/x-hdf5', 'application/x-hdf', 'application/x-netcdf')):
            continue
        requester_pays = asset.get('storage:requester_pays') is True
        auth = authentication_required or bool(asset.get('auth:refs'))
        direct = urlparse(href).scheme in ('https','http') and not requester_pays and not auth and not signing_required
        result.append({'key': key, 'title': asset.get('title') or key, 'href': href,
                       'filename':urlparse(href).path.rsplit('/',1)[-1], 'size_bytes':asset.get('file:size') if isinstance(asset.get('file:size'),int) and asset['file:size']>=0 else None,
                       'provider':provider,'signing_required':signing_required,
                       'common_names': [b['common_name'] for b in asset.get('eo:bands', []) if b.get('common_name')],
                       'roles': asset.get('roles') or [],
                       'raster_metadata': asset.get('raster:bands') or [],
                       'media_type': media_type, 'direct_url': href if direct else None,
                       'requester_pays': requester_pays,
                       'authentication_required': auth, 'access_verified': False,
                       'access_status': 'requester_pays' if requester_pays else 'authentication_required' if auth else 'anonymous_sas' if signing_required else 'http_unverified' if direct else 's3_only',
                       'access_note': '공개 웹 파일 링크 · 개별 접근 상태는 미검사' if direct else
                       'AWS 인증 및 요청자 비용 동의 필요' if requester_pays else '제공처 계정 인증 필요 · 다운로드 미검증' if auth else '계정 불필요 · 서버 단기 SAS 경유 · 파일 접근 미검증' if signing_required else 'S3 주소 · 브라우저 직접 다운로드 미지원'})
    return sorted(result, key=lambda a: (a['direct_url'] is None, a['key'] != 'visual', a['key']))
