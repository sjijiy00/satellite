"""Bounded, locally supervised Sentinel-2 target-date reflectance estimate.

This predicts masked target pixels; it never treats predictions as observations.
"""
import base64
from datetime import date,datetime,timezone
import hashlib
import io
import json
import math
import zipfile

import numpy as np
from rasterio.io import MemoryFile

from .change_analysis import calibration_for_change
from .cloud_composite import BANDS,FLOAT_NODATA,DATE_NODATA,EPOCH,_tiff
from .pixel_policy import LIMITS,POLICY,QualityError
from .pixel_raster import make_grid,grid_info,area_weights,project_footprint,diagnose_scene,map_preview
from .range_reader import public_cog

VERSION='s2-local-ridge-estimate-2026-10-29.1'
OPERATING={'maximum_day_gap':14,'minimum_pairs':400,'minimum_pairs_per_quadrant':40,
           'minimum_train_per_fold':200,'ridge_alpha':1.0,'minimum_mae_improvement':0.05,
           'maximum_band_mae_ratio':1.05,'feature_range_margin':0.05,'target_range_margin':0.10}
DESCRIPTION='목표일과 참조일에 모두 맑은 AOI 픽셀의 적색·근적외선·녹색 반사도 쌍으로 국소 ridge 회귀를 학습해 목표일 가림 영역만 추정'
LIMITATIONS=[
    '추정값은 목표 날짜의 실제 광학 관측이 아닙니다. 불투명 구름 아래 같은 날의 참값은 직접 검증하지 못했습니다.',
    '맑은 학습 픽셀과 가려진 픽셀은 토지피복·생육·홍수 상태가 다를 수 있습니다. 공간 블록 검증도 이를 보증하지 않습니다.',
    '참조일과 목표일의 실제 변화·그림자 오분류·대기보정·정합 오차가 결과에 섞일 수 있습니다.',
    '검증 오차 분위수는 맑은 보류 픽셀에서의 경험값이며 가려진 픽셀의 보증 구간이 아닙니다.',
    '식생 한 시점 소형 AOI만 지원합니다. 홍수·산불·전후 변화·열환경·SAR 복원에는 사용하지 않습니다.']


def _fit(x,y):
    """Deterministic standardized multi-output ridge with an unpenalized intercept."""
    mean_x=x.mean(axis=0);std_x=np.maximum(x.std(axis=0),1e-6)
    mean_y=y.mean(axis=0);std_y=np.maximum(y.std(axis=0),1e-6)
    zx=(x-mean_x)/std_x;zy=(y-mean_y)/std_y
    coef=np.linalg.solve(zx.T@zx+OPERATING['ridge_alpha']*np.eye(len(BANDS)),zx.T@zy)
    return {'x_mean':mean_x,'x_std':std_x,'y_mean':mean_y,'y_std':std_y,'coef':coef,
            'x_min':x.min(axis=0),'x_max':x.max(axis=0),'y_min':y.min(axis=0),'y_max':y.max(axis=0)}


def _predict(model,x):
    return (((x-model['x_mean'])/model['x_std'])@model['coef'])*model['y_std']+model['y_mean']


def _ndvi(values):
    denominator=values[:,1]+values[:,0]
    result=np.full(len(values),np.nan,dtype='float64')
    valid=np.isfinite(denominator)&(denominator>1e-6)
    result[valid]=(values[valid,1]-values[valid,0])/denominator[valid]
    return result


def _metric(actual,pred):
    delta=np.abs(actual-pred)
    return ({key:float(np.mean(delta[:,i])) for i,key in enumerate(BANDS)},
            {key:float(np.sqrt(np.mean((actual[:,i]-pred[:,i])**2))) for i,key in enumerate(BANDS)},
            {key:float(np.quantile(delta[:,i],.90)) for i,key in enumerate(BANDS)})


def _validation(x,y,rows,cols,shape):
    count=len(x)
    if count<OPERATING['minimum_pairs']:
        return {'status':'insufficient','train_pixels':count,'holdout_pixels':0,'note':'맑은 목표일·참조일 짝픽셀 부족'},None
    quadrant=(rows>=shape[0]//2).astype('int8')*2+(cols>=shape[1]//2).astype('int8')
    predictions=np.empty_like(y)
    for block in range(4):
        test=quadrant==block;train=~test
        if test.sum()<OPERATING['minimum_pairs_per_quadrant'] or train.sum()<OPERATING['minimum_train_per_fold']:
            return {'status':'insufficient','train_pixels':count,'holdout_pixels':0,
                    'note':'연속 공간 사분면 4개를 각각 보류할 충분한 짝픽셀이 없습니다.'},None
        predictions[test]=_predict(_fit(x[train],y[train]),x[test])
    mae,rmse,q90=_metric(y,predictions)
    baseline_mae,baseline_rmse,_=_metric(y,x)
    ntruth=_ndvi(y);npred=_ndvi(predictions);nbase=_ndvi(x)
    ndvi_valid=np.isfinite(ntruth)&np.isfinite(npred)&np.isfinite(nbase)
    ndvi_mae=float(np.mean(np.abs(ntruth[ndvi_valid]-npred[ndvi_valid]))) if ndvi_valid.any() else None
    baseline_ndvi_mae=float(np.mean(np.abs(ntruth[ndvi_valid]-nbase[ndvi_valid]))) if ndvi_valid.any() else None
    total_mae=float(np.mean(list(mae.values())));total_baseline=float(np.mean(list(baseline_mae.values())))
    passed=(total_baseline>0 and total_mae<=total_baseline*(1-OPERATING['minimum_mae_improvement'])
            and all(mae[key]<=baseline_mae[key]*OPERATING['maximum_band_mae_ratio'] for key in BANDS)
            and ndvi_mae is not None and baseline_ndvi_mae is not None and ndvi_mae<=baseline_ndvi_mae)
    report={'status':'passed' if passed else 'below_baseline','train_pixels':count,'holdout_pixels':count,
            'mae_by_band':mae,'rmse_by_band':rmse,'error_q90_by_band':q90,
            'baseline_mae_by_band':baseline_mae,'baseline_rmse_by_band':baseline_rmse,
            'ndvi_mae':ndvi_mae,'baseline_ndvi_mae':baseline_ndvi_mae,
            'note':'2×2 연속 공간 사분면을 하나씩 보류한 4-fold 검증. 원관측 참조일 반사도 그대로 복사 기준선과 비교. 맑은 영역 오차이며 구름 아래 보증 아님.'}
    return report,_fit(x,y) if passed else None


def _flatten(bands,mask):
    return np.stack([bands[key][mask] for key in BANDS],axis=1).astype('float64')


def _model_json(model):
    return {key:value.tolist() for key,value in model.items()}


def _false_color(values,mask,grid,label,source,scene_id):
    if not mask.any():return None
    # Display-only NIR/red/green false color; this is not a reflectance export.
    channels=np.stack((values[1],values[0],values[2]),axis=-1)
    stretched=np.power(np.clip(channels/0.35,0,1),1/1.4)
    rgba=np.zeros((*mask.shape,4),dtype='uint8')
    rgba[mask,:3]=(stretched[mask]*255).astype('uint8')
    rgba[mask,3]=190
    preview=map_preview(rgba,grid,label,[scene_id])
    preview['source']=source
    return preview


def process_estimate(payload,opener=None):
    scenes=payload['scenes']
    if not 2<=len(scenes)<=4:raise QualityError('추정에는 목표 영상과 참조 영상 1~3개가 필요합니다.')
    if payload['purpose']!='vegetation' or payload['temporal_mode']!='single':
        raise QualityError('첫 추정 모드는 식생 한 시점에만 허용합니다. 사건/전후 영상을 혼합하지 않습니다.')
    if len({(s['collection'],s['id']) for s in scenes})!=len(scenes):raise QualityError('중복 Item 사용 불가')
    if any(s['collection']!='sentinel-2-l2a' for s in scenes):raise QualityError('Sentinel-2 L2A만 지원합니다.')
    target=next((s for s in scenes if s['id']==payload['target_id']),None)
    if target is None:raise QualityError('목표 영상이 후보에 없습니다.')
    if len({(s['platform'],s['processing_baseline']) for s in scenes})!=1 or not target['platform'] or not target['processing_baseline']:
        raise QualityError('같은 위성 플랫폼·처리 기준선의 제품만 사용합니다.')
    start=date.fromisoformat(payload['start_date']);end=date.fromisoformat(payload['end_date'])
    if (end-start).days>31:raise QualityError('허용 기간은 최대 31일입니다.')
    target_day=date.fromisoformat(target['datetime'][:10])
    donors=[]
    for scene in scenes:
        acquired=date.fromisoformat(scene['datetime'][:10])
        if not start<=acquired<=end:raise QualityError('허용 기간 밖 영상 사용 불가')
        if any(key not in scene['assets'] or not calibration_for_change(scene['assets'][key],scene) for key in BANDS):
            raise QualityError('반사도 scale/offset 또는 제품 보정 근거 누락/상충')
        if scene is not target:
            gap=abs((acquired-target_day).days)
            if gap==0 or gap>OPERATING['maximum_day_gap']:
                raise QualityError('참조 영상은 목표와 다른 날짜이며 최대 14일 차이여야 합니다. 이는 운영 상한이지 동일 상태 보장은 아닙니다.')
            donors.append(scene)
    donors.sort(key=lambda s:(abs((date.fromisoformat(s['datetime'][:10])-target_day).days),s['datetime'],s['collection'],s['id']))
    ordered=[target,*donors]
    grid=make_grid(payload['bbox']);aoi=area_weights(grid['aoi'],grid);total=float(aoi.sum())
    shape=(grid['height'],grid['width']);results=[];masks=[];values=[];weights=[]
    for scene in ordered:
        footprint=area_weights(project_footprint(scene['geometry'],grid),grid)
        band_values={};result,mask=diagnose_scene(scene,grid,footprint,footprint,opener,bands_out=band_values)
        result.update(id=scene['id'],datetime=scene['datetime'])
        results.append(result);masks.append(mask);values.append(band_values);weights.append(footprint)
    if any(result['status']!='checked' for result in results):
        return {'status':'blocked','error':'목표 또는 참조 영상의 실제 SCL/밴드 자료를 검사하지 못했습니다. 추정 정확도는 미확인입니다.',
                'can_execute':False,'scenes':results,'version':VERSION}
    target_mask=masks[0]&(aoi>0)&(weights[0]>0)
    if not target_mask.any():
        return {'status':'blocked','error':'목표 날짜의 맑은 학습 픽셀이 없어 지도학습 정답을 만들 수 없습니다.',
                'can_execute':False,'scenes':results,'version':VERSION}
    target_values=values[0]
    source=np.zeros(shape,dtype='uint16');predicted=np.full((3,*shape),np.nan,dtype='float32')
    donor_reports=[];accepted=[]
    rows,cols=np.indices(shape)
    for index,scene in enumerate(donors,1):
        donor_mask=masks[index]&(aoi>0)&(weights[0]>0)
        paired=target_mask&donor_mask
        paired&=np.all(np.stack([np.isfinite(target_values[key])&np.isfinite(values[index][key])&
                                 (target_values[key]>=0)&(values[index][key]>=0) for key in BANDS]),axis=0)
        validation,model=_validation(_flatten(values[index],paired),_flatten(target_values,paired),rows[paired],cols[paired],shape)
        donor={'index':index,'id':scene['id'],'datetime':scene['datetime'],'gap_days':(date.fromisoformat(scene['datetime'][:10])-target_day).days,
               'validation':validation,'used_pixels':0}
        donor_reports.append(donor)
        if model is None:continue
        accepted.append((index,scene,model,validation))
        candidate=(~target_mask)&donor_mask&(source==0)
        if not candidate.any():continue
        x=_flatten(values[index],candidate)
        span=np.maximum(model['x_max']-model['x_min'],1e-6)
        in_range=np.all((x>=model['x_min']-OPERATING['feature_range_margin']*span)&
                        (x<=model['x_max']+OPERATING['feature_range_margin']*span),axis=1)
        y=_predict(model,x)
        yspan=np.maximum(model['y_max']-model['y_min'],1e-6)
        plausible=np.all(np.isfinite(y)&(y>=np.maximum(0,model['y_min']-OPERATING['target_range_margin']*yspan))&
                         (y<=model['y_max']+OPERATING['target_range_margin']*yspan),axis=1)
        select=in_range&plausible
        rr=rows[candidate][select];cc=cols[candidate][select]
        source[rr,cc]=index
        predicted[:,rr,cc]=y[select].T.astype('float32')
        donor['used_pixels']=int(select.sum())
    estimated=source>0
    original_area=float(aoi[target_mask].sum());estimated_area=float(aoi[estimated].sum())
    base={'version':VERSION,'checked_at':datetime.now(timezone.utc).isoformat(),
          'method':{'name':'AOI 국소 지도학습 ridge 회귀','version':VERSION,'description':DESCRIPTION,
                    'inputs':'참조일 적색·근적외선·녹색 표면반사도 3밴드',
                    'training':'목표일과 참조일에 모두 SCL/NoData 유효한 동일 20 m 격자 픽셀을 정답 쌍으로 사용',
                    'validation':'연속 공간 2×2 사분면 4-fold 보류, 참조일 밴드를 그대로 복사한 기준선과 비교',
                    'limitations':LIMITATIONS},
          'operating_gates':OPERATING,'grid':grid_info(grid),'policy':POLICY,
          'period':{'start':str(start),'end':str(end),'timezone':'UTC'},
          'target_id':target['id'],'target_date':str(target_day),
          'source_dates':[scene['datetime'][:10] for i,scene,_,_ in accepted if donor_reports[i-1]['used_pixels']>0],
          'areas':{'aoi_m2':total,'observed_m2':original_area,'estimated_m2':estimated_area,
                   'remaining_gap_m2':max(0,total-original_area-estimated_area)},
          'donors':donor_reports,'scenes':results,'limits':{**LIMITS,'candidate_scenes':4,'period_days':31,'artifact_zip_bytes':4_000_000},
          'models_fingerprint':hashlib.sha256(json.dumps([{'index':i,'model':_model_json(model)} for i,_,model,_ in accepted],
                                                  sort_keys=True,allow_nan=False).encode()).hexdigest(),
          'validation':_summary([validation for _,_,_,validation in accepted]),
          'artifact_base64':None,'map_layers':{'observed':None,'estimated':None}}
    if not accepted or estimated_area<=0:
        base.update(status='blocked',can_execute=False,
                    error='맑은 학습/공간 검증과 단순 원관측 복사 대비 개선 조건을 충족한 추정 대상이 없습니다. 결측을 유지합니다.')
        return base
    base.update(status='planned' if payload['analysis_mode']=='estimate_plan' else 'succeeded',can_execute=True,error=None)
    if payload['analysis_mode']=='estimate_plan':return base
    observed_data=np.full((3,*shape),FLOAT_NODATA,dtype='float32')
    estimate_data=np.full((3,*shape),FLOAT_NODATA,dtype='float32')
    combined=np.full((3,*shape),FLOAT_NODATA,dtype='float32')
    for channel,key in enumerate(BANDS):
        observed_data[channel,target_mask]=target_values[key][target_mask]
        estimate_data[channel,estimated]=predicted[channel,estimated]
        combined[channel,target_mask]=observed_data[channel,target_mask]
        combined[channel,estimated]=estimate_data[channel,estimated]
    status=np.zeros(shape,dtype='uint8');status[target_mask]=1;status[estimated]=2
    dates=np.full(shape,DATE_NODATA,dtype='int32')
    for index,scene in enumerate(donors,1):
        dates[source==index]=(date.fromisoformat(scene['datetime'][:10])-EPOCH).days
    tag='target observed values remain unchanged; estimated values are model predictions, not measurements; inspect pixel_status'
    files={
        'target_observed.tif':_tiff(observed_data,grid,'float32',FLOAT_NODATA,BANDS,version=VERSION,interpretation='actual target-date observation only'),
        'estimated_only.tif':_tiff(estimate_data,grid,'float32',FLOAT_NODATA,BANDS,version=VERSION,interpretation='ML estimate only; not observed'),
        'estimate_with_observed.tif':_tiff(combined,grid,'float32',FLOAT_NODATA,BANDS,version=VERSION,interpretation=tag),
        'pixel_status.tif':_tiff([status],grid,'uint8',0,('0_unresolved_1_observed_2_estimated',),version=VERSION,interpretation=tag),
        'donor_index.tif':_tiff([source],grid,'uint16',0,('1_based_donor_index_estimates_only',),version=VERSION,interpretation=tag),
        'donor_date.tif':_tiff([dates],grid,'int32',DATE_NODATA,('UTC_days_since_1970_01_01_estimates_only',),version=VERSION,interpretation=tag)}
    manifest={key:value for key,value in base.items() if key not in ('artifact_base64','map_layers')}
    manifest.update(artifact_type='local_supervised_estimate',band_order=list(BANDS),
                    pixel_status_encoding={'0':'미해결/영역 밖','1':'목표일 실제 관측','2':'다른 날짜 자료로 학습한 모델 추정'},
                    validation_interpretation='맑은 목표일 픽셀의 공간 보류 오차; 구름 아래 정확도/보증 구간 아님',
                    donor_index_mapping=[{'index':i,'collection':s['collection'],'id':s['id'],'datetime':s['datetime'],
                                          'model':_model_json(model),'validation':validation}
                                         for i,s,model,validation in accepted],
                    source_date_encoding='int32 UTC days since 1970-01-01; NoData -2147483648',
                    sources=[{'collection':s['collection'],'id':s['id'],'datetime':s['datetime'],
                              'assets':{key:{'url':s['assets'][key]['url'] if public_cog(s['assets'][key]['url']) else None,
                                              'url_note':'공개 허용 URL만 기록; 인증/서명 URL은 기록하지 않음',
                                              'scale':s['assets'][key]['scale'],
                                              'offset':s['assets'][key]['offset'],'nodata':s['assets'][key]['nodata']}
                                        for key in (*BANDS,'scl')}} for s in ordered],
                    files={name:{'sha256':hashlib.sha256(content).hexdigest(),'bytes':len(content)} for name,content in files.items()})
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,content in files.items():archive.writestr(name,content)
        archive.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,allow_nan=False,indent=2))
    artifact=buffer.getvalue()
    if len(artifact)>4_000_000:raise QualityError('추정 ZIP 4 MB 초과. AOI를 줄여 주세요.')
    with zipfile.ZipFile(io.BytesIO(artifact)) as archive:
        for name in files:
            with MemoryFile(archive.read(name)) as memory:
                with memory.open() as raster:
                    if raster.crs is None or raster.width!=grid['width'] or raster.height!=grid['height'] or raster.nodata is None:
                        raise QualityError('생성 GeoTIFF 재열기/CRS/NoData 검증 실패')
    base['artifact_base64']=base64.b64encode(artifact).decode('ascii')
    base['artifact_name']='sentinel-2-local-ml-estimate.zip';base['artifact_size_bytes']=len(artifact)
    base['map_layers']={'observed':_false_color(observed_data,target_mask,grid,'목표일 실제 관측 NIR·적색·녹색 거짓색',
                                               '실제 목표일 픽셀의 화면용 거짓색; 원본 반사도는 GeoTIFF',target['id']),
                        'estimated':_false_color(estimate_data,estimated,grid,'모델 추정 픽셀만 NIR·적색·녹색 거짓색',
                                                '목표일 가림 영역의 ML 추정 화면용 거짓색; 실제 관측 아님',target['id'])}
    return base


def _summary(validations):
    if not validations:
        return {'status':'insufficient','train_pixels':0,'holdout_pixels':0,'mae_by_band':None,
                'rmse_by_band':None,'error_q90_by_band':None,'baseline_mae_by_band':None,
                'baseline_rmse_by_band':None,'note':'통과한 참조 날짜 모델이 없습니다.'}
    n=sum(v['holdout_pixels'] for v in validations)
    def mean_dict(key):
        return {band:sum(v[key][band]*v['holdout_pixels'] for v in validations)/n for band in BANDS}
    return {'status':'passed','train_pixels':sum(v['train_pixels'] for v in validations),'holdout_pixels':n,
            'mae_by_band':mean_dict('mae_by_band'),'rmse_by_band':mean_dict('rmse_by_band'),
            'error_q90_by_band':mean_dict('error_q90_by_band'),
            'baseline_mae_by_band':mean_dict('baseline_mae_by_band'),
            'baseline_rmse_by_band':mean_dict('baseline_rmse_by_band'),
            'note':'통과한 참조 모델들의 맑은 공간 보류 오차를 표본 수로 가중 요약. 구름 아래 정확도 아님.'}
