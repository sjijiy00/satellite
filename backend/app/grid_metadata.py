"""STAC projection metadata only. Never infer a missing CRS from a tile name."""
import math
import re
from pyproj import CRS


def grid_metadata(raw, key):
    asset=raw['assets'][key]
    properties=raw.get('properties') or {}
    bands=asset.get('raster:bands',[])
    if len(bands)>1 and any(k.startswith('proj:') for b in bands for k in b):
        return {'crs':None,'shape':None,'transform':None,'resolution':None,'units':None,'extent':None,
                'source_fields':{},'source':'다중 밴드별 격자 메타데이터: 개별 밴드 해석 미지원, 미확인'}
    values={k:v for k,v in properties.items() if k.startswith('proj:')}
    sources={k:'Item properties' for k in values}
    crs_fields=('proj:code','proj:epsg','proj:wkt2','proj:projjson')
    for label, fields in [('Asset',asset)]+[('raster:bands',b) for b in bands]:
        if any(k in fields for k in crs_fields):
            for k in crs_fields:
                values.pop(k,None);sources.pop(k,None)
        for k,v in fields.items():
            if k.startswith('proj:'):
                values[k]=v;sources[k]=label
    crs=None
    try:
        # Explicit null in modern code must not fall back to a legacy EPSG.
        if 'proj:code' in values:
            code=values['proj:code']
            if isinstance(code,str) and re.fullmatch(r'(EPSG|ESRI|OGC):[A-Za-z0-9]+',code):crs=CRS.from_user_input(code)
        elif isinstance(values.get('proj:epsg'),int):crs=CRS.from_epsg(values['proj:epsg'])
        if crs is None and values.get('proj:wkt2'):crs=CRS.from_wkt(values['proj:wkt2'])
        if crs is None and values.get('proj:projjson'):crs=CRS.from_json_dict(values['proj:projjson'])
    except Exception:
        crs=None
    shape=values.get('proj:shape');affine=values.get('proj:transform')
    if not isinstance(shape,list) or len(shape)!=2 or any(type(n)!=int or n<=0 for n in shape):shape=None
    if (not isinstance(affine,list) or len(affine) not in (6,9)
        or any(type(n) not in (float,int) or not math.isfinite(n) for n in affine)
        or (len(affine)==9 and affine[6:]!=[0,0,1])):affine=None
    if affine and affine[0]*affine[4]-affine[1]*affine[3]==0:affine=None
    resolution=extent=None
    if affine:
        a,b,c,d,e,f=affine[:6]
        resolution=[math.hypot(a,d),math.hypot(b,e)]
        if shape:
            points=[(a*x+b*y+c,d*x+e*y+f) for x,y in [(0,0),(shape[1],0),(0,shape[0]),(shape[1],shape[0])]]
            extent=[min(p[0] for p in points),min(p[1] for p in points),max(p[0] for p in points),max(p[1] for p in points)]
    return {'crs':crs.to_string() if crs else None,'shape':shape,'transform':affine[:6] if affine else None,
            'resolution':resolution,'units':[axis.unit_name for axis in crs.axis_info[:2]] if crs else None,
            'extent':extent,'source_fields':sources,'source':'STAC Item/Asset 메타데이터; 파일 헤더 미검사'}
