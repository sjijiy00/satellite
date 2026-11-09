"""Isolated canonical pixels -> verified files. stdout never contains ZIP bytes."""
import base64
from pathlib import Path
import json
import sys
import numpy as np
from rasterio.io import MemoryFile
from . import artifact_store as artifacts
from .analysis_catalog import METHODS
from .pixel_policy import QualityError
from .pixel_raster import make_grid,area_weights,project_footprint,quality_previews,grid_info
from .processing_raster import tiled_pixels
from .raster_source import open_sources
from .change_analysis import process_change
from .cloud_composite import process_composite
from .cloud_estimate import process_estimate,_false_color

def execute(payload,identifier,opener=None):
    from .product_policy import PRODUCT_METHODS
    if payload['method_id'] in PRODUCT_METHODS:
        from .product_processing import execute as execute_product
        return execute_product(payload,identifier,opener)
    method=payload['method_id'];files={}
    if method in ('s2_quality','ndvi_change'):
        precomputed=tiled_pixels(payload,opener)
        arrays=precomputed['_analysis_arrays'];grid=arrays['grid']
        if method=='ndvi_change':
            report=process_change(payload,opener,precomputed=precomputed,artifact_limit=artifacts.ZIP_LIMIT)
            if report.get('status')!='computed':raise QualityError(report.get('error') or 'NDVI 계산 보류')
            files=artifacts.unpack_artifact(base64.b64decode(report.pop('artifact_base64'),validate=True))
        else:
            report=precomputed;report.pop('_analysis_arrays')
            report['map_layers']={'quality':quality_previews(payload,arrays),'analysis':None}
            mask=(arrays['masks'][0]&arrays['masks'][1]&(arrays['common_weights']>0)).astype('uint8')
            files['valid_mask.tif']=artifacts.tiff_bytes(mask,grid,0,['common_valid_1_excluded_0'])
    else:
        report=(process_estimate if method=='local_ridge' else process_composite)(payload,opener)
        if report.get('status')!='succeeded' or not report.get('artifact_base64'):
            raise QualityError(report.get('error') or '실제 처리 산출물을 만들지 못했습니다.')
        files=artifacts.unpack_artifact(base64.b64decode(report.pop('artifact_base64'),validate=True))
        grid=make_grid(payload['bbox'])
        if 'valid_mask.tif' not in files:
            with MemoryFile(files['pixel_status.tif']) as memory:
                with memory.open() as ds:mask=(ds.read(1)>0).astype('uint8')
            files['valid_mask.tif']=artifacts.tiff_bytes(mask,grid,0,['observed_or_estimated_1_unresolved_0'])
        if 'manifest.json' in files:
            # Preserve the original model/source-date/validation evidence.
            files['engine_record.json']=files.pop('manifest.json')
        if method=='observed_composite':
            with MemoryFile(files['analysis_bands.tif']) as memory:
                with memory.open() as ds:values=ds.read()
            with MemoryFile(files['valid_mask.tif']) as memory:
                with memory.open() as ds:mask=ds.read(1)>0
            report['map_layers']={'observed':_false_color(values,mask,grid,'실제 관측 픽셀 합성 · 촬영일은 source_date.tif 참고',
                '실제 합성 밴드의 지도용 거짓색; 정량 파일은 GeoTIFF',payload['scenes'][0]['id']),'estimated':None}
    with MemoryFile(files['valid_mask.tif']) as memory:
        with memory.open() as ds:valid=ds.read(1)>0
    inside=area_weights(grid['aoi'],grid)>0
    footprints=[project_footprint(s['geometry'],grid) for s in payload['scenes']]
    geometry=footprints[0]
    for f in footprints[1:]:geometry=geometry.intersection(f) if method in ('s2_quality','ndvi_change') else geometry.union(f)
    observed=area_weights(geometry,grid)>0
    exclusion=np.zeros(valid.shape,dtype='uint8')
    exclusion[inside&~observed]=1;exclusion[inside&observed&~valid]=2;exclusion[inside&valid]=3
    files['exclusion_mask.tif']=artifacts.tiff_bytes(exclusion,grid,0,['0_outside_ROI_1_unobserved_2_excluded_3_output'])
    report['transfer']={'bytes':getattr(opener,'bytes',0),'requests':getattr(opener,'requests',0),
        'transport_requests_including_conservative_sas_checks':getattr(getattr(opener,'client',None),'requests',0),'files':getattr(opener,'info',{})}
    # Original per-engine records remain present; the common manifest adds the
    # confirmed ROI/source contract, file verification and explicit denominators.
    manifest={'version':'processing-foundation-1','input':payload['processing_input'],
        'roi_fingerprint':payload['roi_fingerprint'],'grid':grid_info(grid),
        'qa_policy_version':payload['processing_input']['qa_policy_version'],
        'resampling':{'categorical_qa':'nearest','continuous':'average after QA and NoData exclusion'},
        'units':'unitless NDVI' if method=='ndvi_change' else 'unitless reflectance' if method in ('observed_composite','local_ridge') else 'QA categorical mask',
        'mask_encoding':{'0':'outside confirmed ROI','1':'unobserved','2':'QA/NoData/numerically excluded','3':'output; ML estimates are separately identified by pixel_status.tif'},
        'record':report,'sources':[{k:s.get(k) for k in ('id','collection','datetime','platform','processing_baseline','source_url','item_url')} for s in payload['scenes']],
        'interpretation':'Actual observations, excluded values and ML estimates remain distinct. No source pixels or dates are invented.'}
    receipt=artifacts.publish(identifier,files,manifest,METHODS[method]['artifacts'],METHODS[method]['artifact_specs'])
    report.pop('artifact_name',None);report.pop('artifact_size_bytes',None)
    return {'status':'succeeded','result':artifacts.safe_value(report,include_maps=True),'artifact':receipt}

def main():
    store=None
    try:
        envelope=json.load(sys.stdin)
        artifacts.ROOT=Path(envelope['storage_root'])
        payload=envelope['payload'];store=open_sources(payload)
        result=execute(payload,envelope['job_id'],store)
    except Exception as error:
        result={'status':'failed','error':str(error) if isinstance(error,QualityError) else '실제 래스터 처리/산출물 검증 실패. 품질 값은 미확인입니다.',
                'result':{'common_valid_area_m2':None,'common_valid_percent_aoi':None},
                'failure':artifacts.safe_value(getattr(error,'failure',None))}
    finally:
        if store:store.close()
    sys.stdout.write(json.dumps(result,allow_nan=False,ensure_ascii=True))

if __name__=='__main__':main()
