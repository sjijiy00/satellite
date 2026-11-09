"""Disposable bounded raster process, supervised by pixel_quality. JSON in/out."""
import json
import sys
import warnings
from .pixel_policy import QualityError
from .pixel_raster import process_pixels,quality_previews
from .range_reader import RangeStore
from .change_analysis import process_change
from .cloud_composite import process_composite
from .cloud_estimate import process_estimate


def main():
    store=None
    try:
        payload=json.load(sys.stdin)
        urls={asset['path']:asset['url'] for s in payload['scenes'] for asset in s['assets'].values()}
        store=RangeStore(urls)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore',DeprecationWarning)
            mode=payload.get('analysis_mode')
            if mode in ('composite_plan','composite_execute'):result=process_composite(payload,store)
            elif mode in ('estimate_plan','estimate_execute'):result=process_estimate(payload,store)
            elif mode=='ndvi_change':result=process_change(payload,store)
            else:
                result=process_pixels(payload,store,capture=True)
                arrays=result.pop('_analysis_arrays')
                result['map_layers']={'quality':quality_previews(payload,arrays),'analysis':None}
        result['transfer']={'bytes':store.bytes,'requests':store.requests,'files':store.info,'mode':'HTTP HEAD + 검증된 206 Range만; 전체 GET 없음'}
    except Exception as e:
        result={'status':'failed','error':str(e) if isinstance(e,QualityError) else '래스터 처리 실패: 결과 미확인',
                'common_valid_area_m2':None,'common_valid_percent_aoi':None,'common_valid_percent_observed':None}
    finally:
        if store:store.close()
    sys.stdout.write(json.dumps(result,ensure_ascii=True,allow_nan=False))


if __name__=='__main__':main()
