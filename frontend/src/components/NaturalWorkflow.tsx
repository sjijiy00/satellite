'use client';
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {observedGap,qualityState,s2QualitySupported} from '@/lib/workflow';
import {post} from '@/lib/api';
import {sceneKey} from '@/lib/types';
import type {Bbox,CloudJob,CloudPlan,EstimatePlan,PixelReport,Purpose,Scene,SearchResponse,WorkflowInterpretation} from '@/lib/types';
import EstimatedImage from './EstimatedImage';
import {useWorkSession} from '@/lib/workSession';
import Link from 'next/link';

const fmt=(n:number|null|undefined,unit='')=>n==null?'미확인':n.toLocaleString('ko-KR',{maximumFractionDigits:2})+unit;
const active=(job:CloudJob|null)=>job?.status==='queued'||job?.status==='running';

export default function NaturalWorkflow({purpose,purposeType,targetSize,observationNeed,temporalMode,bbox,start,end,selected,data,onSearch,onCompare,onMoveAoi,onEstimate,composing=false,pair,qualityReport,comparisonOpen,onCloseCompare,onSelect,onSingleQuality,children,enabled=true,preprocessingAvailable=true}:{
  enabled?:boolean;preprocessingAvailable?:boolean;purpose:string;purposeType:Purpose;targetSize:string;observationNeed:string;temporalMode:string;
  bbox:Bbox|null;start:string;end:string;selected:string|null;data:SearchResponse|null;onSearch:()=>void;onCompare:(temporal?:boolean)=>void;onMoveAoi:()=>void;
  onEstimate:(result:EstimatePlan|null)=>void;composing?:boolean;pair:[string,string];qualityReport:PixelReport|null;comparisonOpen:boolean;onCloseCompare:()=>void;onSelect:(key:string)=>void;onSingleQuality:(plan:CloudPlan)=>void;children?:ReactNode;
}){
  const session=useWorkSession(),stage=session?.stage||'quality';
  const [followup,setFollowup]=useState('');
  const reference=data?.query.requested_reference_date||'',allowDateChange=false;
  const [qualityOpen,setQualityOpen]=useState(false),[reviewed,setReviewed]=useState(false),[planMode,setPlanMode]=useState<'single'|'composite'|null>(null),[starting,setStarting]=useState(false);
  const [parsed,setParsed]=useState<WorkflowInterpretation|null>(null),[parseError,setParseError]=useState('');
  const [plan,setPlan]=useState<CloudPlan|null>(null),[planError,setPlanError]=useState(''),[planning,setPlanning]=useState(false);
  const [confirmed,setConfirmed]=useState(false),[job,setJob]=useState<CloudJob|null>(null);
  const [candidateIds,setCandidateIds]=useState<string[]|null>((session?.settings.candidates as string[])||null);
  const request=useRef<AbortController|null>(null),version=useRef(0),running=useRef<string|null>(null);
  const scene=data?.items.find(s=>sceneKey(s)===selected)||null;
  const context=JSON.stringify({purpose,purposeType,targetSize,observationNeed,temporalMode,bbox,start,end,selected,
    query:data?.query,ids:data?.items.map(sceneKey),pair,followup,reference,allowDateChange,candidateIds,reviewed});
  const coreContext=JSON.stringify({purpose,purposeType,targetSize,observationNeed,temporalMode,bbox,start,end,selected,pair,query:data?.query});
  useEffect(()=>{setParsed(null);setParseError('');},[coreContext,followup,composing]);
  useEffect(()=>{setQualityOpen(false);setReviewed(false);setPlanMode(null);setFollowup('');},[coreContext]);
  useEffect(()=>{if(qualityState(qualityReport)==='degraded')setQualityOpen(true);},[qualityReport]);
  useEffect(()=>{if(parsed?.intent==='cloud_help'&&parsed.followup_supported!==false)setQualityOpen(true);},[parsed]);
  useEffect(()=>setCandidateIds(null),[selected,data?.query.start_date,data?.query.end_date]);
  useEffect(()=>{
    version.current++;request.current?.abort();
    if(running.current){void post(`cloud/jobs/${running.current}/cancel`,{}).catch(()=>{});running.current=null;}
    setPlan(null);setJob(null);setConfirmed(false);setPlanError('');setPlanning(false);setStarting(false);
    if(!enabled||composing||!data||!scene)return;
    const controller=new AbortController();request.current=controller;
    const timer=setTimeout(()=>{
      void post<WorkflowInterpretation>('request/interpret',{
        purpose,purpose_type:data?.recommendation?.purpose_type||purposeType||null,followup,target_size_m:targetSize?Number(targetSize):null,
        observation_need:observationNeed,temporal_mode:temporalMode,bbox,start_date:start||null,end_date:end||null,
        selected_scene:scene?{collection:scene.collection,id:scene.id,provider_id:scene.provider_id}:null,selected_datetime:scene?.datetime||null,
        reference_date:reference||null,allow_date_change:allowDateChange},controller.signal)
        .then(result=>{if(!controller.signal.aborted){setParsed(result);setParseError('');}})
        .catch(e=>{if(!controller.signal.aborted){setParsed(null);setParseError(e instanceof Error?e.message:'요청 해석 실패');}});
    },350);
    return ()=>{version.current++;clearTimeout(timer);controller.abort();};
  // The complete context is intentional: every confirmed plan is tied to the visible inputs.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  },[context,composing,enabled]);
  useEffect(()=>{
    if(!job||!active(job))return;
    let stopped=false;const current=version.current;
    const poll=async()=>{
      try{
        const response=await fetch(`/api/cloud/jobs/${job.job_id}`,{cache:'no-store'});
        if(!response.ok)throw new Error(`작업 상태 조회 실패 (${response.status})`);
        const next=await response.json() as CloudJob;
        if(!stopped&&current===version.current){setJob(next);if(!active(next))running.current=null;}
      }catch(e){if(!stopped&&current===version.current)setPlanError(e instanceof Error?e.message:'작업 상태 확인 실패');}
    };
    const timer=setInterval(()=>void poll(),1000);void poll();
    return ()=>{stopped=true;clearInterval(timer);};
  },[job?.job_id,job?.status]);
  const recordJob=session?.recordJob;
  useEffect(()=>{if(job)recordJob?.('cloud',job);},[job,recordJob]);
  function eligible():Scene[]{
    if(!scene||!data)return [];
    const targetTime=scene.datetime?Date.parse(scene.datetime):0;
    const others=data.items.filter(s=>s.collection==='sentinel-2-l2a'&&sceneKey(s)!==sceneKey(scene)&&
      s.platform===scene.platform&&s.processing_level===scene.processing_level&&s2QualitySupported(s,data.recommendation?.purpose_type||null)&&s.datetime&&
      s.datetime.slice(0,10)>=data.query.start_date&&s.datetime.slice(0,10)<=data.query.end_date);
    // Whole-scene cloud is only a metadata shortlist; the plan checks real AOI pixels.
    others.sort((a,b)=>(a.scene_cloud_cover??101)-(b.scene_cloud_cover??101)||
      Math.abs(Date.parse(a.datetime!)-targetTime)-Math.abs(Date.parse(b.datetime!)-targetTime)||sceneKey(a).localeCompare(sceneKey(b)));
    return others;
  }
  function candidates(single:boolean):Scene[]{
    if(!scene)return [];
    if(single)return [scene];
    const options=eligible();
    const keys=candidateIds??options.slice(0,3).map(sceneKey);
    return [scene,...options.filter(s=>keys.includes(sceneKey(s))).slice(0,3)];
  }
  async function inspect(single:boolean){
    if(!canPlan||(!single&&!reviewed)||!data||!scene){
      setPlanError('식생 한 시점 목적·확정 AOI/기간·선택 영상을 확인하세요. 전후 사건 날짜는 합성하지 않습니다.');return;
    }
    const list=candidates(single);
    if(session&&!session.canProcess(list,['red','nir','green','scl'])){setPlanError('필수 red/nir/green/scl 밴드와 세부 분석·기간·AOI 조건을 확인하세요. 서버가 canonical Asset의 실제 접근을 검사합니다.');return;}
    const current=++version.current;request.current?.abort();const controller=new AbortController();request.current=controller;
    setPlan(null);setJob(null);setConfirmed(false);setPlanError('');setPlanning(true);setPlanMode(single?'single':'composite');
    try{
      const result=await post<CloudPlan>('cloud/plan',{
        purpose,purpose_type:'vegetation',target_size_m:targetSize?Number(targetSize):null,
        observation_need:observationNeed,temporal_mode:'single',bbox:data.query.bbox,
        start_date:data.query.start_date,end_date:data.query.end_date,
        scene_refs:list.map(s=>({collection:s.collection,id:s.id})),
        target_scene:{collection:scene.collection,id:scene.id},allow_date_change:allowDateChange},controller.signal);
      if(current===version.current){setPlan(result);if(single)onSingleQuality(result);}
    }catch(e){if(current===version.current){const message=e instanceof Error?e.message:'실제 품질 검사 실패';setPlanError(message);if(single)onSingleQuality({status:'failed',error:message});}}
    finally{if(current===version.current)setPlanning(false);}
  }
  async function execute(){
    if(!confirmed||!plan?.plan_id||!plan.confirmation_digest||starting||job||planMode!=='composite'||session&&!session.canProcess(candidates(false),['red','nir','green','scl']))return;
    const current=version.current;setStarting(true);
    try{
      const result=await post<CloudJob>('cloud/jobs',{plan_id:plan.plan_id,confirmation_digest:plan.confirmation_digest});
      if(current!==version.current){void post(`cloud/jobs/${result.job_id}/cancel`,{}).catch(()=>{});return;}
      setJob(result);running.current=result.job_id;setPlanError('');
    }catch(e){if(current===version.current)setPlanError(e instanceof Error?e.message:'작업 시작 실패');}
    finally{if(current===version.current)setStarting(false);}
  }
  async function cancel(){
    if(!job||!active(job))return;
    try{const result=await post<CloudJob>(`cloud/jobs/${job.job_id}/cancel`,{});setJob(result);running.current=null;}
    catch(e){setPlanError(e instanceof Error?e.message:'취소 실패');}
  }
  const currentPurpose=data?.recommendation?.purpose_type||null;
  const canPlan=!!data&&s2QualitySupported(scene,currentPurpose)&&currentPurpose==='vegetation'&&
    parsed?.effective_temporal_mode==='single'&&!parsed.questions.length&&observationNeed!=='all_weather'&&observationNeed!=='night'&&
    ['red','nir','green','scl'].every(key=>scene?.download_assets?.some(asset=>asset.key===key));
  const selectedQA=plan?.scenes?.find(s=>s.id===scene?.id);
  const finished=job?.status==='succeeded'?job.result:null;
  const evidence=finished||plan;
  const estimateReady=!!canPlan&&!starting&&!active(job)&&reviewed&&planMode==='composite'&&observedGap(evidence)&&candidates(false).length>=2;
  const measuredProblem=planMode==='single'&&selectedQA?.status==='checked'&&selectedQA.valid_percent_aoi!=null&&selectedQA.valid_percent_aoi<70&&
    Object.entries(selectedQA.exclusions_m2||{}).some(([key,value])=>['cloud_cirrus','cloud_shadow','nodata','band_nodata_or_mixed_invalid'].includes(key)&&value>0);
  useEffect(()=>{if(measuredProblem)setQualityOpen(true);},[measuredProblem]);
  const showRecovery=(preprocessingAvailable&&stage==='preprocess')||qualityOpen||measuredProblem||qualityState(qualityReport)==='degraded';
  const qaState=planMode==='single'&&(plan||planError)?selectedQA?.status==='checked'?(measuredProblem?'degraded':'good'):'failed':qualityState(qualityReport);
  function requestAction(){
    if(!parsed||parsed.followup_supported===false)return;
    if(parsed.intent==='cloud_help')setQualityOpen(true);
    else if(parsed.intent==='compare')onCompare(true);
    else if(parsed.intent==='move_aoi')onMoveAoi();
    else if(parsed.intent==='search')onSearch();
  }
  if(!enabled||!data)return null;
  if(!scene)return <section className="natural-workflow" aria-label="다음 작업"><h2>다음 작업 · 장면 선택</h2><p>현재 검색 결과에서 장면을 선택하세요. 선택 전에는 품질 검사·합성·추정을 실행하지 않습니다.</p></section>;
  return <section className="natural-workflow" id="next-work" aria-label="다음 작업" data-testid="next-work">
    <div className="eyebrow">SELECTED SCENE → NEXT ACTION</div><h2>② 품질 확인 · 다음 작업</h2>
    <p><strong>{data.recommendation?.label||'추천 메타데이터 미확인'}</strong> · {scene.id} · {data.query.start_date}–{data.query.end_date} UTC</p>
    <p data-testid="next-work-state">{planning?'실제 원본·AOI 검사 중':qaState==='degraded'?'실제 AOI 검사: 구름·그림자·NoData 제외로 운영 기준 미충족':qaState==='good'?'실제 AOI 검사 완료 · 확인한 범위의 결과':qaState==='failed'?'AOI 검사 실패·미확인 · 구름 0% 또는 사용 불가 판정 아님':'AOI 픽셀 미검사 · 장면 전체 구름량으로 사용 불가를 판정하지 않습니다.'}</p>
    <div className="workflow-actions">
      <Link className="download-link" href="/" onClick={()=>session?.requestOriginal()}>원본·밴드·다운로드 확인</Link>
      <button type="button" disabled={data.items.length<2} onClick={()=>onCompare()}>두 장면 비교·분석</button>
      {comparisonOpen&&<button type="button" onClick={onCloseCompare}>비교 작업 접기</button>}
      {!comparisonOpen&&canPlan&&<button type="button" disabled={planning||starting||active(job)||!!session&&!session.canProcess(scene?[scene]:[],['red','nir','green','scl'])} onClick={()=>void inspect(true)}>선택 영상 실제 AOI 품질 검사</button>}
      <button type="button" onClick={()=>setQualityOpen(true)}>구름·그림자·NoData 대응 안내</button>
      <button type="button" onClick={()=>onSelect('')}>장면 선택 해제</button>
    </div>
    {currentPurpose==='flood'&&<p className="warning">홍수: Sentinel-1 GRD 검색 지원 · SAR 픽셀 처리 미지원입니다. 광학 영상은 맑은 시기의 수역 관측 보완이며 SAR와 동등한 장마 관측이 아닙니다. 침수 면적·원인 확정 분석과 합성·ML 추정은 지원하지 않습니다. Sentinel-2 두 날짜의 작은 AOI QA와 메타데이터 비교는 사용할 수 있습니다.</p>}
    {currentPurpose==='thermal'&&<p className="warning">열환경: Landsat L2SP 지표온도 제품의 원본 확인·다운로드와 메타데이터 비교를 사용하세요. 앱 내 온도 분석·픽셀 QA·합성·ML은 미지원입니다. Sentinel-2는 열적외선 지표온도 대안이 아닙니다.</p>}
    {currentPurpose==='urban'&&<p>도시 목적은 원본·밴드 다운로드, 두 장면 비교와 지원되는 Sentinel-2 쌍의 QA까지 제공합니다. 도시 변화 계산·합성·ML은 미지원입니다.</p>}
    {currentPurpose==='vegetation'&&!canPlan&&<p className="asset-help">식생 NDVI 변화는 같은 Sentinel-2 플랫폼 두 날짜의 비교 작업에서 지원합니다. 관측 선택 합성·ML은 식생 한 시점 Sentinel-2 L2A 조건에서만 지원하며 원본 제품·보정·기간·면적은 서버에서 다시 검사합니다.</p>}
    {session&&!session.canProcess([scene])&&<p className="warning">세부 분석·필수 밴드·기간·AOI 조건 확인이 필요합니다. 브라우저 원본 다운로드는 실행 조건이 아니며 서버 원본 접근을 별도로 검사합니다.</p>}
    {canPlan&&session&&!session.canProcess([scene],['red','nir','green','scl'])&&<p className="warning">단일 장면 품질 검사·관측 합성은 red/nir/green/scl이 필요합니다. 기본 NDVI 세트에 green이 없다면 녹색 밴드를 추가 선택하세요. 전체 원본을 먼저 받을 필요는 없습니다.</p>}
    {children}
    <details className="other-request"><summary>다른 작업 요청</summary>
      <p>현재 목적·AOI·기간과 선택 영상을 유지합니다. 예: “이 지역으로 이동해”, “현재 조건으로 검색해”{data.items.length>=2?' , “선택한 두 날짜를 비교해”':''}, “이 영상은 구름이 많아”. 이 의도만 기존 작업으로 연결합니다.</p>
      <label htmlFor="workflow-followup">후속 요청</label>
      <textarea id="workflow-followup" value={followup} onChange={e=>setFollowup(e.target.value)} rows={2} maxLength={2000} placeholder="현재 선택 영상에서 할 다른 작업"/>
      {parsed&&<div className="workflow-structure" data-testid="workflow-structure">
        <strong>해석된 작업 조건 · {parsed.followup_supported===false?'지원하지 않는 요청':parsed.intent==='cloud_help'?'구름 대응':parsed.intent==='compare'?'두 영상 비교':parsed.intent==='move_aoi'?'확정 AOI로 이동':parsed.intent==='search'?'자료 검색':'조건 확인'}</strong>
        <p>{parsed.purpose_label} · {parsed.aoi?.join(', ')} · {parsed.period.start} — {parsed.period.end} UTC · {parsed.selected_scene?.id} · 날짜 변경 미허용</p>
        {parsed.questions.map(q=><p className="warning" key={q}>{q}</p>)}
        {parsed.notes.map(n=><p className="asset-help" key={n}>{n}</p>)}
      </div>}
      {parseError&&<p role="alert">해석 실패: {parseError}</p>}
      <button type="button" disabled={!parsed||parsed.followup_supported===false||!followup.trim()} onClick={requestAction}>요청 적용</button>
    </details>
    {scene&&preprocessingAvailable&&<section id="preprocess-stage" className="search-entry"><h2>③ 전처리 · 필요한 경우만</h2>{session?.analysis.engine==='ndvi_change'?<p>NDVI 변화 엔진 내부에서 두 날짜 SCL 품질 제외·공통20m 격자·확인된 반사도 보정을 수행합니다. 합성·ML 결과를 변화 입력으로 자동 연결하지 않습니다.</p>:<p>기존 관측 픽셀 합성은 실제 SCL 마스킹·공통20m 격자·사용 날짜/출처를 포함한 ZIP을 만듭니다. 다운로드 후 종료할 수 있습니다.</p>}<p>독립 AOI 자르기·임의 CRS/해상도 변환·단독 마스킹 파일 내보내기는 미구현입니다. 지원 엔진에서 내부 수행하는 처리와 구분합니다.</p><p>마스킹은 제외, 다중 시기 합성은 다른 날짜의 실측 선택, ML은 추정입니다. 구름이 있다는 이유로 ML을 자동 실행하지 않습니다.</p>{!finished&&session?.analysis.engine==='ndvi_change'&&<button onClick={()=>{session?.setStage('analysis');document.getElementById('analysis-stage')?.scrollIntoView({behavior:'smooth'});}}>분석으로 계속하기</button>}</section>}
    {showRecovery&&<section className="quality-recovery" aria-label="품질 문제 해결">
      <h3>품질 문제 해결 · 현재 허용 기간 유지</h3>
      <p>사용자 요청 또는 실제 AOI 검사에 따라 안내합니다. 장면 전체 구름량은 후보 탐색용 메타데이터이며 AOI 검사 결과가 아닙니다.</p>
      <h4>1. 같은 기간의 다른 실제 영상 확인</h4>
      <p>검색된 후보만 사용합니다. 검색 한도 밖 장면은 미조사이고 기간을 넓히거나 목적을 바꾸지 않습니다.</p>
      <div className="alternative-scenes">{data.items.filter(s=>s.datetime&&s.datetime.slice(0,10)>=data.query.start_date&&s.datetime.slice(0,10)<=data.query.end_date&&sceneKey(s)!==sceneKey(scene)&&
        (currentPurpose!=='thermal'||(s.collection==='landsat-c2-l2'&&s.processing_level==='L2SP'))).slice(0,10).map(s=><button type="button" key={sceneKey(s)} onClick={()=>onSelect(sceneKey(s))}>{s.datetime?.slice(0,10)} · {s.platform||s.collection} · 다른 영상 확인: {s.id}</button>)}</div>
      {!canPlan&&<p className="warning">이 목적·관측 시점·제품의 실제 관측 합성/ML은 미지원입니다. 다른 영상의 메타데이터·원본 링크를 확인하거나 비교 작업에서 지원되는 QA를 사용하세요.</p>}
      {canPlan&&<>
        <p>합성 후보는 현재 기간의 같은 플랫폼·제품 Sentinel-2 L2A 최대 4개입니다. 실제 AOI 유효율은 원본 SCL/밴드 검사 뒤 확인합니다.</p>
        {eligible().length>0?<details className="workflow-candidates"><summary>합성 후보 날짜 직접 선택 (선택 영상 외 최대 3개)</summary>
          {eligible().slice(0,10).map(s=>{const key=sceneKey(s),current=candidateIds??eligible().slice(0,3).map(sceneKey),checked=current.includes(key);
            return <label key={key}><input type="checkbox" checked={checked} disabled={!checked&&current.length>=3} onChange={e=>{setReviewed(false);setCandidateIds(e.target.checked?[...current,key]:current.filter(id=>id!==key));}}/>
              {s.datetime?.slice(0,10)} · {s.id} · 장면 구름 메타데이터 {fmt(s.scene_cloud_cover,'%')} (AOI 품질 아님)</label>;})}
        </details>:<p>동일 플랫폼·제품의 다른 후보가 없습니다. 현재 범위에서 관측 합성 계획을 만들 수 없습니다.</p>}
        <label className="workflow-check"><input type="checkbox" checked={reviewed} onChange={e=>setReviewed(e.target.checked)}/>현재 기간의 대체 후보와 날짜를 확인했습니다</label>
        <h4>2. 실제 관측 픽셀 선택 합성 계획</h4>
        <button type="button" disabled={!reviewed||planning||starting||active(job)||candidates(false).length<2||!!session&&!session.canProcess(candidates(false),['red','nir','green','scl'])} onClick={()=>void inspect(false)}>현재 기간 후보 검사·합성 계획</button>
      </>}
    </section>}
    {planning&&<p role="status">원본 Item·SCL·필수 밴드의 실제 범위를 읽어 검사 중…</p>}
    {planError&&<p role="alert">{planError}</p>}
    {plan&&<div className="workflow-plan" data-testid="cloud-plan"><h3>{planMode==='single'?'선택 영상 실제 AOI 품질':'실제 관측 검사·합성 계획'}</h3>
      <p><strong>{planMode==='single'&&selectedQA?.status==='checked'?'선택 영상 품질 검사 완료':plan.status==='planned'?'실행 전 확인 필요':plan.status==='blocked'?'현재 조건에서 합성 불가':'검사 실패·미확인'}</strong> · {planMode==='single'&&selectedQA?.status==='checked'?'실측 SCL·NoData 검사이며 분석 가능 확정이 아닙니다.':plan.error||plan.interpretation}</p>
      {selectedQA&&<p>선택 영상 AOI 유효 관측: {fmt(selectedQA.valid_area_m2,' m²')} / {fmt(plan.aoi_area_m2,' m²')} · {selectedQA.status==='checked'?fmt(selectedQA.valid_percent_aoi,'%'):'검사 실패/미관측: 비율 미확인'}</p>}
      {plan.scenes?.map(s=><details key={s.id}><summary>{s.datetime?.slice(0,10)} · {s.id} · {s.status==='checked'?`AOI 유효 ${fmt(s.valid_percent_aoi,'%')}`:'미확인'}</summary>
        <p>{s.error||`기준일과 ${s.date_offset_days}일 차이. SCL 구름·그림자·NoData 등 제외 면적은 아래 근거를 확인하세요.`}</p>
        <pre>{JSON.stringify(s.exclusions_m2,null,2)}</pre></details>)}
      {plan.aoi_area_m2!=null&&<dl className="workflow-metrics"><div><dt>고정 분모 · AOI</dt><dd>{fmt(plan.aoi_area_m2,' m²')}</dd></div>
        <div><dt>원본 선택 영상 유효</dt><dd>{fmt(plan.original_valid_area_m2,' m²')}</dd></div>
        <div><dt>계획 합성 유효</dt><dd>{fmt(plan.composite_valid_area_m2,' m²')} ({fmt(plan.composite_valid_percent_aoi,' %')})</dd></div>
        <div><dt>미관측</dt><dd>{fmt(plan.unobserved_area_m2,' m²')}</dd></div>
        <div><dt>품질/NoData 제외</dt><dd>{fmt(plan.quality_or_nodata_excluded_area_m2,' m²')}</dd></div>
        <div><dt>남는 결측</dt><dd>{fmt(plan.remaining_gap_area_m2,' m²')}</dd></div></dl>}
      {plan.priority&&<p>선택 순서: {plan.priority.map(s=>`${s.datetime.slice(0,10)} ${s.id} (기준 ${s.date_offset_days>=0?'+':''}${s.date_offset_days}일)`).join(' → ')}. 선택 장면 우선, 다른 날짜는 차이가 작은 순·이른 시각·Item ID 순입니다. 한 출력 픽셀의 모든 밴드는 같은 장면에서 가져옵니다.</p>}
      {plan.grid&&<p>공통 격자 {plan.grid.resolution_m} m · {plan.grid.width}×{plan.grid.height} · CRS/extent는 근거에 기록. 가장 오래된 사용 관측 {plan.oldest_observation_date||'미확인'} (기준일과 {fmt(plan.oldest_observation_age_days,'일')}).</p>}
      {plan.estimate&&<p>출력 비압축 크기 근사 {fmt(plan.estimate.output_uncompressed_bytes,'바이트')}. {plan.estimate.note}</p>}
      <p>처리 상한: AOI 25 km², 4장면, 31일, 100,000셀, 전송 64 MiB, 래스터 60초, 동시 1작업. SCL 분류 오류·계절/생육 차이는 남습니다. 구름을 생성·복원하지 않습니다.</p>
      {planMode==='composite'&&plan.status==='planned'&&plan.can_execute&&<><label className="workflow-check"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>위 AOI·기간·목적·장면·마스크 정책과 기간 요약 합성을 확인했습니다</label>
        <button type="button" disabled={!confirmed||!!job||starting} onClick={()=>void execute()}>확인한 계획으로 실제 합성 실행</button></>}
      <details><summary>격자·정책·제한 근거</summary><pre>{JSON.stringify({grid:plan.grid,policy:plan.policy,limits:plan.limits},null,2)}</pre></details>
    </div>}
    {job&&<div className="workflow-job" data-testid="cloud-job" role="status"><strong>작업 {job.status}</strong> · {job.stage}
      {job.error&&<p>{job.error}</p>}
      {active(job)&&<button type="button" onClick={()=>void cancel()}>작업 취소</button>}
      {finished&&<><p>실제 여러 날짜 관측 선택 합성 완료. 원본 유효 {fmt(finished.original_valid_area_m2,' m²')} → 합성 유효 {fmt(finished.composite_valid_area_m2,' m²')} / AOI {fmt(finished.aoi_area_m2,' m²')}. 남은 결측 {fmt(finished.remaining_gap_area_m2,' m²')}.</p>
        <a className="download-link" href={`/api/cloud/jobs/${job.job_id}/download`} download="sentinel-2-observed-composite.zip">전처리 결과 다운로드 · 실제 GeoTIFF·마스크·출처/날짜·manifest ZIP 저장</a><p>관측 합성 결과만 다운로드하고 종료할 수 있습니다. 단일 NDVI 계산과 합성 결과의 NDVI 변화 입력 연결은 미지원입니다.</p></>}
    </div>}
    {estimateReady&&<details className="experimental-estimate"><summary>3. 남은 결측 · 실험적 ML 추정 (선택)</summary>
      <p>실제 관측 합성 계획에서도 결측 {fmt(evidence?.remaining_gap_area_m2,' m²')}가 남았습니다. 추정값은 목표일 실측이 아니며 구름 아래 정확도는 보증하지 않습니다.</p>
      <EstimatedImage data={data} target={scene} candidates={candidates(false)} parsed={parsed} onEstimate={onEstimate} recoveryReady={estimateReady} recoveryKey={JSON.stringify([evidence?.plan_id,evidence?.version,evidence?.remaining_gap_area_m2])}/>
    </details>}
  </section>;
}
