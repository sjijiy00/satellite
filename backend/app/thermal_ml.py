"""Bounded local ridge prediction with buffered spatial holdout validation.

Validation is on clear observations, never a claim about opaque-cloud truth.
No pretrained weights, paid API, or synthesized fixture fallback.
"""
import hashlib
import json
import numpy as np
from .processing_failure import ProcessingBlocked

VERSION = 'thermal-local-ridge-2026-11-06.1'
POLICY = dict(alpha=1., spatial_folds=4, buffer_m=120, sampling_spacing_m=120,
              minimum_train=40, minimum_holdout=12, minimum_pairs=80,
              maximum_rmse_k=2., maximum_mae_k=1.5, maximum_p95_k=4.,
              minimum_copy_improvement=.10, minimum_bias_improvement=.05,
              maximum_training_distance_m=2000)


def blocked(code, message, evidence):
    raise ProcessingBlocked(message, {'code':code, 'ml_validation':evidence})


def design(donor):
    yy, xx = np.indices(donor.shape)
    x = xx / max(1, donor.shape[1]-1)*2-1
    y = yy / max(1, donor.shape[0]-1)*2-1
    # Centering constants/variances are learned only on each training fold.
    t = donor-273.15
    return np.stack([t, x, y, t*x, t*y], axis=-1)


def fit(x, y):
    center=x.mean(axis=0); scale=x.std(axis=0); scale=np.where(scale<1e-8,1,scale)
    z=(x-center)/scale; intercept=float(y.mean())
    coef=np.linalg.solve(z.T@z+np.eye(z.shape[1])*POLICY['alpha'],z.T@(y-intercept))
    return dict(center=center.tolist(),scale=scale.tolist(),coef=coef.tolist(),intercept=intercept)


def predict(model, x):
    return ((x-np.array(model['center']))/np.array(model['scale']))@np.array(model['coef'])+model['intercept']


def metrics(pred, truth):
    e=np.abs(pred-truth)
    return dict(rmse_k=float(np.sqrt(np.mean(e**2))),mae_k=float(e.mean()),p95_k=float(np.percentile(e,95)),count=int(e.size))


def estimate(target, donor, target_valid, donor_valid, clouds, inside, resolution=30):
    evidence={'version':VERSION,'policy':POLICY,'validation_scope':'clear pixels; four buffered spatial holdouts; not cloud-underlying truth',
              'status':'blocked','folds':[],'cloud_truth_accuracy_verified':False}
    original=inside&target_valid&np.isfinite(target)
    gap=inside&~original&clouds
    if not gap.any():blocked('ml_no_cloud_gap','ML 추정할 구름 결측이 없습니다. 불확실성 단독 탈락·일반 NoData는 구름으로 간주하지 않습니다.',evidence)
    pairs=original&donor_valid&np.isfinite(donor)
    candidate=gap&donor_valid&np.isfinite(donor)
    if not candidate.any():blocked('ml_no_donor','구름 결측 위치에 유효한 참조 관측이 없습니다. 다른 참조 영상을 선택하세요.',evidence)
    yy,xx=np.indices(target.shape);step=max(1,int(np.ceil(POLICY['sampling_spacing_m']/resolution)))
    sampled=pairs&(yy%step==0)&(xx%step==0)
    evidence.update(paired_cells=int(pairs.sum()),sampled_pairs=int(sampled.sum()),sampling_step_cells=step)
    if sampled.sum()<POLICY['minimum_pairs']:blocked('ml_insufficient_training','맑은 공통 관측의 학습 표본이 부족합니다. 최소 80개 공간 간격 표본이 필요합니다.',evidence)
    features=design(donor);h,w=target.shape;midy=h//2;midx=w//2;buffer=int(np.ceil(POLICY['buffer_m']/resolution))
    folds=(yy>=midy).astype('uint8')*2+(xx>=midx)
    predictions=[];truths=[];copies=[];biases=[]
    for fold in range(4):
        test=sampled&(folds==fold)
        y0,y1=(0,midy) if fold<2 else (midy,h)
        x0,x1=(0,midx) if fold%2==0 else (midx,w)
        excluded=(yy>=y0-buffer)&(yy<y1+buffer)&(xx>=x0-buffer)&(xx<x1+buffer)
        train=sampled&~excluded
        row={'fold':fold,'train_count':int(train.sum()),'holdout_count':int(test.sum())}
        evidence['folds'].append(row)
        if train.sum()<POLICY['minimum_train'] or test.sum()<POLICY['minimum_holdout']:
            blocked('ml_insufficient_spatial_support','공간을 나눠 검증할 맑은 표본이 부족합니다. 구름 아래 정확도를 추정하지 않습니다.',evidence)
        model=fit(features[train],target[train]);pred=predict(model,features[test]);truth=target[test]
        copy=donor[test];bias=copy+np.median(target[train]-donor[train])
        row.update(model=metrics(pred,truth),copy=metrics(copy,truth),bias_corrected_copy=metrics(bias,truth))
        predictions.extend(pred);truths.extend(truth);copies.extend(copy);biases.extend(bias)
    truth=np.array(truths)
    model_score=metrics(np.array(predictions),truth);copy_score=metrics(np.array(copies),truth);bias_score=metrics(np.array(biases),truth)
    evidence.update(model=model_score,copy=copy_score,bias_corrected_copy=bias_score)
    def accurate(m):return m['rmse_k']<=POLICY['maximum_rmse_k'] and m['mae_k']<=POLICY['maximum_mae_k'] and m['p95_k']<=POLICY['maximum_p95_k']
    improvement=model_score['rmse_k'] < copy_score['rmse_k']*(1-POLICY['minimum_copy_improvement']) and model_score['rmse_k'] < bias_score['rmse_k']*(1-POLICY['minimum_bias_improvement'])
    if not improvement or not accurate(model_score) or not all(accurate(r['model']) for r in evidence['folds']):
        blocked('ml_validation_failed','ML 검증 기준을 통과하지 못해 추정 파일을 만들지 않았습니다. 오차 또는 단순 보충 대비 개선이 부족합니다.',evidence)
    model=fit(features[sampled],target[sampled]);out=np.full(target.shape,np.nan)
    # No extrapolation beyond donor/target training ranges; local clear support.
    lo,hi=float(donor[sampled].min()),float(donor[sampled].max())
    candidate&=(donor>=lo)&(donor<=hi)
    positions=np.argwhere(candidate);train_positions=np.argwhere(sampled)
    # Bound memory even for the maximum grid; nearest clear representative.
    supported=np.zeros(target.shape,dtype=bool)
    limit=(POLICY['maximum_training_distance_m']/resolution)**2
    for start in range(0,len(positions),128):
        points=positions[start:start+128];distance=np.full(len(points),np.inf)
        for j in range(0,len(train_positions),1024):
            diff=points[:,None,:]-train_positions[None,j:j+1024,:]
            distance=np.minimum(distance,np.sum(diff*diff,axis=2).min(axis=1))
        ok=points[distance<=limit];supported[ok[:,0],ok[:,1]]=True
    out[supported]=predict(model,features[supported])
    supported&=np.isfinite(out)&(out>=target[sampled].min())&(out<=target[sampled].max())
    if not supported.any():blocked('ml_outside_training_support','구름 결측이 학습 범위·주변 관측 지지 범위를 벗어나 추정을 보류합니다.',evidence)
    status=np.where(original,1,np.where(supported,2,0)).astype('uint8')
    values=np.where(original,target,np.where(supported,out,np.nan))
    evidence.update(status='passed',fitted_model=model,features=['donor_celsius','x','y','donor_celsius*x','donor_celsius*y'],
                    training_donor_range_k=[lo,hi],estimated_cells=int(supported.sum()))
    evidence['model_sha256']=hashlib.sha256(json.dumps(model,sort_keys=True).encode()).hexdigest()
    return values,status,evidence
