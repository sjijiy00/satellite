"""Observed-pixel S2 period composite on A3's bounded common grid."""
import base64
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
import zipfile

import numpy as np
import shapely
from rasterio.io import MemoryFile

from .change_analysis import calibration_for_change
from .pixel_policy import LIMITS, POLICY, QualityError
from .pixel_raster import make_grid, grid_info, area_weights, project_footprint, diagnose_scene

VERSION='s2-observed-composite-2026-10-29.1'
BANDS=('red','nir','green')
FLOAT_NODATA=-9999.0
DATE_NODATA=-2147483648
EPOCH=date(1970,1,1)


def _tiff(data, grid, dtype, nodata, names, *, version=VERSION, interpretation='multi-date observed-pixel period composite; never reconstructed'):
    with MemoryFile() as memory:
        with memory.open(driver='GTiff', width=grid['width'],height=grid['height'],count=len(names),
                         dtype=dtype,nodata=nodata,crs=grid['crs'],transform=grid['transform'],
                         tiled=True,blockxsize=256,blockysize=256,compress='deflate') as dst:
            for band,(array,name) in enumerate(zip(data,names),1):
                dst.write(array.astype(dtype),band)
                dst.set_band_description(band,name)
                dst.update_tags(band,unit='UTC days since 1970-01-01' if dtype=='int32' else '1')
            dst.update_tags(processing_version=version,interpretation=interpretation)
        return memory.read()


def process_composite(payload,opener=None):
    """Plan and execute use identical reads and deterministic source selection."""
    scenes=payload['scenes']
    if not 1<=len(scenes)<=4:raise QualityError('합성 후보 장면은 1~4개입니다.')
    if payload['purpose']!='vegetation' or payload['temporal_mode']!='single':
        raise QualityError('전후 사건·생육 변화 분석은 날짜 혼합 합성을 지원하지 않습니다. 기간 요약도 원래 목적을 바꾸지 않습니다.')
    if len({(s['collection'],s['id']) for s in scenes})!=len(scenes):raise QualityError('중복 Item은 사용할 수 없습니다.')
    target=next((s for s in scenes if s['id']==payload['target_id']),None)
    if not target:raise QualityError('선택 영상이 후보에 없습니다.')
    if len({(s['platform'],s['processing_baseline']) for s in scenes})!=1 or not scenes[0]['platform'] or not scenes[0]['processing_baseline']:
        raise QualityError('동일 위성 플랫폼·처리 기준선의 Sentinel-2 L2A만 합성합니다.')
    start=date.fromisoformat(payload['start_date']);end=date.fromisoformat(payload['end_date'])
    if (end-start).days>31:raise QualityError('계획 기간 31일 초과')
    for scene in scenes:
        acquired=datetime.fromisoformat(scene['datetime'].replace('Z','+00:00')).date()
        if not start<=acquired<=end:raise QualityError('허용 기간 밖의 영상이 포함되었습니다.')
        if any(key not in scene['assets'] or not calibration_for_change(scene['assets'][key],scene) for key in BANDS):
            raise QualityError('반사도 scale/offset·제공처 보정 표시가 누락/상충합니다. 합성하지 않습니다.')
    target_day=datetime.fromisoformat(target['datetime'].replace('Z','+00:00')).date()
    priority=sorted(scenes,key=lambda s:(s['id']!=target['id'],abs((datetime.fromisoformat(s['datetime'].replace('Z','+00:00')).date()-target_day).days),
                                        s['datetime'],s['collection'],s['id']))
    grid=make_grid(payload['bbox']);aoi=area_weights(grid['aoi'],grid);total=float(aoi.sum())
    shape=(grid['height'],grid['width'])
    results=[];masks=[];values=[];footprints=[]
    for scene in priority:
        footprint=project_footprint(scene['geometry'],grid)
        footprint_weight=area_weights(footprint,grid)
        band_values={}
        result,mask=diagnose_scene(scene,grid,footprint_weight,footprint_weight,opener,bands_out=band_values)
        result.update(id=scene['id'],collection=scene['collection'],datetime=scene['datetime'],
                      valid_percent_aoi=None if result['valid_area_m2'] is None else result['valid_area_m2']/total*100,
                      date_offset_days=(datetime.fromisoformat(scene['datetime'].replace('Z','+00:00')).date()-target_day).days)
        results.append(result)
        footprints.append(footprint if result['status']=='checked' else shapely.GeometryCollection())
        masks.append(mask if mask is not None else np.zeros(shape,dtype=bool))
        values.append(band_values)
    if any(r['status']!='checked' for r in results):
        return {'status':'blocked','error':'일부 후보의 실제 품질 자료를 검사하지 못했습니다. 0%로 간주하지 않으며, 실패 후보를 제외하고 다시 계획해 주세요.',
                'scenes':results,'can_execute':False,'version':VERSION,'grid':grid_info(grid)}
    observed=area_weights(shapely.union_all(footprints),grid) if any(not g.is_empty for g in footprints) else np.zeros(shape)
    source=np.zeros(shape,dtype='uint16')
    for index,(mask,bands) in enumerate(zip(masks,values),1):
        if results[index-1]['status']!='checked':continue
        valid=mask&(aoi>0)&np.all(np.stack([np.isfinite(bands[key]) & (bands[key]>=0) for key in BANDS]),axis=0)
        source[(source==0)&valid]=index
    good=source>0
    area=float(aoi[good].sum())
    original=float(aoi[masks[0]&(aoi>0)].sum())
    observed_area=float(observed.sum())
    used=sorted(set(int(i) for i in source[good]))
    report={'status':'planned' if payload['analysis_mode']=='composite_plan' else 'succeeded',
            'version':VERSION,'checked_at':datetime.now(timezone.utc).isoformat(),
            'purpose':'vegetation','temporal_mode':'single','interpretation':'여러 날짜의 실제 관측을 선택한 기간 요약 합성; 단일 날짜 실측/AI 복원 아님',
            'target_id':target['id'],'target_date':str(target_day),'period':{'start':str(start),'end':str(end),'timezone':'UTC'},
            'date_change_allowed':payload.get('allow_date_change',False),'grid':grid_info(grid),
            'aoi_area_m2':total,'observed_area_m2':observed_area,'unobserved_area_m2':max(0,total-observed_area),
            'original_valid_area_m2':original,'composite_valid_area_m2':area,
            'composite_valid_percent_aoi':area/total*100,'remaining_gap_area_m2':max(0,total-area),
            'quality_or_nodata_excluded_area_m2':max(0,observed_area-area),
            'scenes':results,'priority':[{'index':i+1,'id':s['id'],'datetime':s['datetime'],'date_offset_days':results[i]['date_offset_days']}
                        for i,s in enumerate(priority)],
            'used_scene_count':len(used),'oldest_observation_date':min((results[i-1]['datetime'][:10] for i in used),default=None),
            'oldest_observation_age_days':max(((target_day-date.fromisoformat(results[i-1]['datetime'][:10])).days for i in used),default=None),
            'can_execute':len({s['datetime'][:10] for s in priority})>=2 and len(used)>=2 and area>0,
            'limits':{**LIMITS,'candidate_scenes':4,'period_days':31,'artifact_zip_bytes':4_000_000},
            'estimate':{'output_uncompressed_bytes':grid['width']*grid['height']*19,
                        'note':'출력 3개 float32 밴드 + 출처 uint16 + 날짜 int32 + 마스크 uint8의 상한 근사. 압축률·처리 시간은 확정할 수 없습니다. 파일 읽기는 최대 64 MiB/60초 정책.'},
            'policy':POLICY,'artifact_base64':None}
    if not report['can_execute']:
        report.update(status='blocked',error='허용 기간의 서로 다른 날짜에서 실제로 선택할 맑은 픽셀이 없습니다. 빈 영역을 임의로 채우지 않습니다.')
        return report
    if payload['analysis_mode']=='composite_plan':return report
    output=np.full((3,*shape),FLOAT_NODATA,dtype='float32')
    dates=np.full(shape,DATE_NODATA,dtype='int32')
    for index,(scene,bands) in enumerate(zip(priority,values),1):
        selected=source==index
        for channel,key in enumerate(BANDS):output[channel,selected]=bands[key][selected]
        dates[selected]=(date.fromisoformat(scene['datetime'][:10])-EPOCH).days
    files={'analysis_bands.tif':_tiff(output,grid,'float32',FLOAT_NODATA,BANDS),
           'valid_mask.tif':_tiff([good.astype('uint8')],grid,'uint8',0,('observed_valid_1_excluded_0',)),
           'source_index.tif':_tiff([source],grid,'uint16',0,('source_index_1_based',)),
           'source_date.tif':_tiff([dates],grid,'int32',DATE_NODATA,('UTC_days_since_1970_01_01',))}
    manifest={k:v for k,v in report.items() if k!='artifact_base64'}
    manifest.update(processing_version=VERSION,band_order=list(BANDS),source_index_mapping=[
        {'index':i+1,'collection':s['collection'],'id':s['id'],'datetime':s['datetime'],'item_url':s.get('item_url'),
         'assets':{key:{'href':s['assets'][key]['url'],'scale':s['assets'][key]['scale'],
                         'offset':s['assets'][key]['offset'],'nodata':s['assets'][key]['nodata']}
                   for key in (*BANDS,'scl')}} for i,s in enumerate(priority)],
        selection_rule='target scene first, then smallest absolute day difference, earlier acquisition, collection, Item ID; all bands from one scene per output pixel',
        source_date_encoding='int32 UTC days since 1970-01-01; NoData -2147483648',
        boundary_area_note='summary uses fractional AOI/footprint cell area; TIFF mask is whole 20 m cells',
        files={name:{'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)} for name,content in files.items()},
        official_sources=POLICY['sources'])
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,content in files.items():archive.writestr(name,content)
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,allow_nan=False,indent=2))
    artifact=buffer.getvalue()
    if len(artifact)>4_000_000:raise QualityError('합성 ZIP 4 MB 초과. AOI를 줄여 주세요.')
    # Reopen every real generated file before a successful job is reported.
    with zipfile.ZipFile(io.BytesIO(artifact)) as archive:
        for name in files:
            with MemoryFile(archive.read(name)) as mem:
                with mem.open() as raster:
                    if raster.crs is None or raster.width!=grid['width'] or raster.height!=grid['height'] or raster.nodata is None:
                        raise QualityError('생성 GeoTIFF 재열기/CRS/NoData 검증 실패')
                    if raster.count!=(3 if name=='analysis_bands.tif' else 1):raise QualityError('생성 GeoTIFF 밴드 수 오류')
    report['artifact_base64']=base64.b64encode(artifact).decode('ascii')
    report['artifact_name']='sentinel-2-observed-composite.zip'
    report['artifact_size_bytes']=len(artifact)
    return report
