'use client';
import ResultArchive from './ResultArchive';
import dynamic from 'next/dynamic';
import Link from 'next/link';
import {usePathname,useRouter} from 'next/navigation';
import WorkSummary,{RestoredJobs} from './WorkSummary';
import AnalysisSelection from './AnalysisSelection';
import ProcessingExecution from './ProcessingExecution';
import {taskInputs,assessTask,processingCapabilities,automaticTaskBands} from '@/lib/analysisFlow';
import {WorkContext,selectedBands,type Acquisition,type Acquisitions,type SavedJob,type WorkSession} from '@/lib/workSession';
import {readSnapshot,writeSnapshot} from '@/lib/workSnapshot';
import {ndviPairSupported} from '@/lib/workflow';
import {useEffect,useState,useRef,useMemo,useCallback} from 'react';
import SensorRecommendations from '@/components/SensorRecommendations';
import Results from '@/components/Results';
import SceneComparison from '@/components/SceneComparison';
import NaturalWorkflow from '@/components/NaturalWorkflow';
import AutomaticConditions from '@/components/AutomaticConditions';
import {useConditionInput,originLabel,type FormConditions} from '@/lib/useConditionInput';
import ImageryExplorer from '@/components/ImageryExplorer';
import EarthdataConnection from '@/components/EarthdataConnection';
import {groupScenesByDay,firstOnDay,sceneDay} from '@/lib/imageryExplorer';
import {sceneKey} from '@/lib/types';
import {defaultPair,type CompareMode} from '@/lib/selection';
import {post} from '@/lib/api';
import type {Bbox,Purpose,Recommendation,SearchResponse,PixelReport,EstimatePlan,CloudPlan,AnalysisCatalog,ProcessingJobRef,ProcessingJob} from '@/lib/types';
const MapPanel=dynamic(()=>import('@/components/MapPanel'),{ssr:false,loading:()=><div className="map-panel map-loading">지도 불러오는 중…</div>});
const purposes=[['vegetation','식생 분석'],['flood','침수·수역 분석'],['urban','도시·토지피복 변화'],['thermal','열환경 분석']];
export default function WorkflowWorkspace() {
  const path=usePathname(),router=useRouter(),processing=path==='/processing';
  const [ready,setReady]=useState(false),[restored,setRestored]=useState(false),[storageError,setStorageError]=useState('');
  const [analysisCatalog,setAnalysisCatalog]=useState<AnalysisCatalog|null>(null),[analysisError,setAnalysisError]=useState('');
  const [analysisChoice,setAnalysisChoice]=useState<string|null>(null),[confirmedAnalysis,setConfirmedAnalysis]=useState<string|null>(null);
  useEffect(()=>{const abort=new AbortController();fetch('/api/analysis/catalog',{signal:abort.signal,cache:'no-store'}).then(r=>{if(!r.ok)throw new Error('세부 분석 목록 연결 실패');return r.json();}).then(c=>{if(!abort.signal.aborted)setAnalysisCatalog(c);}).catch(()=>{if(!abort.signal.aborted)setAnalysisError('세부 분석 목록을 불러오지 못했습니다. 서버 반영 상태를 확인하세요.');});return()=>abort.abort();},[]);
  const [bands,setBands]=useState<Record<string,string[]>>({}),[acquisitions,setAcquisitions]=useState<Acquisitions>({});
  const [linksSaved,setLinksSaved]=useState<Record<string,number>>({}),[jobs,setJobs]=useState<SavedJob[]>([]),[restoredJobs,setRestoredJobs]=useState<SavedJob[]>([]);
  const [stage,setStage]=useState<WorkSession['stage']>('quality');
  const [processingJob,setProcessingJob]=useState<ProcessingJobRef|null>(null);
  const [settings,setSettingsState]=useState<Record<string,unknown>>({});
  const setSettings=useCallback((values:Record<string,unknown>)=>{
    setSettingsState(old=>({...old,...values}));setQualityReport(null);setMapLayers(undefined);setEstimateLayers(undefined);
    setShowQuality(false);setShowAnalysis(false);setShowEstimated(false);setShowObservedEstimate(false);
  },[]);
  const hydrating=useRef(true),lastRecommendation=useRef('');
  const originalFocus=useRef(false);

  const [purpose,setPurpose]=useState('');
  const [recInput,setRecInput]=useState('');
  const auto=useConditionInput(purpose,()=>invalidate());
  const {start,end,coordinates,purposeType,temporalMode,targetSize,observationNeed}=auto.form,bbox=auto.bbox;
  const effectivePurpose:Purpose=purposeType;
  const purposeBasis=auto.form.origins.purposeType==='auto'?'AI 해석으로 설정':auto.form.origins.purposeType==='manual'?'사용자 직접 선택':null;
  const effectiveTemporal=temporalMode;
  const detailId=analysisChoice??auto.form.intent?.detail??null;
  const chosenTask=analysisCatalog?.analyses.find(a=>a.id===detailId&&a.domain===effectivePurpose)||null;
  const baseRecommendationInput=JSON.stringify({purpose:"",purpose_type:effectivePurpose||null,target_size_m:targetSize?Number(targetSize):null,observation_need:observationNeed,temporal_mode:effectiveTemporal});
  const recommendationInput=JSON.stringify({...JSON.parse(baseRecommendationInput),detail_intent:chosenTask?.id||null,requested_resolution_m:auto.form.resolution?Number(auto.form.resolution):null});
  const [mode,setMode]=useState('auto'),[collections,setCollections]=useState(['sentinel-2-l2a','landsat-c2-l2']);
  const [limit,setLimit]=useState(50),[rec,setRec]=useState<Recommendation|null>(null),[recError,setRecError]=useState('');
  const [data,setData]=useState<SearchResponse|null>(null),[selected,setSelected]=useState<string|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [selectedCardId,setSelectedCardId]=useState<string|null>(null);
  const currentRec=recInput===recommendationInput?rec:null;
  const activeCard=currentRec?.cards?.find(c=>c.id===selectedCardId&&c.search_enabled);
  const effectiveCollections=activeCard?.search_conditions?.collections||(mode==='manual'?collections:currentRec?.collections||[]);
  const searchNext=busy?'실제 영상 검색 중입니다.':auto.composing?'입력 중인 글자를 확정하세요.':auto.pending?'문장 해석·위치 확인을 기다리세요.':!auto.manualMode&&auto.phase==='interrupted'?'검색 대기: 이전 AI 해석 결과 확인이 필요합니다. 위성 선택과는 별개입니다.':!auto.manualMode&&auto.phase==='failed'?'검색 대기: AI 해석에 실패했습니다. 직접 입력으로 전환하면 AI 없이 계속할 수 있습니다.':!effectivePurpose?'분석 목적을 선택하세요.':!start||!end?'시작일과 종료일을 입력하세요.':auto.blocking?'검색 대기: AI 조건의 위치·기간·수동 수정값을 확인하거나 직접 입력으로 전환하세요.':!auto.form.confirmed?'분석 영역이 미확정입니다. 좌표 적용 또는 지도에서 분석 AOI 확정을 누르세요.':!effectiveCollections.length?'검색할 위성 제품을 선택하세요.':'검색 조건이 준비됐습니다. 위성영상 검색을 누르세요.';
  const [collectionComparisonOpen,setCollectionComparisonOpen]=useState(false);
  const [comparisonOpen,setComparisonOpen]=useState(false),[compareMode,setCompareMode]=useState<CompareMode>('sensor');
  const [qualityReport,setQualityReport]=useState<PixelReport|null>(null);
  const [staleQuery,setStaleQuery]=useState<SearchResponse['query']|null>(null);
  const [activeDay,setActiveDay]=useState<string|null>(null),[showFootprints,setShowFootprints]=useState(true),[showPreview,setShowPreview]=useState(true),[showQuality,setShowQuality]=useState(false),[showAnalysis,setShowAnalysis]=useState(false);
  const [mapLayers,setMapLayers]=useState<PixelReport['map_layers']>(undefined),[pair,setPair]=useState<[string,string]>(['','']);
  const [estimateLayers,setEstimateLayers]=useState<EstimatePlan['map_layers']>(undefined),[showObservedEstimate,setShowObservedEstimate]=useState(false),[showEstimated,setShowEstimated]=useState(false);
  const [moveAoiToken,setMoveAoiToken]=useState(0);
  const grouped=useMemo(()=>data?groupScenesByDay(data.items,data.query.start_date,data.query.end_date):null,[data]);
  const scopedData=useMemo(()=>data&&grouped?{...data,items:grouped.included,returned:grouped.included.length}:null,[data,grouped]);
  const selectedScene=scopedData?.items.find(s=>sceneKey(s)===selected)||null;
  const capabilities=processingCapabilities(chosenTask,selectedScene,effectivePurpose);
  const analysisInputs=taskInputs(chosenTask,selectedScene,scopedData?.items||[],pair);
  useEffect(()=>{if(processing)setBands(old=>automaticTaskBands(chosenTask,analysisInputs,old));},[processing,chosenTask,analysisInputs]);
  const taskAssessment=assessTask(chosenTask,analysisInputs,bands,auto.aoiConfirmed?bbox:null,start,end,auto.form.resolution?Number(auto.form.resolution):null);
  // Confirm the user's method, then re-evaluate data on every render. Changing a
  // scene does not require re-entering the same method, but cannot bypass QA/data gates.
  const analysisValidationKey=JSON.stringify([purpose,effectivePurpose,chosenTask?.id]);
  const analysisConfirmed=!!chosenTask&&confirmedAnalysis===analysisValidationKey&&!auto.blocking&&!auto.pending;
  const ndviPair=scopedData?.items.flatMap((a,i)=>scopedData.items.slice(i+1).filter(b=>ndviPairSupported(a,b,effectivePurpose)).map(b=>[sceneKey(a),sceneKey(b)] as [string,string]))[0];
  const qualityLayer=mapLayers?.quality.find(layer=>layer.scene_ids.length===1&&layer.scene_ids[0]===selectedScene?.id)||null;
  const layerScenes=mapLayers?.analysis?.scene_ids;
  const analysisLayer=layerScenes&&(layerScenes.length===1?layerScenes[0]===selectedScene?.id:layerScenes.length===2&&pair[0]&&pair[1]&&scopedData?.items.find(s=>sceneKey(s)===pair[0])?.id===layerScenes[0]&&scopedData?.items.find(s=>sceneKey(s)===pair[1])?.id===layerScenes[1])?mapLayers!.analysis:null;
  const observedEstimateLayer=selectedScene&&estimateLayers?.observed?.scene_ids.includes(selectedScene.id)?estimateLayers.observed:null;
  const estimatedLayer=selectedScene&&estimateLayers?.estimated?.scene_ids.includes(selectedScene.id)?estimateLayers.estimated:null;
  const chooseScene=useCallback((key:string)=>{setSelected(key||null);setMapLayers(undefined);setQualityReport(null);setEstimateLayers(undefined);setShowQuality(false);setShowAnalysis(false);setShowObservedEstimate(false);setShowEstimated(false);const scene=data?.items.find(s=>sceneKey(s)===key);if(scene)setActiveDay(sceneDay(scene));if(!key)setPair(['','']);},[data]);
  const chooseDay=(day:string|null)=>{setActiveDay(day);if(day&&grouped)chooseScene(firstOnDay(grouped.included,day,selected)||'');};
  const changePair=useCallback((next:[string,string])=>{setPair(next);setMapLayers(undefined);setQualityReport(null);setEstimateLayers(undefined);setShowQuality(false);setShowAnalysis(false);setShowObservedEstimate(false);setShowEstimated(false);},[]);
  const applyEstimate=useCallback((result:EstimatePlan|null)=>{
    const layers=result?.status==='succeeded'?result.map_layers:undefined;
    setEstimateLayers(layers);setShowObservedEstimate(!!layers?.observed);setShowEstimated(!!layers?.estimated);
  },[]);
  const requestVersion=useRef(0), searchController=useRef<AbortController|null>(null);
  function invalidate() {
    if(data)setStaleQuery(data.query);
    setQualityReport(null);setComparisonOpen(false);
    requestVersion.current++; searchController.current?.abort();
    setBusy(false);setData(null);setSelected(null);setActiveDay(null);setPair(['','']);setMapLayers(undefined);setShowQuality(false);setShowAnalysis(false);
    setEstimateLayers(undefined);setShowObservedEstimate(false);setShowEstimated(false);setError('');
  }
  useEffect(()=>()=>{searchController.current?.abort();},[]);
  useEffect(()=>{
    if(!ready)return;
    if(hydrating.current){hydrating.current=false;lastRecommendation.current=baseRecommendationInput;return;}
    if(lastRecommendation.current!==baseRecommendationInput){lastRecommendation.current=baseRecommendationInput;invalidate();setSelectedCardId(null);}
  },[baseRecommendationInput,ready]);
  useEffect(()=>{
    if(auto.composing)return;
    let active=true;
    const timer=setTimeout(()=>{post<Recommendation>('recommend',JSON.parse(recommendationInput)).then(r=>{if(active){setRec(r);setRecInput(recommendationInput);setRecError('');}}).catch(e=>{if(active){setRec(null);setRecError(e.message);}});},350);
    return ()=>{active=false;clearTimeout(timer);};
  },[recommendationInput,auto.composing]);

  const contextKey=JSON.stringify([purpose,data?.query,selected,pair,[selected,...pair].map(key=>[key,key?bands[key]:null]),effectivePurpose,effectiveTemporal,settings,chosenTask?.id]);
  const contextRef=useRef(contextKey);contextRef.current=contextKey;
  const historyJobs=useMemo(()=>Array.from(new Map([...restoredJobs,...jobs.filter(row=>row.context!==contextKey)].map(row=>[row.job.job_id,row])).values()),[restoredJobs,jobs,contextKey]);
  const recordAsset=useCallback((scene:import('@/lib/types').Scene,key:string,value:Acquisition)=>setAcquisitions(old=>({...old,[sceneKey(scene)]:{...old[sceneKey(scene)],[key]:value}})),[]);
  const recordLinks=useCallback((scene:import('@/lib/types').Scene)=>setLinksSaved(old=>({...old,[sceneKey(scene)]:Date.now()})),[]);
  const recordJob=useCallback((kind:'cloud'|'estimate',job:import('@/lib/types').CloudJob|import('@/lib/types').EstimateJob,context?:string)=>{
    setJobs(old=>[...old.filter(row=>row.job.job_id!==job.job_id),{kind,job,context:context??contextRef.current}].slice(-8));
  },[]);
  function changeBands(id:string,keys:string[]){
    setBands(old=>({...old,[id]:keys}));setQualityReport(null);setMapLayers(undefined);setEstimateLayers(undefined);
    setShowQuality(false);setShowAnalysis(false);setShowEstimated(false);setShowObservedEstimate(false);
  }
  function chooseAnalysis(id:string|null){setAnalysisChoice(id);setConfirmedAnalysis(null);setQualityReport(null);setMapLayers(undefined);setEstimateLayers(undefined);setShowQuality(false);setShowAnalysis(false);setShowEstimated(false);setShowObservedEstimate(false);}
  const session:WorkSession={analysis:{id:chosenTask?.id||null,label:chosenTask?.label||null,confirmed:analysisConfirmed,metadataReady:taskAssessment.metadataReady,engine:chosenTask?.engine||null},context:contextKey,stage,setStage,settings,setSettings,bands,acquisitions,linksSaved,jobs,setBands:changeBands,
    requestOriginal:()=>{originalFocus.current=true;},
    canSearchPcLandsat:!busy&&!auto.blocking&&!auto.pending&&auto.aoiConfirmed&&!!start&&!!end,searchPcLandsat:()=>{router.push('/');setMode('manual');setCollections(['pc-landsat-c2-l2']);setSelectedCardId(null);void search(undefined,['pc-landsat-c2-l2']);},
    recordAsset,recordLinks,recordJob,canProcess:(scenes,required)=>analysisConfirmed&&taskAssessment.metadataReady&&scenes.length>0&&scenes.every(scene=>(required||selectedBands(scene,bands)).every(key=>selectedBands(scene,bands).includes(key)))};
  useEffect(()=>{
    const saved=readSnapshot();
    if(saved){
      const form=saved.form as FormConditions;
      if(form.coordinates.every(v=>typeof v==='string')&&['','vegetation','flood','urban','thermal'].includes(form.purposeType)){
        auto.restore(form,saved.purpose as string,saved.location as import('@/lib/types').PlaceProposal|null,saved.inputConfirmed===true,saved.interpretation);
        setPurpose(saved.purpose as string);setData((saved.data as SearchResponse)||null);setSelected((saved.selected as string)||null);
        setBands((saved.bands as Record<string,string[]>)||{});setAcquisitions((saved.acquisitions as Acquisitions)||{});setLinksSaved((saved.linksSaved as Record<string,number>)||{});
        setPair((saved.pair as [string,string])||['','']);setCompareMode(saved.compareMode==='temporal'?'temporal':'sensor');
        setMode(saved.mode==='manual'?'manual':'auto');setCollections((saved.collections as string[])||['sentinel-2-l2a','landsat-c2-l2']);
        setSelectedCardId((saved.selectedCardId as string)||null);setQualityReport((saved.qualityReport as PixelReport)||null);
        setSettingsState((saved.settings as Record<string,unknown>)||{});
        setAnalysisChoice(typeof saved.analysisChoice==='string'?saved.analysisChoice:null);setConfirmedAnalysis(typeof saved.confirmedAnalysis==='string'?saved.confirmedAnalysis:null);
        const restoredJob=saved.processingJob as ProcessingJobRef|null;
        if(restoredJob&&/^[a-f0-9]{32}$/.test(restoredJob.job_id)&&typeof restoredJob.context==='string'&&typeof restoredJob.method_id==='string')setProcessingJob(restoredJob);
        setJobs((saved.jobs as SavedJob[])||[]);setRestoredJobs((saved.jobs as SavedJob[])||[]);setRestored(true);
      }
    }
    setReady(true);
  },[]);
  useEffect(()=>{
    if(!ready)return;
    try{writeSnapshot({version:1,purpose,interpretation:auto.snapshot,inputConfirmed:!auto.blocking&&!auto.pending&&!auto.composing,form:auto.form,location:auto.location,data,selected,bands,acquisitions,linksSaved,pair,compareMode,mode,collections,selectedCardId,qualityReport,settings,jobs,analysisChoice,confirmedAnalysis,processingJob});setStorageError('');}
    catch{setStorageError('브라우저 작업 보관이 차단됐거나 상한을 넘었습니다. 페이지 이동은 유지되지만 새로고침 복원은 제한됩니다.');}
  },[ready,purpose,auto.form,auto.location,auto.blocking,auto.pending,auto.composing,JSON.stringify(auto.snapshot),data,selected,bands,acquisitions,linksSaved,pair,compareMode,mode,collections,selectedCardId,qualityReport,settings,jobs,analysisChoice,confirmedAnalysis,processingJob]);
  useEffect(()=>{
    if(path!=='/'||!selected||!originalFocus.current)return;
    const frame=requestAnimationFrame(()=>{
      const panel=document.querySelector(`[data-scene-key='${CSS.escape(selected)}'] .asset-downloads`);
      if(panel){panel.setAttribute('open','');panel.scrollIntoView({behavior:'smooth',block:'start'});originalFocus.current=false;}
    });return()=>cancelAnimationFrame(frame);
  },[path,selected,scopedData]);
  function applyBbox(b:Bbox) {auto.manualBbox(b);}
  function applyQuality(report:PixelReport) {
    
    setQualityReport(report);
    if(!report.map_layers){setMapLayers(undefined);setShowQuality(false);setShowAnalysis(false);}
    if(report.map_layers){setMapLayers(report.map_layers);setShowQuality(!report.map_layers.analysis);setShowAnalysis(!!report.map_layers.analysis);}
    setData(current=>current?{...current,items:current.items.map(scene=>{
        const result=report.scenes?.find(s=>s.id===scene.id&&(s.collection?s.collection===scene.collection:scene.collection==='sentinel-2-l2a'));
      return result?{...scene,pixel_quality:{status:result.status==='checked'?'checked' as const:'failed' as const,message:result.status==='checked'?`현재 AOI 제품 QA·NoData 진단: 개별 유효 ${result.valid_percent_aoi==null?'미계산':result.valid_percent_aoi.toFixed(2)+'%'} · 분석 가능 판정 아님`:'현재 AOI 픽셀 진단 실패/관측 픽셀 없음: 미확인'}}:report.status==='failed'&&(pair.includes(sceneKey(scene))||selected===sceneKey(scene))?{...scene,pixel_quality:{status:'failed' as const,message:'현재 AOI 검사 요청 실패·미확인'}}:scene;
    })}:current);
  }
  function applySingleQuality(plan:CloudPlan){
    
    setData(current=>current?{...current,items:current.items.map(scene=>{
      const result=plan.scenes?.find(s=>s.collection===scene.collection&&s.id===scene.id);
      return result?{...scene,pixel_quality:{status:result.status==='checked'?'checked' as const:'failed' as const,
        message:result.status==='checked'?`현재 AOI 실제 검사: 유효 ${result.valid_percent_aoi==null?'미계산':result.valid_percent_aoi.toFixed(2)+'%'} · 분석 가능 확정 아님`:'현재 AOI 실제 검사 실패·미확인'}}:plan.status==='failed'&&selected===sceneKey(scene)?{...scene,pixel_quality:{status:'failed' as const,message:'현재 AOI 실제 검사 요청 실패·미확인'}}:scene;
    })}:current);
  }
  function coordinateBbox():Bbox {
    if(coordinates.some(v=>v.trim()==='')) throw new Error('관심 지역을 지도에서 선택하거나 좌표 네 개를 입력하세요.');
    const b=coordinates.map(Number) as Bbox;
    if(!b.every(Number.isFinite) || b[0]>=b[2] || b[1]>=b[3] || b[0]<-180 || b[2]>180 || b[1]<-80 || b[3]>80) throw new Error('좌표를 확인하세요. 서 < 동, 남 < 북이며 위도는 -80~80입니다.');
    if(b[2]-b[0]>5 || b[3]-b[1]>5) throw new Error('관심 지역은 가로·세로 각각 5도 이하로 선택하세요.');
    return b;
  }
  async function search(event?:React.FormEvent,override?:string[]) {
    const card=override?undefined:activeCard;
    event?.preventDefault();
    if(auto.blocking||auto.pending||auto.composing){setError('자연어 조건 해석이 끝난 뒤 최종 조건을 확인하고 검색하세요.');void auto.run();return;}
    invalidate();
    const version=requestVersion.current, controller=new AbortController();searchController.current=controller;
    try {
      const b=coordinateBbox();
      if(!auto.aoiConfirmed)throw new Error('분석 AOI를 지도 또는 좌표로 직접 지정하고 확정하세요. 새 지명과 기존 AOI의 유지 여부도 확인하세요.');
      if(!start||!end||start>end) throw new Error('시작일과 종료일을 올바르게 입력하세요.');
      if((Date.parse(end)-Date.parse(start))/86400000>366) throw new Error('조회 기간은 최대 366일입니다.');
      if(!override&&!card&&mode==='manual'&&!collections.length) throw new Error('검색할 위성을 하나 이상 선택하세요.');
      setBusy(true);setData(null);setSelected(null);
      const result=await post<SearchResponse>('search',{...JSON.parse(recommendationInput),recommendation_id:card?.id||null,bbox:b,start_date:start,end_date:end,requested_resolution_m:auto.form.resolution?Number(auto.form.resolution):null,max_scene_cloud_cover:auto.form.cloud?Number(auto.form.cloud):null,requested_reference_date:auto.form.referenceDate||null,analysis_target:auto.form.analysisTarget||null,collections:override||(card||mode==='manual'?effectiveCollections:null),max_items:limit},controller.signal);
      if(version!==requestVersion.current)return;
      setData(result);setStaleQuery(null);const within=groupScenesByDay(result.items,result.query.start_date,result.query.end_date).included;
      setPair(defaultPair(within,'sensor') as [string,string]);setCompareMode('sensor');
      const first=within.find(s=>s.purpose_plan?.group==='primary')||within[0];setSelected(first?sceneKey(first):null);
    } catch(e) {if(version===requestVersion.current)setError(e instanceof Error?e.message:'요청 처리에 실패했습니다.');} finally {if(version===requestVersion.current)setBusy(false);}
  }
  if(path!=='/'&&path!=='/processing')return null;
  return <WorkContext.Provider value={session}><main className={processing?"workflow-workspace":"workflow-workspace collection-workspace"}>
    <header className="topbar"><Link className="brand" href="/"><span className="brand-icon">◎</span><span>Satellite Insight <b>AI</b><small>위성영상 분석 지원 플랫폼</small></span></Link><div className="topbar-right"><EarthdataConnection/><span className="phase-label">{processing?'PROCESSING':'COLLECTION'}</span><span>{processing?'전처리·분석':'데이터 수집'}</span></div></header>
    <nav className="workflow-navigation" aria-label="작업 페이지"><Link href="/" aria-current={!processing?'page':undefined}>01 데이터 수집</Link><Link href="/processing" aria-current={processing?'page':undefined}>02 전처리·분석</Link></nav>
    <ol className="research-progress" aria-label="연구 작업 흐름">{['조건 확정','영상 선택','분석 준비·실행','결과 검토·저장'].map((label,i)=><li key={label} aria-current={i===(processing?(qualityLayer||analysisLayer?3:2):selectedScene?1:0)?'step':undefined}><span>{i+1}</span>{label}</li>)}</ol>
    {storageError&&<p role="status" className="warning">{storageError}</p>}
    {restored&&<details className="collection-help"><summary>이전 작업을 복원했습니다</summary><p>같은 탭의 조건·선택·수신 기록을 복원했습니다. 원본 파일/인증/서명 주소·지도 픽셀·분석 ZIP은 브라우저 저장소에 보관하지 않습니다. 과거 품질 수치는 기록이며, 새로고침만으로 처리하지 않습니다.</p></details>}
    <ResultArchive/><div className="intro" hidden={processing}><div><div className="eyebrow">EARTH OBSERVATION WORKSPACE</div><h1>목적·기간·영역부터 선택하세요</h1><p>조건 확인 → 제품 추천 → 실제 영상 검색</p></div><div className="data-source"><span className="live-dot"/> 실제 데이터 연결<small>Earth Search · Copernicus · NASA CMR</small></div></div>
    <div className={processing?"workspace processing-workspace":"workspace"}><form hidden={processing} id="analysis-input" onSubmit={search} className="conditions" aria-label="영상 검색 조건" aria-describedby={error?"collection-input-error":undefined}><fieldset disabled={!ready}>
      <div className="section-title"><h2>분석 조건</h2><span className="step-number">01</span></div>
      <nav className="condition-shortcuts" aria-label="조건 입력 바로가기"><a href="#purpose">목적</a><a href="#start">기간</a><a href="#coord-0">AOI</a><a href="#collection-search">검색으로 이동</a></nav>
      <div hidden={auto.manualMode}><label htmlFor="purpose">분석 목적</label><textarea id="purpose" aria-describedby="ai-cost-notice" value={purpose} maxLength={2000} onChange={e=>{auto.editText(e.target.value);invalidate();setPurpose(e.target.value);}} onCompositionStart={auto.compositionStart} onCompositionEnd={e=>auto.compositionEnd(e.currentTarget.value)} onBlur={()=>void auto.run()} placeholder="예: 2026년 7월 충남의 집중호우 전후 침수 범위를 분석하고 싶어." rows={3}/></div>
      <AutomaticConditions state={auto}/>
      <section aria-label="요청의 큰 분석 분야" className="automatic-conditions" hidden={auto.manualMode}>
       <strong>큰 분석 분야: {analysisCatalog?.domains.find(d=>d.id===effectivePurpose)?.label||'미지정 · 분야 확인 필요'}</strong>
       {(auto.pending||auto.form.intent?.summary)&&<p>{auto.pending?'새 요청 해석 중 · 이전 요약으로 검색하지 않습니다.':auto.form.intent?.summary}</p>}
       {auto.form.intent?.detail&&<p>보존한 세부 의도: {analysisCatalog?.analyses.find(a=>a.id===auto.form.intent?.detail)?.label||auto.form.intent.detail} · 다음 페이지에서 확인/변경</p>}
       {!!auto.form.intent?.domains.length&&<div>여러 분야 후보 · 추천을 바꾸는 분야만 확인하세요.{auto.form.intent.domains.map(d=><button type="button" key={d} onClick={()=>auto.manualPurposeType(d)}>{analysisCatalog?.domains.find(v=>v.id===d)?.label||d}</button>)}</div>}
      </section>
      <label htmlFor="purpose-type" className="minor-label">목적 직접 선택 <span>{originLabel(auto.form.origins.purposeType)} · 자동 해석이 어려운 경우</span></label><select id="purpose-type" value={purposeType} onChange={e=>{invalidate();auto.manualPurposeType(e.target.value as Purpose);}}><option value="">미지정 · AI 해석 또는 직접 선택</option>{purposes.map(([v,l])=><option key={v} value={v}>{l}</option>)}</select>
      <div className="form-divider"/><label>분석 기간 <span className="label-help">UTC · 최대 366일</span></label><div className="date-row"><div><label htmlFor="start" className="minor-label">시작일 <small id="start-origin" data-testid="start-origin">{originLabel(auto.form.origins.start)}</small></label><input type="date" id="start" aria-label="시작일" aria-describedby="start-origin" value={start} onChange={e=>auto.manualDate('start',e.target.value)} required/></div><div><label htmlFor="end" className="minor-label">종료일 <small id="end-origin" data-testid="end-origin">{originLabel(auto.form.origins.end)}</small></label><input type="date" id="end" aria-label="종료일" aria-describedby="end-origin" value={end} onChange={e=>auto.manualDate('end',e.target.value)} required/></div></div>
      <div className="form-divider"/><label>관심 지역 <span className="label-help">WGS84 · 경도, 위도</span></label><label htmlFor="analysis-place" className="minor-label">분석 장소</label><input id="analysis-place" value={auto.placeInput} maxLength={100} placeholder="장소 이름 입력 · 좌표로만 지정해도 됩니다" onChange={e=>auto.editPlaceInput(e.target.value)} onCompositionStart={auto.placeCompositionStart} onCompositionEnd={e=>auto.placeCompositionEnd(e.currentTarget.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();if(!e.nativeEvent.isComposing&&!auto.composing&&!auto.locating&&auto.placeInput.trim())auto.lookupDirect();}}}/><button type="button" disabled={auto.composing||auto.locating||!auto.placeInput.trim()} onClick={auto.lookupDirect}>{auto.locating?'장소 확인 중…':'장소 찾기'}</button><small>장소를 바꾼 뒤 분석 영역을 다시 확정하세요.</small>{auto.location&&auto.placeInput!==auto.location.name&&<small>입력한 장소는 아직 확인 전입니다. 마지막 확인 위치: {auto.location.name}</small>}<p className="hint">{auto.aoiConfirmed?'분석 AOI 확정':'분석 AOI 미확정 · 좌표 적용 또는 지도 확정 버튼을 누르세요.'}</p><a className="map-input-link" href="#collection-map">지도에서 AOI 지정하기 ↓</a><div className="coordinate-grid">{['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].map((l,i)=><div key={l}><label htmlFor={`coord-${i}`} className="minor-label">{l} <small id={`coord-${i}-origin`} data-testid={`coord-${i}-origin`}>{originLabel(auto.form.origins.coordinates[i])}</small></label><input id={`coord-${i}`} aria-label={l} aria-describedby={`coord-${i}-origin`} type="number" step="any" value={coordinates[i]} onChange={e=>auto.manualCoordinate(i,e.target.value)} placeholder={['126.5','36.3','127.0','36.8'][i]}/></div>)}</div>
      <div className="aoi-actions"><button type="button" onClick={()=>{try{applyBbox(coordinateBbox());}catch(e){setError((e as Error).message);}}}>좌표 적용</button><button type="button" onClick={()=>applyBbox([126.5,36.3,127,36.8])}>충남 예시 영역</button></div>
  <details><summary>위치 재시도·직접 지명·거리 지정</summary>
   <p>장소 이름을 바꿔도 기존 분석 좌표는 유지됩니다. 해외 지역은 좌표로 직접 지정할 수 있습니다. 지도에서 두 꼭짓점을 선택하거나 좌표를 입력·적용하세요.</p><small>위치 서비스: {auto.placeConfig?.ready?'Kakao 설정 준비됨 · 실제 조회 결과와 별개':'미설정/확인 전'}. AI 없이 직접 지정한 지명도 조회할 수 있습니다.</small>
   <label htmlFor="place-query">지명 직접 입력</label><input id="place-query" value={auto.placeInput} maxLength={100} onChange={e=>auto.editPlaceInput(e.target.value)} onCompositionStart={auto.placeCompositionStart} onCompositionEnd={e=>auto.placeCompositionEnd(e.currentTarget.value)}/>
   <button type="button" disabled={auto.composing||auto.locating||!auto.placeInput.trim()} onClick={auto.lookupDirect}>입력 지명 확인</button>
   <button type="button" disabled={auto.composing||auto.locating||!auto.proposal?.extraction?.places?.length} onClick={auto.retryLocation}>위치 검색 재시도</button>
   <label htmlFor="place-radius">장소 주변 거리 (m)</label><input id="place-radius" type="number" min="1" max="100000" value={auto.radius} onChange={e=>auto.setRadius(e.target.value)}/>
   <button type="button" disabled={auto.locating||!auto.radius||!auto.location} onClick={auto.applyRadius}>확인한 장소에 거리 적용</button>
   <p>거리 없는 점 위치에 임의 사각형을 만들지 않습니다. 지도에서 AOI를 직접 지정할 수도 있습니다.</p>
  </details>
      <div className="form-divider"/><label htmlFor="mode">위성 선택</label><select id="mode" value={mode} onChange={e=>{invalidate();setSelectedCardId(null);setMode(e.target.value);}}><option value="auto">목적별 자동 추천</option><option value="manual">직접 선택</option></select>
      {mode==='manual'&&<div className="checks">{[['sentinel-2-l2a','Sentinel-2 Level-2A'],['landsat-c2-l2','Landsat Collection 2 Level-2'],['sentinel-1-grd','Sentinel-1 GRD · Copernicus'],['viirs-vnp09ga-002','Suomi NPP VIIRS VNP09GA · NASA CMR'],['hls-l30-002','NASA HLS L30 · Landsat · v2.0'],['hls-s30-002','NASA HLS S30 · Sentinel-2 · v2.0'],['pc-sentinel-2-l2a','Sentinel-2 L2A · Planetary Computer'],['pc-landsat-c2-l2','Landsat 8/9 C2 L2 · Planetary Computer'],['noaa-viirs-ndvi-cdr','NOAA-20 VIIRS NDVI CDR v1 · NODD']].map(([id,title])=><label key={id}><input type="checkbox" checked={collections.includes(id)} onChange={e=>{invalidate();setSelectedCardId(null);setCollections(e.target.checked?[...collections,id]:collections.filter(c=>c!==id));}}/>{title}</label>)}</div>}
      <label htmlFor="limit" className="minor-label">최대 조회 개수</label><select id="limit" value={limit} onChange={e=>{invalidate();setLimit(Number(e.target.value));}}>{[25,50,100].map(n=><option key={n} value={n}>{n}건</option>)}</select>
      <details className="sensor-options"><summary>관측 조건 선택 (선택 입력)</summary>
        <small>{originLabel(auto.form.origins.targetSize)}</small><label htmlFor="target-size">구분하려는 대상의 대략적 크기 (m)</label><input id="target-size" type="number" min="0.01" max="100000" step="any" value={targetSize} placeholder="미입력 시 크기 판정 보류" onChange={e=>{invalidate();auto.manualField('targetSize',e.target.value);}}/>
        <small>{originLabel(auto.form.origins.temporalMode)}</small><label htmlFor="temporal-mode">관측 시점</label><select id="temporal-mode" value={temporalMode} onChange={e=>{invalidate();auto.manualTemporalMode(e.target.value as 'single'|'change'|'unspecified');}}><option value="unspecified">미지정 · 가정 표시</option><option value="single">한 시점 상태</option><option value="change">전후 변화</option></select>
        <small>{originLabel(auto.form.origins.observationNeed)}</small><label htmlFor="observation-need">구름·야간 관측 필요</label><select id="observation-need" value={observationNeed} onChange={e=>{invalidate();auto.manualField('observationNeed',e.target.value);}}><option value="unspecified">미지정 · 가정 표시</option><option value="clear_day">맑은 주간 관측 가능</option><option value="all_weather">구름 중 관측 필수</option><option value="night">야간 관측 필수</option></select>
        <small>{originLabel(auto.form.origins.analysisTarget)}</small><label htmlFor="analysis-target">분석 대상</label><input id="analysis-target" value={auto.form.analysisTarget} onChange={e=>auto.manualField('analysisTarget',e.target.value)}/>
        <small>{originLabel(auto.form.origins.resolution)}</small><label htmlFor="requested-resolution">요청 해상도 상한 (m)</label><input id="requested-resolution" type="number" min="0.01" max="100000" value={auto.form.resolution} onChange={e=>auto.manualField('resolution',e.target.value)}/>
        <small>{originLabel(auto.form.origins.cloud)}</small><label htmlFor="cloud-limit">장면 전체 구름량 상한 (%)</label><input id="cloud-limit" type="number" min="0" max="100" value={auto.form.cloud} onChange={e=>auto.manualField('cloud',e.target.value)}/><small>장면 메타데이터 필터이며 AOI 픽셀 QA가 아닙니다.</small>
        <small>{originLabel(auto.form.origins.referenceDate)}</small><label htmlFor="requested-reference">비교 기준일 (UTC)</label><input id="requested-reference" type="date" min={start||undefined} max={end||undefined} value={auto.form.referenceDate} onChange={e=>auto.manualField('referenceDate',e.target.value)}/>
      </details>
      <section className="search-entry collection-search" aria-label="실제 영상 검색" id="collection-search" tabIndex={-1}>
       <div className="collection-next" role="status" id="collection-next"><strong>다음에 할 일</strong><p>{searchNext}</p>{!auto.manualMode&&auto.blocking&&!auto.pending&&<button type="button" onClick={auto.useManual}>현재 조건으로 직접 입력 전환</button>}</div>
       <div data-testid="effective-search-selection" role="status"><p>{activeCard?`선택 제품: ${activeCard.product}`:mode==='manual'?'수동 선택 적용':'현재 목적의 자동 추천 적용'}</p><p>최종 검색 컬렉션: {effectiveCollections.join(' · ')||'선택 없음 / 추천 확인 필요'}</p></div>
       <details><summary>적용할 제품·검색 범위와 제한</summary><small>추천 카드를 고르면 해당 제품으로 검색합니다. 이후 위성 선택 방식·체크박스를 바꾸면 카드 선택을 해제하고 수동/자동 조건을 적용합니다.</small><p className="hint">작은 AOI로 검색에 성공해도 모든 제품이 작은 대상을 상세 분석할 수 있다는 뜻은 아닙니다. Sentinel-1은 SAR 검색·메타데이터·접근 안내만 지원합니다. VIIRS VNP09GA.002는 일별 지표반사도이며 산불 탐지·야간조명 제품이 아닙니다. VIIRS 픽셀 QA·NDVI는 앱 내 미지원입니다.</p></details>
       {!processing&&error&&<div role="alert" className="error" id="collection-input-error"><strong>검색 조건 또는 연결을 확인하세요</strong><p>{error}</p></div>}
       <button form="analysis-input" className="search-button" type="submit" aria-describedby="collection-next" disabled={busy||auto.blocking||auto.pending||auto.composing}>{busy?"실제 위성영상 검색 중…":"위성영상 검색"} <span>↗</span></button>
      </section>
    </fieldset></form><div className="right-column">
      <div hidden={!processing}><h1>전처리·분석</h1>{selectedScene?<><WorkSummary scene={selectedScene} data={scopedData} processing capabilities={capabilities}/></>:<section className="search-entry" data-testid="processing-empty" aria-label="처리할 영상 없음"><h2>{ready?"선택 영상이 없습니다":"작업 복원 중…"}</h2><p>데이터 수집에서 영상을 검색·선택한 뒤 이 화면으로 이어가세요. 검색·다운로드·처리는 자동 실행하지 않습니다.</p><Link className="download-link" href="/">데이터 수집으로 돌아가기</Link></section>}</div>
      {processing&&selectedScene&&<AnalysisSelection catalog={analysisCatalog} error={analysisError} domain={effectivePurpose} intent={auto.form.intent} task={chosenTask} items={scopedData?.items||[]} pair={pair} assessment={taskAssessment} confirmed={analysisConfirmed} capabilities={capabilities} onChoose={chooseAnalysis} onPair={next=>{changePair(next);setCompareMode('temporal');}} onConfirm={()=>{setConfirmedAnalysis(analysisValidationKey);if(chosenTask?.comparison)setCompareMode('temporal');}} onOriginal={()=>{originalFocus.current=true;}}/>}
      {processing&&selectedScene&&<ProcessingExecution task={chosenTask} confirmed={analysisConfirmed} bbox={bbox} aoiConfirmed={auto.aoiConfirmed} boundary={auto.form.boundary} start={start} end={end} reference={auto.form.referenceDate} items={scopedData?.items||[]} selected={selected} onSelect={chooseScene} pair={pair} onPair={changePair} savedJob={processingJob} onJob={setProcessingJob} onResult={result=>{
        if(result.map_layers&&'quality' in result.map_layers)applyQuality({...result,status:'checked'} as PixelReport);
        else applyEstimate({...result,status:'succeeded'} as EstimatePlan);
      }}/>}
      {processing&&selectedScene&&<>
        <div className="workflow-actions">{qualityLayer&&<button onClick={()=>setShowQuality(v=>!v)}>실제 품질 레이어 {showQuality?'끄기':'켜기'}</button>}{analysisLayer&&<button onClick={()=>setShowAnalysis(v=>!v)}>실제 계산 결과 레이어 {showAnalysis?'끄기':'켜기'}</button>}{observedEstimateLayer&&<button onClick={()=>setShowObservedEstimate(v=>!v)}>합성/ML 원관측 레이어</button>}{estimatedLayer&&<button onClick={()=>setShowEstimated(v=>!v)}>ML 추정 레이어 (실측 아님)</button>}</div>
      </>}
      <div hidden={processing&&!selectedScene} id="collection-map" tabIndex={-1}><MapPanel boundaryProposal={auto.boundaryProposal} confirmedBoundary={auto.form.boundary} camera={auto.camera} onManualCamera={auto.manualCamera} aoiConfirmed={auto.aoiConfirmed} onConfirmAoi={auto.confirmAoi} bbox={bbox} onBbox={b=>auto.manualBbox(b,false)} scenes={scopedData?.items||[]} selected={selected} onSelect={chooseScene} activeDay={activeDay} showFootprints={showFootprints} pair={pair} qualityOverlay={showQuality?qualityLayer:null} analysisOverlay={showAnalysis?analysisLayer:null} observedEstimateOverlay={showObservedEstimate?observedEstimateLayer:null} estimatedOverlay={showEstimated?estimatedLayer:null} moveAoiToken={moveAoiToken}/></div>
      <div hidden={processing}><section className="recommendation"><div className="recommendation-icon">✧</div><div><div className="eyebrow">SENSOR RECOMMENDATION</div><h2>{rec?.label||'분석 목적을 입력하세요'}</h2>{rec&&<details className="collection-help"><summary>추천 이유·적용 범위</summary>{rec.reasons.map(r=><p key={r}>{r}</p>)}{rec.future.map(r=><p className="future" key={r}>{r}</p>)}{rec.matched.length ? <small>분류 근거: {purposeBasis||rec.matched.join(', ')}</small>:null}</details>}{recError&&<p role="status">추천 서버 연결 실패: {recError}</p>}</div></section>
      <SensorRecommendations recommendation={data?.recommendation&&(data.recommendation.detail_intent??null)===(chosenTask?.id??null)?data.recommendation:currentRec||data?.recommendation||null} selectedScene={data?.items.find(s=>sceneKey(s)===selected)} busy={busy||auto.pending||auto.composing} selectedCardId={selectedCardId} onSelect={card=>{invalidate();setSelectedCardId(card.id);setCollections(card.search_conditions?.collections||[]);}} start={start} end={end} bbox={bbox} aoiConfirmed={auto.aoiConfirmed}/>

      <a className="map-input-link" href="#collection-search">검색 버튼으로 이동 ↑</a>
      {scopedData&&grouped&&<ImageryExplorer days={grouped.days} total={grouped.included.length} activeDay={activeDay} onDay={chooseDay} scene={selectedScene} showPreview={showPreview} onPreview={setShowPreview} showFootprints={showFootprints} onFootprints={setShowFootprints} qualityReady={!!qualityLayer} analysisReady={!!analysisLayer} observedEstimateReady={!!observedEstimateLayer} estimateReady={!!estimatedLayer} showQuality={showQuality&&!!qualityLayer} onQuality={setShowQuality} showAnalysis={showAnalysis&&!!analysisLayer} onAnalysis={setShowAnalysis} showObservedEstimate={showObservedEstimate&&!!observedEstimateLayer} onObservedEstimate={setShowObservedEstimate} showEstimated={showEstimated&&!!estimatedLayer} onEstimated={setShowEstimated} outside={grouped.outside} unknownDate={grouped.unknownDate}/>}
      {scopedData&&scopedData.items.length>1&&<details className="collection-comparison" onToggle={e=>setCollectionComparisonOpen(e.currentTarget.open)}><summary>두 장면 미리보기·메타데이터 비교</summary>{!processing&&collectionComparisonOpen&&<SceneComparison data={scopedData} pair={pair} onPairChange={changePair} mode={compareMode} onModeChange={setCompareMode} metadataOnly/>}</details>}
    <WorkSummary scene={selectedScene} data={scopedData} processing={false}/>
    {scopedData&&<Results key={JSON.stringify(scopedData.query)+scopedData.items.map(sceneKey).join(',')} data={scopedData} selected={selected} onSelect={chooseScene} activeDay={activeDay}/>}
      </div>
      <div hidden={!processing||!selectedScene||!capabilities.quality}>
       {!analysisConfirmed&&selectedScene&&<p className="warning" role="status">먼저 세부 분석을 확인하세요. 이전 확인은 분야·조건·영상·밴드 변경 시 다시 검증합니다.</p>}
       <fieldset className="analysis-execution" disabled={!analysisConfirmed}>
       {selectedScene&&<>
        <nav className="workflow-navigation" aria-label="처리 단계">{[['quality','② 품질 확인'],...(capabilities.preprocessing?[['preprocess','③ 전처리']]:[]),...(capabilities.analysis?[['analysis','④ 분석·내보내기']]:[])].map(([key,label])=><button key={key} type="button" aria-pressed={stage===key} onClick={()=>{setStage(key as WorkSession['stage']);document.getElementById(key==='quality'?'next-work':key==='preprocess'?'preprocess-stage':'analysis-stage')?.scrollIntoView({behavior:'smooth'});}}>{label}</button>)}</nav>
        <p className="hint">두 시점 공통 AOI 유효율: {qualityReport?.common_valid_percent_aoi==null?'미계산 · 지원 원본 품질 검사를 실행해야 합니다.':qualityReport.common_valid_percent_aoi.toFixed(2)+'% (검사 당시 기록)'}. 장면 전체 구름량은 AOI 품질이 아닙니다.</p>
       </>}
      <NaturalWorkflow key={JSON.stringify([scopedData?.query,selected,pair,purpose,effectivePurpose,targetSize,observationNeed,effectiveTemporal,bands,chosenTask?.id])} enabled={capabilities.quality} preprocessingAvailable={capabilities.preprocessing} purpose={purpose} purposeType={effectivePurpose} targetSize={targetSize} observationNeed={observationNeed}
        temporalMode={analysisConfirmed&&chosenTask?(chosenTask.comparison?'change':'single'):effectiveTemporal} bbox={bbox} start={start} end={end} selected={selected} data={scopedData} composing={auto.composing} pair={pair} qualityReport={qualityReport} comparisonOpen={comparisonOpen} onCloseCompare={()=>setComparisonOpen(false)} onSelect={chooseScene}
        onSearch={()=>void search()} onCompare={(temporal=false)=>{setComparisonOpen(true);if(temporal)setCompareMode('temporal');}} onMoveAoi={()=>setMoveAoiToken(v=>v+1)} onEstimate={applyEstimate} onSingleQuality={applySingleQuality}>
      {scopedData&&selected&&comparisonOpen&&<SceneComparison key={JSON.stringify(scopedData.query)+scopedData.items.map(sceneKey).join(',')} data={scopedData} onQuality={applyQuality} onPairChange={changePair} pair={pair} mode={compareMode} onModeChange={setCompareMode}/>}
      </NaturalWorkflow>
      {selectedScene&&capabilities.analysis&&<section id="analysis-stage" className="search-entry"><h2>④ 분석·내보내기</h2><p>현재 지원 분석은 원본 Sentinel-2 L2A 같은 플랫폼·기준선 두 날짜의 NDVI 변화입니다. 합성 ZIP/ML 결과를 NDVI 변화 엔진에 직접 넣는 연결은 미구현입니다.</p><p>일반적인 전처리는 강제하지 않습니다. 지원 원본의 필수 밴드·SCL·보정·면적 조건은 기존 서버가 다시 확인합니다.</p><button disabled={!ndviPair||chosenTask?.engine!=='ndvi_change'||!analysisConfirmed||!taskAssessment.metadataReady} onClick={()=>{setComparisonOpen(true);setCompareMode('temporal');}}>두 날짜 NDVI 작업 열기</button></section>}
      <div id="analysis-outlet"/>
       </fieldset>
      </div>
      <div hidden={!processing||!selectedScene}><RestoredJobs jobs={historyJobs} context={contextKey}/></div>
      {processing&&!!selectedScene&&error&&<div role="alert" className="error"><strong>검색 조건 또는 연결을 확인하세요</strong><p>{error}</p></div>}
      {!processing&&staleQuery&&<div role="status" className="warning" data-testid="stale-results">이전 조건의 검색·분석 결과는 오래된 결과입니다. 이전 기간 {staleQuery.start_date}–{staleQuery.end_date}, AOI {staleQuery.bbox.join(", ")}. 현재 조건으로 다시 검색하세요. 이전 결과는 새 분석에 사용하지 않습니다.</div>}
      {!processing&&busy&&<div className="empty" role="status"><span className="loading-dot"/> Earth Search에서 실제 메타데이터를 조회하고 있습니다.</div>}
      {!processing&&!data&&!busy&&<div className="empty"><span className="empty-icon">▤</span><h3>분석할 지역에서 어떤 영상이 촬영되었을까요?</h3><p>조건을 설정하고 검색하면 영상 목록과 촬영 범위, 원본 파일 링크를 확인할 수 있습니다.</p></div>}
    </div></div>

    <footer hidden={processing&&!selectedScene}>Satellite Insight AI <span>검색 · 품질 진단 · 식생 NDVI 변화</span><span>NDVI 차이는 변화 원인이나 식생 증감을 확정하지 않습니다.</span></footer>
  </main></WorkContext.Provider>;
}
