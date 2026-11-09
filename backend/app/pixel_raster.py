"""Small-AOI S2 raster reads, quality diagnostics, and display previews."""
import math
import base64
import struct
import zlib
import numpy as np
import rasterio
from rasterio.transform import from_origin
from rasterio.windows import Window,from_bounds
from rasterio.warp import reproject,transform_bounds,Resampling
from pyproj import Transformer,CRS
from shapely.geometry import box,shape
import shapely
from .pixel_policy import LIMITS,POLICY,QualityError


def make_grid(bbox,*,limits=None):
    limits=limits or LIMITS
    w,s,e,n=bbox
    crs=f'+proj=laea +lat_0={(s+n)/2} +lon_0={(w+e)/2} +datum=WGS84 +units=m'
    project=Transformer.from_crs(4326,crs,always_xy=True).transform
    aoi=shapely.transform(box(*bbox).segmentize(.001),project,interleaved=False)
    if not math.isfinite(aoi.area) or not 0<aoi.area<=limits['aoi_km2']*1e6:raise QualityError(f"AOI는 0보다 크고 {limits['aoi_km2']} km² 이하여야 합니다. 지도에서 작은 영역을 다시 선택하세요.")
    res=limits['resolution_m'];west,south,east,north=aoi.bounds
    west=math.floor(west/res)*res;north=math.ceil(north/res)*res
    width=math.ceil((east-west)/res);height=math.ceil((north-south)/res)
    if width*height>limits['grid_pixels']:raise QualityError('공통 격자 픽셀 수 상한 초과. 길쭉한 AOI를 줄여 주세요.')
    return {'crs':crs,'transform':from_origin(west,north,res,res),'width':width,'height':height,'aoi':aoi,'bbox':bbox}


def grid_info(g):
    t=g['transform']
    return {'crs':CRS.from_user_input(g['crs']).to_wkt(),'resolution_m':abs(t.a),
            'transform':list(t)[:6],'extent':[t.c,t.f-g['height']*abs(t.e),t.c+g['width']*t.a,t.f],
            'width':g['width'],'height':g['height'],'pixel_count':g['width']*g['height'],
            'area_method':POLICY['area_method'],'scl_resampling':'nearest','reflectance_resampling':'average'}


def _png_rgba(pixels):
    """Small bounded map preview; GeoTIFF remains the quantitative artifact."""
    height,width,_=pixels.shape
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    rows=b''.join(b'\0'+pixels[row].tobytes() for row in range(height))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+
            chunk(b'IDAT',zlib.compress(rows,6))+chunk(b'IEND',b''))


def map_preview(pixels,g,label,scene_ids):
    t=g['transform'];west,north=t.c,t.f;east=west+g['width']*t.a;south=north+g['height']*t.e
    to_wgs84=Transformer.from_crs(g['crs'],4326,always_xy=True)
    corners=[list(to_wgs84.transform(x,y)) for x,y in ((west,north),(east,north),(east,south),(west,south))]
    return {'png_base64':base64.b64encode(_png_rgba(pixels)).decode('ascii'),'coordinates':corners,
            'label':label,'scene_ids':scene_ids,'source':'실제 AOI 픽셀의 화면 시각화; 정확한 수치·격자는 GeoTIFF/검사 결과를 사용'}


def quality_previews(payload,arrays):
    g=arrays['grid'];aoi=area_weights(g['aoi'],g)>0
    output=[]
    for scene,mask in zip(payload['scenes'],arrays['masks']):
        if mask is None:continue
        inside=aoi&(area_weights(project_footprint(scene['geometry'],g),g)>0)
        rgba=np.zeros((g['height'],g['width'],4),dtype='uint8')
        rgba[inside&~mask]=[238,126,54,145]
        rgba[inside&mask]=[13,160,113,100]
        output.append(map_preview(rgba,g,'실제 SCL·NoData 유효 마스크: 녹색 유효, 주황 제외', [scene['id']]))
    return output


def difference_preview(difference,mask,g,scene_ids):
    rgba=np.zeros((*difference.shape,4),dtype='uint8')
    positive=mask&(difference>0);negative=mask&(difference<0);neutral=mask&~positive&~negative
    rgba[positive]=[28,146,83,150];rgba[negative]=[156,54,137,150];rgba[neutral]=[120,120,120,120]
    return map_preview(rgba,g,'실제 NDVI 차이 화면 표시: 녹색 양수, 보라 음수, 회색 0; 변화 원인 판정 아님',scene_ids)


def area_weights(geometry,g):
    rows,cols=np.indices((g['height'],g['width']));t=g['transform']
    left=t.c+cols*t.a;top=t.f+rows*t.e
    cells=shapely.box(left,top+t.e,left+t.a,top)
    return shapely.area(shapely.intersection(cells,geometry)).astype('float64')


def project_footprint(geometry,g):
    footprint=shape(geometry)
    if not footprint.is_valid or footprint.geom_type not in ('Polygon','MultiPolygon'):raise QualityError('촬영 범위 형식 오류')
    clipped=box(*g['bbox']).intersection(footprint)
    project=Transformer.from_crs(4326,g['crs'],always_xy=True).transform
    return shapely.transform(clipped.segmentize(.001),project,interleaved=False).intersection(g['aoi'])


def read_native(path,asset,g,opener=None,*,profile=None):
    with rasterio.open(path,opener=opener,driver='GTiff',sharing=False) as src:
        if src.count!=1 or not src.crs or src.transform.b!=0 or src.transform.d!=0 or src.transform.a<=0 or src.transform.e>=0:
            raise QualityError('단일 밴드·북쪽 위 격자·파일 CRS 조건 미충족')
        if not src.crs.is_projected or src.crs.linear_units!='metre':raise QualityError('원본 격자 단위/CRS 미지원')
        if profile:
            expected=asset.get('nodata')
            explicit_fill=asset.get('bitmask_fill')==1 and expected==1 and src.nodata is None
            if expected is not None and src.nodata!=expected and not explicit_fill:raise QualityError('파일 헤더와 제품 NoData 메타데이터가 다릅니다.')
            if expected is None and src.nodata not in (None,0):raise QualityError('문서화되지 않은 QA NoData입니다.')
            if src.dtypes[0]!=asset['dtype']:raise QualityError('파일 헤더와 제품 자료형이 다릅니다.')
        elif src.nodata!=0 or asset['nodata']!=0:raise QualityError('파일 헤더와 STAC NoData=0 조건 불일치/미확인')
        if not src.is_tiled:raise QualityError('window 읽기에 부적합한 비타일 TIFF는 중단합니다.')
        if any(x*y>4_194_304 for x,y in src.block_shapes):raise QualityError('원본 압축 블록 크기 상한 초과')
        if not all(any(abs(v-r)<.001 for r in (asset['resolutions'] if profile else (10,20))) for v in src.res):raise QualityError('검증된 제품의 원본 출력 격자 해상도가 아닙니다.')
        bounds=transform_bounds(g['crs'],src.crs,*grid_info(g)['extent'],densify_pts=21)
        win=from_bounds(*bounds,transform=src.transform)
        left=max(0,math.floor(win.col_off)-2);top=max(0,math.floor(win.row_off)-2)
        right=min(src.width,math.ceil(win.col_off+win.width)+2);bottom=min(src.height,math.ceil(win.row_off+win.height)+2)
        if right<=left or bottom<=top:raise QualityError('AOI에 읽을 원본 픽셀이 없습니다.')
        if (right-left)*(bottom-top)>LIMITS['source_window_pixels']:raise QualityError('원본 window 픽셀 수 상한 초과')
        window=Window(left,top,right-left,bottom-top)
        data=src.read(1,window=window)
        mask=src.read_masks(1,window=window)>0
        if profile and asset.get('zero_valid'):mask=np.ones(data.shape,dtype=bool) # QA_RADSAT=0 means unsaturated, never NoData.
        if profile and (src.scales[0]!=1 or src.offsets[0]!=0):
            if not math.isclose(src.scales[0],asset['scale'],abs_tol=1e-10,rel_tol=0) or not math.isclose(src.offsets[0],asset['offset'],abs_tol=1e-10,rel_tol=0):raise QualityError('실제 헤더와 STAC 보정값이 상충합니다. 중복 보정을 하지 않습니다.')
        header={'crs':src.crs.to_string(),'transform':list(src.transform)[:6],'width':src.width,'height':src.height,
                'nodata':src.nodata,'dtype':src.dtypes[0],'resolution':list(src.res),'block_shapes':src.block_shapes,
                'window':[left,top,right-left,bottom-top],'file_header_read':True,
                'header_scale':src.scales[0],'header_offset':src.offsets[0],
                'source':'실제 GeoTIFF 헤더 + AOI window; header 기본 scale=1/offset=0은 보정 근거로 추정하지 않음'}
        return data,mask,src.window_transform(window),src.crs,header


def warp(array,src_t,src_crs,dst_shape,dst_t,dst_crs,method,nodata=None):
    dst=np.full(dst_shape,0 if nodata is None else nodata,dtype=array.dtype)
    reproject(array,dst,src_transform=src_t,src_crs=src_crs,dst_transform=dst_t,dst_crs=dst_crs,
              src_nodata=nodata,dst_nodata=0 if nodata is None else nodata,resampling=method,num_threads=1)
    return dst


def radiometry(asset,scene):
    scale,offset=asset.get('scale'),asset.get('offset');applied=scene.get('boa_offset_applied')
    valid=all(type(x) in (float,int) and math.isfinite(x) for x in (scale,offset)) and scale>0
    conflict=applied is True and valid and offset!=0
    return {'status':'confirmed_metadata' if valid and not conflict else 'unknown',
            'scale':scale if type(scale) in (float,int) and math.isfinite(scale) else None,
            'offset':offset if type(offset) in (float,int) and math.isfinite(offset) else None,'boa_offset_applied':applied,
            'source':'원본 STAC raster:bands',
            'message':'DN × scale + offset, NoData 제거 후 적용' if valid and not conflict else
                      '보정 메타데이터 누락/상충. 임의 보정하지 않으며 DN 유효성만 검사; 반사도 값·지수는 제공하지 않음'}


def diagnose_scene(scene,g,weights,common_weights,opener=None,bands_out=None):
    evidence=[];rad=[];valid=None
    shape_out=(g['height'],g['width'])
    try:
        if weights.sum()<=0:raise QualityError('AOI 내 촬영 픽셀이 없습니다.')
        scl=scene['assets']['scl']
        values,source_mask,t,crs,header=read_native(scl['path'],scl,g,opener)
        evidence.append({'key':'scl',**header})
        if values.dtype!=np.uint8:raise QualityError('SCL 파일 자료형이 uint8이 아닙니다.')
        values=np.where(source_mask,values,0).astype('uint8')
        dest_scl=warp(values,t,crs,shape_out,g['transform'],g['crs'],Resampling.nearest)
        accepted=np.isin(dest_scl,POLICY['accepted_scl']);valid=accepted.copy()
        has_samples=bool(np.any((dest_scl>0)&(weights>0)))
        for key in scene['required_keys']:
            asset=scene['assets'][key]
            dn,mask,bt,bcrs,bheader=read_native(asset['path'],asset,g,opener)
            evidence.append({'key':key,**bheader})
            if dn.dtype!=np.uint16:raise QualityError('반사도 원본 파일 자료형이 uint16이 아닙니다.')
            native_scl=warp(values,t,crs,dn.shape,bt,bcrs,Resampling.nearest)
            base_valid=mask&(dn!=0)&np.isfinite(dn)
            # The read window includes a halo: samples outside the AOI must not
            # turn an empty AOI into a measured 0% result.
            sample_fraction=warp(base_valid.astype('float32'),bt,bcrs,shape_out,g['transform'],g['crs'],Resampling.average)
            has_samples=has_samples and bool(np.any((sample_fraction>0)&(weights>0)))
            source_valid=base_valid&np.isin(native_scl,POLICY['accepted_scl'])
            calibration=radiometry(asset,scene);rad.append({'key':key,**calibration})
            numeric=dn.astype('float32')
            if calibration['status']=='confirmed_metadata':numeric=numeric*calibration['scale']+calibration['offset']
            numeric[~source_valid]=np.nan
            averaged=warp(numeric,bt,bcrs,shape_out,g['transform'],g['crs'],Resampling.average,np.nan)
            fraction=warp(source_valid.astype('float32'),bt,bcrs,shape_out,g['transform'],g['crs'],Resampling.average)
            valid&=(fraction>=.999)&np.isfinite(averaged)
            if bands_out is not None:bands_out[key]=averaged
        reasons={}
        for label,classes in [('nodata',[0]),('saturated',[1]),('dark_or_topographic_shadow',[2]),('cloud_shadow',[3]),
                              ('unclassified',[7]),('cloud_cirrus',[8,9,10]),('snow_ice',[11])]:
            reasons[label]=float(weights[np.isin(dest_scl,classes)].sum())
        reasons['unknown_scl']=float(weights[~np.isin(dest_scl,list(range(12)))].sum())
        reasons['band_nodata_or_mixed_invalid']=float(weights[accepted&~valid].sum())
        if not has_samples:
            return {'status':'no_pixels','error':'읽은 범위에 SCL/필수 밴드의 관측 픽셀이 없습니다. 0%로 판정하지 않습니다.',
                    'valid_area_m2':None,'valid_in_common_area_m2':None,'exclusions_m2':reasons,'headers':evidence,'radiometry':rad},None
        area=float(weights[valid].sum());inside=float(common_weights[valid].sum())
        return {'status':'checked','error':None,'valid_area_m2':area,'valid_in_common_area_m2':inside,
                'observed_area_m2':float(weights.sum()),'excluded_area_m2':float(weights.sum())-area,
                'exclusions_m2':reasons,'headers':evidence,'radiometry':rad},valid
    except Exception as e:
        message=str(e) if isinstance(e,QualityError) else getattr(opener,'failure',None) or '래스터/품질 자료 읽기 또는 격자 처리 실패. 결과는 미확인입니다.'
        return {'status':'failed','error':message,'valid_area_m2':None,'valid_in_common_area_m2':None,
                'exclusions_m2':None,'headers':evidence,'radiometry':rad},None


def process_pixels(payload,opener=None,*,capture=False,grid=None):
    g=grid if grid is not None else make_grid(payload['bbox']);aoi_weights=area_weights(g['aoi'],g)
    geoms=[project_footprint(s['geometry'],g) for s in payload['scenes']]
    weights=[area_weights(geom,g) for geom in geoms]
    common_weights=area_weights(geoms[0].intersection(geoms[1]),g)
    total=float(aoi_weights.sum());common=float(common_weights.sum())
    results=[];masks=[];bands=[]
    for i,scene in enumerate(payload['scenes']):
        values={} if capture else None
        result,mask=diagnose_scene(scene,g,weights[i],common_weights,opener,bands_out=values)
        result.update(id=scene['id'],datetime=scene['datetime'],observed_area_m2=float(weights[i].sum()))
        result['valid_percent_aoi']=None if result['valid_area_m2'] is None else result['valid_area_m2']/total*100
        result['valid_percent_common']=None if result['valid_in_common_area_m2'] is None or common==0 else result['valid_in_common_area_m2']/common*100
        results.append(result);masks.append(mask);bands.append(values)
    area=float(common_weights[masks[0]&masks[1]].sum()) if all(m is not None for m in masks) and common>0 else None
    pct=None if area is None else area/common*100
    report={'status':'checked' if area is not None else 'partial' if any(r['status']=='checked' for r in results) else 'failed',
            'scenes':results,'grid':grid_info(g),'policy':POLICY,'limits':LIMITS,
            'aoi_area_m2':total,'common_observed_area_m2':common,
            'common_valid_area_m2':area,'common_valid_percent_aoi':None if area is None else area/total*100,
            'common_valid_percent_observed':pct,'common_excluded_area_m2':None if area is None else common-area,
            'operational_threshold':{'minimum_percent':payload['minimum_valid_percent'],'denominator':'두 시점 공통 촬영 영역',
                'met':None if pct is None else pct>=payload['minimum_valid_percent'],'note':'사용자가 조정할 수 있는 운영 기준이며 보편적 과학 기준/분석 가능 확정이 아닙니다.'},
            'analysis_ready':False,'conclusion':'SCL·NoData 기반 관측 유효성 진단입니다. 실제 변화·침수·식생 지수는 계산하지 않았습니다.'}
    if capture:report['_analysis_arrays']={'grid':g,'common_weights':common_weights,'masks':masks,'bands':bands}
    return report
