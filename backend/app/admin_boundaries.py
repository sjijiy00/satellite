"""Versioned, sourced administrative boundary proposals. Search remains bbox-only."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from shapely.geometry import shape, box, Point
from .evaluation import projected_area

ROOT=Path(__file__).parent/'data/boundaries'
REGISTRY={'서울특별시':{'stem':'seoul-sgis-2025-q2','aliases':('서울','서울시','서울특별시'),
    'admin_level':'시·도','parents':('',None,'대한민국'),'provider_codes':('11','1100000000')},
    '제주특별자치도':{'stem':'jeju-sgis-2025-q2','aliases':('제주','제주도','제주특별자치도'),
    'admin_level':'시·도','parents':('',None,'대한민국'),'provider_codes':('39','50','5000000000')}}
ALIASES={alias:name for name,record in REGISTRY.items() for alias in record['aliases']}


def canonical_name(name):
    provinces={'충남':'충청남도','충북':'충청북도','경남':'경상남도','경북':'경상북도','전남':'전라남도','전북':'전북특별자치도','전라북도':'전북특별자치도','강원':'강원특별자치도','강원도':'강원특별자치도','경기':'경기도'}
    parts=name.strip().split()
    if parts:parts[0]=provinces.get(parts[0],parts[0])
    normalized=' '.join(parts)
    return ALIASES.get(normalized,normalized)


@lru_cache(maxsize=4)
def load_boundary(name):
    record=REGISTRY[name];stem=record['stem'] # trusted registration only; never a caller file path
    meta=json.loads((ROOT/(stem+'.metadata.json')).read_text(encoding='utf-8'))
    if meta['crs']!='EPSG:4326' or meta['axis_order']!='longitude, latitude':raise ValueError('Unexpected output CRS/axis contract')
    raw=(ROOT/(stem+'.geojson')).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=meta['geojson_sha256']:raise ValueError('Boundary hash mismatch')
    feature=json.loads(raw);g=shape(feature['geometry'])
    if not g.is_valid or g.geom_type not in ('Polygon','MultiPolygon') or feature['properties']['code']!=meta['code'] or meta['name']!=name:raise ValueError('Invalid boundary')
    if not all(abs(a-b)<1e-10 for a,b in zip(g.bounds,meta['bbox'])):raise ValueError('Boundary bounds mismatch')
    if not (124<g.bounds[0]<g.bounds[2]<132 and 32<g.bounds[1]<g.bounds[3]<39):raise ValueError('Wrong axis order')
    return meta,feature,g


def propose(region):
    missing={'status':'unsupported','message':'등록된 검증 행정경계가 없습니다. 점 위치로 지도만 이동하고 AOI는 직접 지정하세요.'}
    name=canonical_name(region.get('name',''));record=REGISTRY.get(name)
    if not record:return missing
    if region.get('admin_level')!=record['admin_level'] or region.get('parent') not in record['parents']:
        return {'status':'mismatch','message':'행정 단계·상위 지역이 등록한 경계와 일치하지 않습니다.'}
    code=str(region.get('region_code') or '')
    if code and code not in record['provider_codes']:
        return {'status':'mismatch','message':'제공처 행정코드가 등록한 경계와 일치하지 않습니다.'}
    try:
        meta,feature,g=load_boundary(name)
        if not g.covers(Point(*region['center'])):return {'status':'mismatch','message':'제공처 중심점이 등록한 경계에 포함되지 않습니다.'}
        bbox=list(g.bounds);area=projected_area(box(*bbox),bbox)/1e6
        return {'status':'proposed','id':meta['id'],'name':meta['name'],'code':meta['code'],'code_system':meta['code_system'],
            'geometry':g.simplify(0.00005,preserve_topology=True).__geo_interface__ if name=='제주특별자치도' else feature['geometry'],
            'display_simplification':'제주 지도 윤곽만 위경도0.00005도 허용오차로 간소화. bbox는 원본 전체 꼭짓점에서 계산.' if name=='제주특별자치도' else None,
            'bbox':bbox,'year':meta['year'],'source':meta['source'],'source_url':meta['source_url'],
            'terms':meta['terms'],'original_crs':meta['original_crs'],'crs':meta['crs'],'axis_order':meta['axis_order'],
            'geojson_sha256':meta['geojson_sha256'],'note':meta['note'],
            'match_basis':'지명 별칭·시도 단계·상위 지역·중심점 포함 및 제공된 경우 행정코드 대조',
            'search_scope':'행정경계 외접 범위','polygon_clipping':False,'boundary_area_km2':meta['area_km2'],'bbox_area_km2':area,
            'search_supported':True,'pixel_area_limit_km2':25,'pixel_area_exceeded':area>25,
            'message':'검증한 행정경계의 외접 bbox입니다. 명시 조건은 자동 적용하며 수동값 충돌은 확인합니다. 픽셀 처리는 25 km² 이하 S2 조건만 지원하며 폴리곤 클리핑은 하지 않습니다.'}
    except (OSError,ValueError,KeyError,TypeError):
        return {'status':'failed','message':'경계 자료 검증에 실패했습니다. 임의 사각형으로 대체하지 않습니다. 지도에서 AOI를 직접 지정하세요.'}
