'use client';
import {useEffect,useRef,useState} from 'react';
import {post} from '@/lib/api';
import {useWorkSession} from '@/lib/workSession';
import {sceneKey} from '@/lib/types';
import type {EstimateJob,EstimatePlan,Scene,SearchResponse,WorkflowInterpretation} from '@/lib/types';

const metric=(value:number|null|undefined,unit='')=>value==null?'미확인':`${value.toLocaleString('ko-KR',{maximumFractionDigits:4})}${unit}`;
const running=(job:EstimateJob|null)=>job?.status==='queued'||job?.status==='running';
function BandErrors({title,values}:{title:string;values:Record<string,number>|null|undefined}){
  return <div><dt>{title}</dt><dd>{values&&Object.keys(values).length?Object.entries(values).map(([band,value])=>`${band} ${metric(value)}`).join(' · '):'미확인'}</dd></div>;
}

export default function EstimatedImage({data,target,candidates,parsed,onEstimate,recoveryReady,recoveryKey}:{
  data:SearchResponse|null;target:Scene|null;candidates:Scene[];parsed:WorkflowInterpretation|null;
  onEstimate:(result:EstimatePlan|null)=>void;recoveryReady:boolean;recoveryKey:string;
}){
  const session=useWorkSession();
  const [plan,setPlan]=useState<EstimatePlan|null>(null),[job,setJob]=useState<EstimateJob|null>(null);
  const [busy,setBusy]=useState(false),[confirmed,setConfirmed]=useState(false),[error,setError]=useState('');
  const version=useRef(0),request=useRef<AbortController|null>(null),runningJob=useRef<string|null>(null);
  const context=JSON.stringify({query:data?.query,target:target&&sceneKey(target),candidateKeys:candidates.map(sceneKey),
    purpose:parsed?.purpose_type,temporal:parsed?.effective_temporal_mode,questions:parsed?.questions,recoveryReady,recoveryKey});
  useEffect(()=>{
    version.current++;request.current?.abort();
    if(runningJob.current){void post(`estimate/jobs/${runningJob.current}/cancel`,{}).catch(()=>{});runningJob.current=null;}
    setPlan(null);setJob(null);setBusy(false);setConfirmed(false);setError('');onEstimate(null);
    return ()=>{version.current++;request.current?.abort();};
  },[context,onEstimate]);
  useEffect(()=>{
    if(!job||!running(job))return;
    let stopped=false;const current=version.current;
    const poll=async()=>{
      try{
        const response=await fetch(`/api/estimate/jobs/${job.job_id}`,{cache:'no-store'});
        if(!response.ok)throw new Error(`추정 작업 조회 실패 (${response.status})`);
        const next=await response.json() as EstimateJob;
        if(!stopped&&current===version.current){
          setJob(next);if(!running(next)){runningJob.current=null;onEstimate(next.status==='succeeded'?next.result:null);}
        }
      }catch(cause){if(!stopped&&current===version.current)setError(cause instanceof Error?cause.message:'추정 작업 상태 확인 실패');}
    };
    const timer=setInterval(()=>void poll(),1000);void poll();
    return ()=>{stopped=true;clearInterval(timer);};
  },[job?.job_id,job?.status,onEstimate]);
  const recordJob=session?.recordJob;
  useEffect(()=>{if(job)recordJob?.('estimate',job);},[job,recordJob]);
  const eligible=(!session||session.canProcess(candidates,['red','nir','green','scl']))&&recoveryReady&&!!data&&!!target&&target.collection==='sentinel-2-l2a'&&
    parsed?.purpose_type==='vegetation'&&parsed.effective_temporal_mode==='single'&&!parsed.questions.length&&
    candidates.length>=2&&candidates.every(s=>s.collection==='sentinel-2-l2a'&&
      s.platform===target.platform&&s.processing_level===target.processing_level&&s.datetime&&target.datetime&&Math.abs(Date.parse(s.datetime)-Date.parse(target.datetime))<=14*86400000);

  async function inspect(){
    if(!eligible||!data||!target)return;
    const current=++version.current;request.current?.abort();const controller=new AbortController();request.current=controller;
    setPlan(null);setJob(null);setConfirmed(false);setError('');setBusy(true);onEstimate(null);
    try{
      const result=await post<EstimatePlan>('estimate/plan',{
        purpose_type:'vegetation',temporal_mode:'single',bbox:data.query.bbox,
        start_date:data.query.start_date,end_date:data.query.end_date,
        scene_refs:candidates.map(s=>({collection:s.collection,id:s.id})),
        target_scene:{collection:target.collection,id:target.id},allow_date_change:false,
      },controller.signal);
      if(current===version.current)setPlan(result);
    }catch(cause){if(current===version.current)setError(cause instanceof Error?cause.message:'추정 계획·실제 자료 검사 실패');}
    finally{if(current===version.current)setBusy(false);}
  }
  async function execute(){
    if(!confirmed||!plan?.plan_id||!plan.confirmation_digest||busy||job)return;
    const current=version.current;setBusy(true);
    try{
      const result=await post<EstimateJob>('estimate/jobs',{plan_id:plan.plan_id,confirmation_digest:plan.confirmation_digest});
      if(current!==version.current){void post(`estimate/jobs/${result.job_id}/cancel`,{}).catch(()=>{});return;}
      setJob(result);runningJob.current=result.job_id;setError('');
    }catch(cause){if(current===version.current)setError(cause instanceof Error?cause.message:'추정 작업 시작 실패');}
    finally{if(current===version.current)setBusy(false);}
  }
  async function cancel(){
    if(!job||!running(job))return;
    const current=version.current;
    try{const result=await post<EstimateJob>(`estimate/jobs/${job.job_id}/cancel`,{});if(current===version.current){setJob(result);runningJob.current=null;onEstimate(null);}}
    catch(cause){if(current===version.current)setError(cause instanceof Error?cause.message:'추정 작업 취소 실패');}
  }
  const result=job?.status==='succeeded'&&job.result?job.result:plan;
  const estimateArea=result?.areas;
  return <section className="estimate-mode" aria-label="ML 추정영상 모드">
    <div className="eyebrow">OPTIONAL · ESTIMATED PIXELS</div><h3>ML 추정영상 모드</h3>
    <p>선택 장면의 구름·그림자·NoData 때문에 보이지 않는 곳을 다른 날짜의 실제 관측으로 학습해 <strong>추정</strong>합니다. 구름을 지워 그날의 실제 관측을 되찾은 영상이 아닙니다. 원관측 픽셀, 추정 픽셀, 끝까지 알 수 없는 픽셀을 별도로 표시합니다.</p>
    <p className="asset-help">대상: 현재 검색의 작은 AOI·확정 UTC 기간·선택 장면. 후보 날짜는 위 합성 후보 선택과 공유합니다. 허용 기간 밖 영상이나 다른 센서·제품을 자동으로 추가하지 않습니다.</p>
    {!eligible&&<p className="warning">현재 시범 추정은 식생 한 시점, 동일 플랫폼·제품의 Sentinel-2 L2A 후보 2장 이상만 계획할 수 있습니다. 사건 전후 비교·홍수 당일 복원·열환경/SAR 광학 변환은 미지원입니다.</p>}
    <div className="workflow-actions"><button type="button" disabled={!eligible||busy||running(job)} onClick={()=>void inspect()}>{busy?'원본·검증용 픽셀 검사 중…':'ML 추정 계획·검증 실행'}</button></div>
    {error&&<p role="alert">{error}</p>}
    {plan&&<div className="estimate-plan" data-testid="estimate-plan">
      <strong>{plan.status==='planned'?'실행 전 확인 필요':plan.status==='blocked'?'현재 조건에서 추정 불가':'검사 실패·미확인'}</strong>
      {plan.error&&<p className="warning">{plan.error}</p>}
      {plan.method&&<><h4>어떻게 추정하나요?</h4><p><b>{plan.method.name}</b> · 규칙/모델 버전 {plan.method.version}</p>
        <p>{plan.method.description}</p><dl className="estimate-evidence"><div><dt>학습 자료</dt><dd>{plan.method.training}</dd></div>
          <div><dt>검증 방식</dt><dd>{plan.method.validation}</dd></div></dl>
        {plan.method.limitations?.map(limit=><p className="asset-help" key={limit}>한계: {limit}</p>)}</>}
      {plan.target_date&&<p>추정 대상 장면 날짜: {plan.target_date}</p>}
      {plan.source_dates&&<p>모델에 사용된 참조 관측일: {plan.source_dates.join(' · ')||'미확인'}. 참조일 영상은 추정 근거이며 대상 장면의 실제 촬영일로 바뀌지 않습니다.</p>}
      {plan.validation&&<><h4>현재 AOI의 보류 픽셀 검증</h4><p>{plan.validation.note}</p>
        <dl className="estimate-evidence"><div><dt>학습 픽셀</dt><dd>{metric(plan.validation.train_pixels)}</dd></div>
          <div><dt>따로 보류한 검증 픽셀</dt><dd>{metric(plan.validation.holdout_pixels)}</dd></div>
          <BandErrors title="밴드별 RMSE" values={plan.validation.rmse_by_band}/>
          <BandErrors title="기준선 RMSE" values={plan.validation.baseline_rmse_by_band}/>
          <BandErrors title="밴드별 MAE" values={plan.validation.mae_by_band}/>
          <BandErrors title="오차 90백분위" values={plan.validation.error_q90_by_band}/></dl>
        <p className="asset-help">밴드 오차 단위는 보정된 표면반사도입니다. 보류 픽셀 오차는 그 지역에서 관측된 맑은 픽셀의 시험값입니다. 실제 두꺼운 구름 아래 같은 시점의 참값 정확도가 아닙니다. 분모와 표본 분리는 처리 기록을 확인하세요.</p></>}
      {estimateArea&&<dl className="estimate-evidence"><div><dt>AOI 전체</dt><dd>{metric(estimateArea.aoi_m2,' m²')}</dd></div>
        <div><dt>원관측 유효</dt><dd>{metric(estimateArea.observed_m2,' m²')}</dd></div>
        <div><dt>{job?.status==='succeeded'?'추정 완료':'추정 대상 계획'}</dt><dd>{metric(estimateArea.estimated_m2,' m²')}</dd></div>
        <div><dt>남은 결측</dt><dd>{metric(estimateArea.remaining_gap_m2,' m²')}</dd></div></dl>}
      {plan.grid&&<p>공통 출력 격자 {plan.grid.resolution_m} m · {plan.grid.width}×{plan.grid.height}. 업샘플링을 원래 관측 해상도 향상으로 해석하지 않습니다.</p>}
      {plan.status==='planned'&&plan.can_execute&&<><label className="workflow-check"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>원관측과 ML 추정의 차이, 검증 한계, 대상 AOI·기간·후보 날짜를 확인했습니다.</label>
        <button type="button" disabled={!confirmed||!!job||busy} onClick={()=>void execute()}>확인한 계획으로 추정영상 생성</button></>}
    </div>}
    {job&&<div className="estimate-job" data-testid="estimate-job" role="status"><strong>추정 작업 {job.status}</strong> · {job.stage}
      {job.error&&<p>{job.error}</p>}{running(job)&&<button type="button" onClick={()=>void cancel()}>추정 작업 취소</button>}
      {job.status==='succeeded'&&job.result&&<><p>원관측·추정·미해결 픽셀을 구분한 산출물이 생성됐습니다. 지도에서 실제 관측과 추정 거짓색 레이어를 별도로 켜고 끌 수 있습니다. 합쳐진 GeoTIFF도 <strong>한 날짜의 실측 영상이 아닙니다.</strong></p>
        <p className="asset-help">ZIP: target_observed.tif(실측), estimated_only.tif(ML만), estimate_with_observed.tif(혼합), pixel_status.tif(0 미해결·1 실측·2 추정), donor_index/date.tif, manifest.json. 혼합 파일은 반드시 상태 마스크와 함께 사용하세요.</p>
        <a className="download-link" href={`/api/estimate/jobs/${job.job_id}/download`} download={job.result.artifact_name||'estimated-image.zip'}>추정 GeoTIFF·상태 마스크·검증·방법 기록 ZIP 저장</a></>}
    </div>}
  </section>;
}
