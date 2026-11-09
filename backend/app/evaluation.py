from datetime import datetime
from pyproj import Transformer
from shapely.geometry import box, shape
from shapely import transform
from .purpose_plan import purpose_plan
from .sensor_catalog import CATALOG


def projected_area(geometry, bbox):
    """Reuse one local equal-area method for individual and common footprints."""
    w, s, e, n = bbox
    project = Transformer.from_crs('EPSG:4326', f'+proj=laea +lat_0={(s+n)/2} +lon_0={(w+e)/2} +datum=WGS84 +units=m', always_xy=True).transform
    return transform(geometry.segmentize(0.02), project, interleaved=False).area


def overlap_percent(geometry, bbox):
    """Area of AOI/footprint intersection using local equal-area projection, not pixel coverage."""
    if not geometry:
        return None
    try:
        footprint, aoi = shape(geometry), box(*bbox)
        if not footprint.is_valid or footprint.geom_type not in ('Polygon', 'MultiPolygon'):
            return None
        # Densify geographic edges before projection to reduce chord error.
        area = projected_area(aoi, bbox)
        intersection = aoi.intersection(footprint)
        return round(max(0, min(100, projected_area(intersection, bbox) / area * 100)), 2)
    except Exception:
        return None


def evaluate(item, query, purpose):
    """Expose ranking evidence, with feasibility always deferred until pixel inspection."""
    item['overlap_percent'] = overlap_percent(item['geometry'], query.bbox)
    days = None
    try:
        captured = datetime.fromisoformat(item['datetime'].replace('Z', '+00:00')).date()
        days = (captured - query.start_date).days
    except (TypeError, ValueError, AttributeError):
        pass
    item['purpose_plan'] = purpose_plan(item, purpose)
    profile = CATALOG.get(item['purpose_plan'].get('profile_id'))
    if profile:
        item['native_resolution'] = item.get('native_resolution') or profile['native_resolution']
        item['output_grid'] = item.get('output_grid') or profile['output_grid']
    item['pixel_quality'] = {'status':'not_checked','message':'실제 장면 픽셀 QA 미검사'}
    plan = item['purpose_plan']
    sensor_match = None if plan.get('metadata_only') else not plan['missing_bands'] if item['bands'] else None
    reason = plan['analysis'] + (' — 필요 밴드 미확인: ' + ', '.join(plan['missing_bands']) if plan['missing_bands'] else '')
    item['evaluation'] = {'status': '판정 보류', 'label': '예비 적합성 평가', 'days_from_start': days,
                          'sensor_match': sensor_match, 'sensor_reason': reason,
                          'limitations': ['픽셀 검사를 수행하지 않았습니다.', '장면 구름량은 AOI 구름량이 아닙니다.', '촬영 범위 중첩은 유효 관측률이 아닙니다.']}
    return item


def rank_key(item):
    """Lexicographic order avoids inventing a scientific quality score."""
    sensor = {True: 0, False: 1, None: 2}[item['evaluation']['sensor_match']]
    overlap, cloud = item['overlap_percent'], item['scene_cloud_cover']
    days = item['evaluation']['days_from_start']
    return (sensor, -(overlap if overlap is not None else -1), cloud if cloud is not None else 101,
            min(item['resolution_m'], default=float('inf')), abs(days) if days is not None else float('inf'), item.get('collection') or '', item['id'])
