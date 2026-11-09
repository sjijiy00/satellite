"""Explicit two-date observation selection, never target-date restoration."""
from datetime import datetime, timezone, date
import numpy as np
from . import artifact_store
from .pixel_policy import QualityError
from .pixel_raster import grid_info, map_preview
from .product_policy import QA_VERSION, VERSION, SOURCES


def select(target, donor, target_valid, donor_valid, cloud, inside):
    original = inside & target_valid & np.isfinite(target)
    filled = inside & ~original & cloud & donor_valid & np.isfinite(donor)
    status = np.where(original, 1, np.where(filled, 2, 0)).astype('uint8')
    return np.where(original, target, np.where(filled, donor, np.nan)), status


def publish(payload, identifier, opener, g, weights, raw, valids, observations, clouds, records, tiles):
    from .analysis_catalog import METHODS
    from .product_processing import display
    inside = weights > 0
    ml=payload['method_id']=='thermal_ml';validation=None
    if ml:
        from .thermal_ml import estimate
        values,status,validation=estimate(raw[0][0],raw[1][0],valids[0],valids[1],clouds[0],inside,abs(g['transform'].a))
    else:values, status = select(raw[0][0], raw[1][0], valids[0], valids[1], clouds[0], inside)
    original, filled, valid = status == 1, status == 2, status > 0
    if not valid.any():
        raise QualityError('대상 날짜의 유효 온도도, 구름 영역을 채울 보충 날짜의 유효 온도도 없습니다. 다른 날짜를 선택하세요. 결측을 임의 온도로 채우지 않습니다.')
    scenes = payload['scenes']; files = {}; total = float(weights.sum())
    def area(mask): return float(weights[mask].sum())
    def stats(a, mask):
        size = area(mask)
        return dict(valid_area_m2=size, mean=float(np.sum(a[mask]*weights[mask])/size) if size else None,
                    minimum=float(a[mask].min()) if size else None, maximum=float(a[mask].max()) if size else None)
    for name, a, mask in [('target_temperature.tif', raw[0][0], original), ('estimated_only.tif' if ml else 'filled_only.tif', values if ml else raw[1][0], filled), ('estimate_with_observed.tif' if ml else 'multi_date_temperature.tif', values, valid)]:
        files[name] = artifact_store.tiff_bytes(np.where(mask, np.array([a, a-273.15]), -9999).astype('float32'), g, -9999, ['surface_temperature_kelvin', 'surface_temperature_celsius'], ['K', 'degC'])
    files['pixel_status.tif'] = artifact_store.tiff_bytes(status, g, 0, ['0_unresolved_or_outside_1_target_2_ML_estimated' if ml else '0_unresolved_or_outside_1_target_2_other_date'])
    files['valid_mask.tif'] = artifact_store.tiff_bytes(valid.astype('uint8'), g, 0, ['1_observed_or_estimated_0_invalid' if ml else '1_multi_date_valid_0_invalid'])
    exclusion = np.where(inside, np.where(valid, 3, np.where(observations[0] | observations[1], 2, 1)), 0).astype('uint8')
    files['exclusion_mask.tif'] = artifact_store.tiff_bytes(exclusion, g, 0, ['0_outside_1_unobserved_both_dates_2_unresolved_3_observed_or_estimated' if ml else '0_outside_1_unobserved_both_dates_2_unresolved_3_multi_date_valid'])
    files['donor_index.tif' if ml else 'source_index.tif'] = artifact_store.tiff_bytes(np.where(filled,2,0).astype('uint16') if ml else status.astype('uint16'), g, 0, ['2_reference_for_estimation' if ml else '1_target_2_donor'])
    days = [(date.fromisoformat(s['datetime'][:10])-date(1970, 1, 1)).days for s in scenes]
    source_date = np.where(original, days[0], np.where(filled, days[1], -2147483648)).astype('int32')
    if ml:source_date=np.where(filled,days[1],-2147483648).astype('int32')
    files['donor_date.tif' if ml else 'source_date.tif'] = artifact_store.tiff_bytes(source_date, g, -2147483648, ['reference_date_not_estimated_observation_date' if ml else 'actual_observation_date'], 'UTC days since 1970-01-01')
    summary = dict(target_date=scenes[0]['datetime'][:10], donor_date=scenes[1]['datetime'][:10],
                   original_valid_area_m2=area(original), filled_area_m2=area(filled),
                   composite_valid_area_m2=area(valid), composite_valid_percent_aoi=area(valid)/total*100,
                   remaining_gap_area_m2=area(inside & ~valid), cloud_gap_area_m2=area(inside & clouds[0] & ~original),
                   target_date_restored=False,mode='ml_estimate' if ml else 'other_date_observation')
    common = valids[0] & valids[1]; observed = observations[0] & observations[1]
    rgba = np.zeros((*status.shape, 4), dtype='uint8')
    rgba[inside & ~valid] = [238,126,54,160]; rgba[original] = [13,160,113,170]; rgba[filled] = [130,90,220,170]
    report = dict(status='checked', analysis_completed=True, analysis_label=METHODS[payload['method_id']]['label'], version=VERSION,
        checked_at=datetime.now(timezone.utc).isoformat(), scenes=records, grid=grid_info(g), aoi_area_m2=total,
        common_observed_area_m2=area(observed), common_valid_area_m2=area(common), common_valid_percent_aoi=area(common)/total*100,
        common_valid_percent_observed=area(common)/area(observed)*100 if observed.any() else None,
        common_excluded_area_m2=area(observed & ~common), cloud_fill=summary,
        statistics={'target_celsius':stats(raw[0][0]-273.15,original), 'estimated_celsius' if ml else 'other_date_fill_celsius':stats(values-273.15 if ml else raw[1][0]-273.15,filled)},
        output_summary={'sources':[{'id':s['id'],'collection':s['collection'],'datetime':s['datetime']} for s in scenes],
            'crs':g['crs'],'resolution_m':abs(g['transform'].a),'width':g['width'],'height':g['height'],
            'units':['K','degC'],'formula':'Keep valid target; fill cloud/shadow gaps only with QA-valid donor; no temporal temperature prediction', 'qa_policy_version':QA_VERSION},
        qa_policy={'version':QA_VERSION,'thermal_options':payload['processing_input']['qa_options'],
                   'note':'Both dates retain strict QA. Target cloud/dilated/cirrus/shadow bits or observed pixels rejected by minimum cloud distance; fill/snow excluded. Unrelated NoData or uncertainty-only failures remain unresolved.'},
        conclusion='다른 날짜의 실제 관측으로 구름 결측을 보충했습니다. 대상 날짜의 온도 복원·기간 평균이 아닙니다. 보충 면적이 0이면 구름 보충 효과가 없으며 남은 결측은 유지합니다.',
        tiling={'enabled':bool(payload.get('bounded_tiling')),'tiles':tiles,'failure_policy':'whole_job_failed_no_partial_artifact'},
        map_layers={'quality':[map_preview(rgba,g,'초록: 대상 날짜 · 보라: 다른 날짜 보충 · 주황: 남은 결측',[s['id'] for s in scenes])],
                    'analysis':display(values-273.15,valid,g,scenes,'여러 날짜 지표면 온도 · 원래 날짜 복원 아님','degC')},
        transfer={'bytes':getattr(opener,'bytes',0),'requests':getattr(opener,'requests',0)})
    if ml:
        report['ml_validation']=validation
        report['output_summary']['formula']='Local standardized ridge: donor Celsius, normalized x/y and interactions -> target Kelvin; original valid target unchanged'
        report['conclusion']='실제 관측과 ML 추정이 포함된 결과입니다. 맑은 영역 공간 검증을 통과했지만 구름 아래 정확도는 미검증입니다.'
        report['map_layers']={'quality':[map_preview(rgba,g,'초록: 실제 관측 · 보라: ML 추정 · 주황: 미해결',[s['id'] for s in scenes])],
            'analysis':display(values-273.15,valid,g,scenes,'지표면 온도 · 실제 관측 + ML 추정 (실측 아님)','degC')}
    manifest={'version':VERSION,'input':payload['processing_input'],'roi_fingerprint':payload['roi_fingerprint'],
              'grid':grid_info(g),'sources':scenes,'product_sources':SOURCES,'qa_policy_version':QA_VERSION,
              'source_index':{'1':scenes[0]['id'],'2':scenes[1]['id']},
              'mask_encoding':{'pixel_status.tif':{'0':'unresolved or outside AOI','1':'original target observation','2':'other-date observation'},
                               'exclusion_mask.tif':{'0':'outside AOI','1':'unobserved both dates','2':'unresolved quality/numeric gap','3':'multi-date valid'}},
              'resampling':'native QA first; average with >=0.999 valid fraction; categorical nearest; uncertainty max/cloud distance min',
              'record':report}
    if ml:
        manifest['mask_encoding']['pixel_status.tif']['2']='ML estimated, not observed'
        manifest['mask_encoding']['exclusion_mask.tif']['3']='target observed or ML estimated'
        manifest['donor_index']={'2':scenes[1]['id']};manifest.pop('source_index')
        manifest['model']=validation
    method=METHODS[payload['method_id']]
    return {'status':'succeeded','result':artifact_store.safe_value(report,include_maps=True),
            'artifact':artifact_store.publish(identifier,files,manifest,method['artifacts'],method['artifact_specs'])}
