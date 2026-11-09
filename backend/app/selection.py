"""A1 selection guard only: no pixel/asset/header inspection or feasibility verdict."""
from shapely.geometry import shape, box
from shapely.geometry import mapping
from .evaluation import projected_area
import math


def footprint_metrics(bbox, geometry_a, geometry_b):
    """A2 geometric areas only; missing geometry is not zero valid pixels."""
    empty = {'aoi_area_m2':None,'scene_a_percent':None,'scene_b_percent':None,
             'common_area_m2':None,'common_percent':None,'geometry':None}
    try:
        a, b = shape(geometry_a), shape(geometry_b)
        if any(not g.is_valid or g.is_empty or g.geom_type not in ('Polygon','MultiPolygon') for g in (a,b)):
            return empty
        aoi=box(*bbox)
        common=aoi.intersection(a).intersection(b)
        total=projected_area(aoi,bbox)
        area=projected_area(common,bbox)
        if not math.isfinite(area) or not math.isfinite(total) or total<=0:return empty
        pct=lambda g:round(max(0,min(100,projected_area(g,bbox)/total*100)),6)
        return {'aoi_area_m2':round(total,3),'scene_a_percent':pct(aoi.intersection(a)),
                'scene_b_percent':pct(aoi.intersection(b)), 'common_area_m2':area,
                'common_percent':pct(common),'geometry':mapping(common) if area>0 else None,
                'method':'AOI 중심 LAEA 등적 투영 · 경계 0.02도 세분화 · 촬영 footprint 근사 면적 (유효 픽셀 아님)'}
    except Exception:
        return empty


def common_footprint(query):
    try:
        if not query.geometry_a or not query.geometry_b:
            return {'common_geometry': None, 'message': '촬영 범위가 누락되어 공통 영역을 확인하지 못했습니다.'}
        a, b = shape(query.geometry_a), shape(query.geometry_b)
        if any(not g.is_valid or g.geom_type not in ('Polygon', 'MultiPolygon') for g in (a, b)):
            raise ValueError('Invalid footprint')
        # Only positive-area existence in lon/lat, never a metric area calculation.
        exists = box(*query.bbox).intersection(a).intersection(b).area > 0
        return {'common_geometry': exists, 'message': 'AOI 안에 공통 촬영 영역이 있습니다. 이 기하 검사는 픽셀 품질을 검사하지 않습니다.' if exists else 'AOI 안에 두 영상의 공통 촬영 영역이 없습니다.'}
    except Exception:
        return {'common_geometry': None, 'message': '촬영 범위 형식 오류로 공통 영역을 확인하지 못했습니다.'}
