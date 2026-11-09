"""A4: bounded two-date Sentinel-2 L2A NDVI difference on A3's common grid."""
import base64
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import zipfile
from urllib.parse import urlsplit, urlunsplit

import numpy as np
from rasterio.io import MemoryFile

from .pixel_policy import POLICY
from .pixel_raster import process_pixels, radiometry, quality_previews, difference_preview
from .range_reader import public_cog


VERSION = 's2-l2a-ndvi-change-2026-10-29.1'
NODATA = -9999.0
DENOMINATOR_MIN = 1e-6  # numerical guard in unitless reflectance, not vegetation threshold
SOURCES = [
    'https://sentiwiki.copernicus.eu/web/s2-products',
    'https://documentation.dataspace.copernicus.eu/notebook-samples/openeo/NDVI_Timeseries.html',
    'https://documentation.dataspace.copernicus.eu/APIs/SentinelHub/Data/S2L2A.html',
]


def safe_item_url(url):
    try:
        parsed = urlsplit(url)
        if (parsed.scheme == 'https' and parsed.hostname == 'earth-search.aws.element84.com'
                and not (parsed.username or parsed.password or parsed.query or parsed.fragment)):
            return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))
    except (TypeError, ValueError):pass
    return None


def calibration_for_change(asset, scene):
    """Require metadata consistent with the documented S2 baseline and provider flag."""
    status = radiometry(asset, scene)
    if status['status'] != 'confirmed_metadata':return False
    try:baseline = float(scene['processing_baseline'])
    except (TypeError, ValueError, KeyError):return False
    scale,offset = status['scale'],status['offset']
    if not math.isclose(scale, 1/10000, rel_tol=0, abs_tol=1e-10):return False
    applied = scene.get('boa_offset_applied')
    if applied is not True and applied is not False:return False
    if baseline < 4:
        return applied is False and math.isclose(offset,0,rel_tol=0,abs_tol=1e-10)
    return ((applied is True and math.isclose(offset,0,rel_tol=0,abs_tol=1e-10)) or
            (applied is False and math.isclose(offset,-0.1,rel_tol=0,abs_tol=1e-10)))


def ndvi(red, nir, qa_mask):
    """Return a finite NDVI raster and a mask; never turn invalid arithmetic into 0."""
    red = red.astype('float64', copy=False)
    nir = nir.astype('float64', copy=False)
    denominator = nir + red
    valid = qa_mask & np.isfinite(red) & np.isfinite(nir) & (red >= 0) & (nir >= 0) & (denominator > DENOMINATOR_MIN)
    values = np.full(red.shape, np.nan, dtype='float64')
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        np.divide(nir-red, denominator, out=values, where=valid)
    valid &= np.isfinite(values) & (values >= -1-1e-6) & (values <= 1+1e-6)
    values[~valid] = np.nan
    values[valid] = np.clip(values[valid], -1, 1)
    return values, valid


def geotiff_bytes(arrays, mask, grid):
    profile = dict(driver='GTiff', width=grid['width'], height=grid['height'],
                   transform=grid['transform'], crs=grid['crs'], tiled=True,
                   blockxsize=256, blockysize=256, compress='deflate', predictor=3)
    with MemoryFile() as mem:
        with mem.open(**profile, count=3, dtype='float32', nodata=NODATA) as dst:
            for i, (name, array) in enumerate(zip(('NDVI_before','NDVI_after','NDVI_difference_after_minus_before'), arrays), 1):
                dst.write(np.where(mask, array, NODATA).astype('float32'), i)
                dst.set_band_description(i, name)
                dst.update_tags(i, unit='1', long_name=name)
            dst.update_tags(processing_version=VERSION, mask_file='valid_mask.tif',
                            formula='NDVI=(NIR-RED)/(NIR+RED); difference=after-before',
                            interpretation='index difference on common valid pixels; not classified vegetation change')
        image = mem.read()
    with MemoryFile() as mem:
        with mem.open(**(profile | {'predictor':2}), count=1, dtype='uint8', nodata=0) as dst:
            dst.write(mask.astype('uint8'), 1)
            dst.set_band_description(1, 'common_valid_mask_1_valid_0_invalid')
            dst.update_tags(1,unit='1')
        quality_mask = mem.read()
    return image, quality_mask


def process_change(payload, opener=None, *, precomputed=None, artifact_limit=4_000_000):
    """Reuses A3 reads/masks; an unconfirmed calibration yields no export."""
    report = precomputed if precomputed is not None else process_pixels(payload, opener, capture=True)
    arrays = report.pop('_analysis_arrays')
    report['map_layers']={'quality':quality_previews(payload,arrays),'analysis':None}
    report.pop('analysis_ready',None)
    report.update(version=VERSION, checked_at=datetime.now(timezone.utc).isoformat(),
                  analysis='two-date NDVI difference', artifact_base64=None,
                  analysis_completed=False)

    def blocked(reason):
        report.update(status='blocked', error=reason, conclusion='NDVI 변화를 계산하지 않았습니다.',
                      analysis_area_m2=None, excluded_common_area_m2=None,
                      numeric_excluded_area_m2=None, ndvi_before_mean=None,
                      ndvi_after_mean=None, ndvi_difference_mean=None)
        return report

    if payload.get('purpose') != 'vegetation':return blocked('A4는 식생 NDVI 전후 차이만 지원합니다.')
    if len(payload['scenes']) != 2 or payload['scenes'][0]['id'] == payload['scenes'][1]['id']:
        return blocked('서로 다른 두 Item이 필요합니다.')
    try:
        dates = [datetime.fromisoformat(s['datetime'].replace('Z','+00:00')) for s in payload['scenes']]
        if dates[0] >= dates[1] or dates[0].date() == dates[1].date():return blocked('서로 다른 UTC 날짜의 이전→이후 순서가 필요합니다.')
    except (KeyError, ValueError, TypeError):return blocked('취득시각이 누락되거나 잘못되었습니다.')
    baselines = [s.get('processing_baseline') for s in payload['scenes']]
    if not all(baselines) or baselines[0] != baselines[1]:return blocked('동일 처리 기준선이 확인되지 않습니다.')
    if report['status'] != 'checked':return blocked('두 장면의 A3 픽셀 검사에 실패해 공통 유효 픽셀을 확인할 수 없습니다.')
    if report['common_observed_area_m2'] <= 0 or not report['common_valid_area_m2']:
        return blocked('두 날짜의 공통 유효 픽셀이 없습니다.')
    if any({'red','nir'} - set(s['required_keys']) for s in payload['scenes']):
        return blocked('NDVI 필수 적색·근적외선 밴드가 없습니다.')
    if any(not all(calibration_for_change(scene['assets'][key],scene) for key in ('red','nir'))
           for scene in payload['scenes']):
        return blocked('처리 기준선·제공처 보정 표시·scale/offset이 서로 일치하지 않습니다. 보정값을 추정하지 않습니다.')
    raw_masks = arrays['masks']
    bands = arrays['bands']
    if any(m is None for m in raw_masks) or any(not {'red','nir'} <= set(b) for b in bands):
        return blocked('필수 밴드의 실제 픽셀 또는 품질 마스크가 없습니다.')
    ndvis = [ndvi(b['red'], b['nir'], m) for b,m in zip(bands,raw_masks)]
    weights = arrays['common_weights']
    qa_common = raw_masks[0] & raw_masks[1] & (weights > 0)
    valid = qa_common & ndvis[0][1] & ndvis[1][1]
    area = float(weights[valid].sum())
    if not math.isfinite(area) or area <= 0:return blocked('분모 0·NaN/Inf·음수 반사도 제외 후 분석할 공통 픽셀이 없습니다.')
    before, after = ndvis[0][0], ndvis[1][0]
    difference = after - before
    if not np.all(np.isfinite(difference[valid])):return blocked('NDVI 차이에 NaN/Inf가 발생해 결과를 내보내지 않습니다.')
    means = [float(np.sum(value[valid]*weights[valid]) / area) for value in (before,after,difference)]
    if not all(math.isfinite(v) for v in means):return blocked('NDVI 평균이 유한하지 않습니다.')

    image, mask_file = geotiff_bytes((before,after,difference), valid, arrays['grid'])
    common = report['common_observed_area_m2']
    qa_area = float(weights[qa_common].sum())
    report.update(status='computed', error=None, analysis_completed=True,
                  analysis_area_m2=area, excluded_common_area_m2=common-area,
                  excluded_aoi_area_m2=report['aoi_area_m2']-area,
                  qa_excluded_area_m2=common-qa_area,
                  numeric_excluded_area_m2=qa_area-area,
                  ndvi_before_mean=means[0], ndvi_after_mean=means[1],
                  ndvi_difference_mean=means[2],
                  conclusion='두 날짜의 공통 유효 픽셀에서 NDVI 전후·차이를 계산했습니다. 변화 원인이나 식생 증감을 확정하는 분류는 아닙니다.')
    report['map_layers']['analysis']=difference_preview(difference,valid,arrays['grid'],[s['id'] for s in payload['scenes']])
    manifest = {
        'processing_version':VERSION, 'checked_at':report['checked_at'],
        'analysis':'Sentinel-2 L2A two-date NDVI difference',
        'formula':'NDVI=(NIR-RED)/(NIR+RED); difference=after-before',
        'required_bands':['red/B04','nir/B08','scl'],
        'radiometry':'STAC raster:bands DN * scale + offset; baseline/boa_offset_applied/scale/offset consistency required; conflicting/missing calibration blocks analysis',
        'numeric_policy':{'denominator_must_exceed':DENOMINATOR_MIN,'negative_reflectance':'exclude',
                          'nonfinite':'exclude','ndvi_range':[-1,1],'classification_threshold':None},
        'mask_policy':POLICY, 'grid':report['grid'],
        'area_method':'20 m LAEA cell intersections with AOI and both footprints; fractional boundary areas',
        'mask_interpretation':'valid_mask.tif: 1 both dates valid, 0 excluded/outside AOI. Border pixels are whole raster cells but summary areas use fractional AOI/footprint overlap.',
        'areas_m2':{k:report[k] for k in ('aoi_area_m2','common_observed_area_m2','analysis_area_m2',
                                            'excluded_common_area_m2','excluded_aoi_area_m2',
                                            'qa_excluded_area_m2','numeric_excluded_area_m2')},
        'means':{'before':means[0],'after':means[1],'difference':means[2]},
        'input':{'bbox':payload['bbox'],'reference_date':payload.get('reference_date'),
                 'purpose':payload['purpose'],'minimum_valid_percent':payload.get('minimum_valid_percent')},
        'sources':[{'id':s['id'],'collection':s['collection'],'datetime':s['datetime'],
                    'item_url':safe_item_url(s.get('source_url')),'processing_baseline':s['processing_baseline'],
                    'boa_offset_applied':s.get('boa_offset_applied'),
                    'assets':{k:{'href':v['url'] if public_cog(v.get('url')) else None,
                                 'nodata':v['nodata'],'scale':v.get('scale'),
                                 'offset':v.get('offset'),
                                 'etag':getattr(opener,'info',{}).get(v['path'],{}).get('etag')}
                              for k,v in s['assets'].items() if k in ('red','nir','scl')}}
                   for s in payload['scenes']],
        'file_headers':[s['headers'] for s in report['scenes']],
        'files':{'ndvi_change.tif':{'sha256':hashlib.sha256(image).hexdigest(),'bands':['before','after','after-minus-before'],
                                    'dtype':'float32','nodata':NODATA,'unit':'NDVI (unitless)'},
                 'valid_mask.tif':{'sha256':hashlib.sha256(mask_file).hexdigest(),'dtype':'uint8','nodata':0,'valid':1}},
        'official_sources':SOURCES,'sources_checked_on':'2026-10-29',
        'interpretation':'NDVI difference is a candidate signal. Season, phenology, illumination, atmosphere and sensor/platform differences need review.'}
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        archive.writestr('ndvi_change.tif',image)
        archive.writestr('valid_mask.tif',mask_file)
        archive.writestr('processing.json',json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False))
    artifact=buffer.getvalue()
    if len(artifact)>artifact_limit:return blocked('내보내기 크기 상한 4 MB 초과. AOI를 줄여 주세요.')
    report['artifact_base64']=base64.b64encode(artifact).decode('ascii')
    report['artifact_name']='sentinel-2-ndvi-change.zip'
    report['artifact_size_bytes']=len(artifact)
    return report
