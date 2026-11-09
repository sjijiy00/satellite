"""One fixed grid, bounded windows; reuse the A3 pixel/QA and A4 arithmetic."""
import copy
import numpy as np
import shapely
from shapely.geometry import shape
from pyproj import Transformer
from rasterio.transform import Affine
from .pixel_policy import LIMITS,QualityError
from .pixel_raster import make_grid,process_pixels,area_weights,project_footprint,grid_info

GRID_LIMITS={**LIMITS,'aoi_km2':50,'grid_pixels':150000}
TILE_EDGE=160
MAX_TILES=16
SINGLE_METHODS={'ndvi','mndwi','ndbi','surface_temperature','hotspots','temperature_comparison','thermal_gapfill'}
SINGLE_LIMITS={**GRID_LIMITS,'aoi_km2':200,'grid_pixels':600000}
SINGLE_MAX_TILES=36

def processing_grid(payload):
    single=payload.get('method_id') in SINGLE_METHODS
    g=make_grid(payload['bbox'],limits={**(SINGLE_LIMITS if single else GRID_LIMITS),'resolution_m':payload.get('grid_resolution_m',20)})
    if payload.get('method_id')=='thermal_ml':g=make_grid(payload['bbox'],limits={**GRID_LIMITS,'aoi_km2':25,'grid_pixels':100000,'resolution_m':30})
    roi=payload.get('roi',{})
    if roi.get('mode')=='polygon':
        geometry=shape(roi['geometry'])
        project=Transformer.from_crs(4326,g['crs'],always_xy=True).transform
        g['aoi']=shapely.transform(geometry.segmentize(.001),project,interleaved=False)
    count=((g['height']+TILE_EDGE-1)//TILE_EDGE)*((g['width']+TILE_EDGE-1)//TILE_EDGE)
    if count>(SINGLE_MAX_TILES if single else MAX_TILES):raise QualityError('총 타일 수 상한입니다. 길쭉한 AOI를 줄여 주세요. 검색 범위는 바꾸지 않습니다.')
    return g,count

def tiled_pixels(payload,opener):
    g,count=processing_grid(payload);height,width=g['height'],g['width']
    records=[None,None];masks=[np.zeros((height,width),dtype=bool) for _ in range(2)]
    bands=[{k:np.full((height,width),np.nan,dtype='float32') for k in s['required_keys']} for s in payload['scenes']]
    for top in range(0,height,TILE_EDGE):
        for left in range(0,width,TILE_EDGE):
            tile={**g,'height':min(TILE_EDGE,height-top),'width':min(TILE_EDGE,width-left),
                  'transform':g['transform']*Affine.translation(left,top)}
            result=process_pixels(payload,opener,capture=True,grid=tile)
            arrays=result.pop('_analysis_arrays');sl=np.s_[top:top+tile['height'],left:left+tile['width']]
            for i,r in enumerate(result['scenes']):
                # An empty geometric tile is not a provider failure or a zero
                # quality measurement. A real read failure aborts the whole job.
                if r['observed_area_m2']>0 and r['status']=='failed':raise QualityError(r['error'])
                if records[i] is None:
                    records[i]={**copy.deepcopy(r),'headers':[],'exclusions_m2':{},'sample_seen':False}
                out=records[i];out['headers'].extend(r.get('headers',[]))
                if r.get('radiometry'):out['radiometry']=r['radiometry']
                for key,value in (r.get('exclusions_m2') or {}).items():out['exclusions_m2'][key]=out['exclusions_m2'].get(key,0)+value
                if r['status']=='checked':out['sample_seen']=True
                mask=arrays['masks'][i]
                if mask is not None:masks[i][sl]=mask
                for key,value in (arrays['bands'][i] or {}).items():bands[i][key][sl]=value
    total_weights=area_weights(g['aoi'],g);total=float(total_weights.sum())
    footprints=[project_footprint(s['geometry'],g) for s in payload['scenes']]
    observed=[area_weights(f,g) for f in footprints]
    common=area_weights(footprints[0].intersection(footprints[1]),g);common_area=float(common.sum())
    if total<=0:raise QualityError('확정 AOI의 면적이 없습니다.')
    for i,r in enumerate(records):
        if not r.pop('sample_seen'):raise QualityError('AOI에서 실제 관측 픽셀을 확인하지 못했습니다. 품질 비율은 미확인입니다.')
        valid=float(observed[i][masks[i]].sum());inside=float(common[masks[i]].sum())
        r.update(status='checked',error=None,observed_area_m2=float(observed[i].sum()),valid_area_m2=valid,
                 valid_in_common_area_m2=inside,excluded_area_m2=float(observed[i].sum())-valid,
                 valid_percent_aoi=valid/total*100,valid_percent_common=inside/common_area*100 if common_area else None)
    valid=float(common[masks[0]&masks[1]].sum())
    percent=valid/common_area*100 if common_area else None
    report={**result,'status':'checked','error':None,'scenes':records,'grid':grid_info(g),
            'limits':{**GRID_LIMITS,'tile_edge':TILE_EDGE,'maximum_tiles':MAX_TILES},
            'aoi_area_m2':total,'common_observed_area_m2':common_area,'common_valid_area_m2':valid,
            'common_valid_percent_aoi':valid/total*100,'common_valid_percent_observed':percent,
            'common_excluded_area_m2':common_area-valid,
            'operational_threshold':{'minimum_percent':payload['minimum_valid_percent'],'met':None if percent is None else percent>=payload['minimum_valid_percent']},
            'tiling':{'tile_count':count,'tile_edge':TILE_EDGE,'one_global_grid':True,'overlap_counted_once':True},
            '_analysis_arrays':{'grid':g,'common_weights':common,'masks':masks,'bands':bands}}
    return report
