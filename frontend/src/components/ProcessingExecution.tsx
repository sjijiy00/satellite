'use client';
import {useEffect,useRef,useState} from 'react';
import {post} from '@/lib/api';
import {selectedBands,useWorkSession} from '@/lib/workSession';
import ProcessingOutcome from './ProcessingOutcome';
import ProcessingFailure from './ProcessingFailure';
import ResearchGuide from './ResearchGuide';
import ResearchRecord from './ResearchRecord';
import {sceneKey,type AnalysisTask,type Bbox,type BoundaryProposal,type ProcessingJob,type ProcessingJobRef,type ProcessingPlan,type Scene} from '@/lib/types';
type Controls={threshold?:string;basis?:string;maximum_uncertainty_k?:string;minimum_cloud_distance_km?:string;regions?:string[][];labels?:string[];regionsConfirmed?:boolean};

export default function ProcessingExecution({task,confirmed,bbox,aoiConfirmed,boundary,start,end,reference,items,selected,onSelect,pair,onPair,savedJob,onJob,onResult}:{
 task:AnalysisTask|null;confirmed:boolean;bbox:Bbox|null;aoiConfirmed:boolean;boundary:BoundaryProposal|null;start:string;end:string;reference:string;
 items:Scene[];selected:string|null;onSelect:(key:string)=>void;pair:[string,string];onPair:(pair:[string,string])=>void;
 savedJob:ProcessingJobRef|null;onJob:(ref:ProcessingJobRef)=>void;onResult:(result:NonNullable<ProcessingJob['result']>)=>void;
}){
 const session=useWorkSession(),methods=task?.execution?.methods||[];
 const [choice,setChoice]=useState(savedJob?.method_id||''),[pairMode,setPairMode]=useState(savedJob?.uses_pair||false),[polygon,setPolygon]=useState(()=>{
  try{const roi=JSON.parse(savedJob?.context||'{}').roi;return roi?.mode==='polygon'&&roi.source==='registered_boundary';}catch{return false;}
 });
 const method=methods.find(m=>m.id===choice)||methods.find(m=>m.engine===task?.engine)||methods[0];
 const usePair=!!method&&method.maximum_scenes>1&&(pairMode||method.minimum_scenes>1);
 const scenes=(usePair?pair.map(k=>items.find(s=>sceneKey(s)===k)):[items.find(s=>sceneKey(s)===selected)]).filter((s):s is Scene=>!!s);
 // Server catalog only. An explicit expert selection (including an empty set)
 // is never overwritten; changing methods offers explicit restoration below.
 useEffect(()=>{for(const scene of scenes){const key=sceneKey(scene),p=method?.products?.find(p=>p.provider_id===scene.provider_id&&p.collection===scene.collection);if(p&&session&&!Object.hasOwn(session.bands,key))session.setBands(key,[...new Set([...(scene.purpose_plan?.default_keys||[]),...p.required_keys])].filter(k=>scene.download_assets?.some(a=>a.key===k)));}},[method?.id,scenes.map(sceneKey).join('|')]);
 const roi=polygon?{confirmed:aoiConfirmed,mode:'polygon',bbox,source:'registered_boundary',boundary_id:boundary?.id}:{confirmed:aoiConfirmed,mode:'bbox',bbox,source:'manual_bbox'};
 const settings=(session?.settings.product_inputs||{}) as Record<string,Controls>,controls=settings[method?.id||'']||{};
 const update=(values:Partial<Controls>)=>session?.setSettings({product_inputs:{...settings,[method!.id]:{...controls,...values}}});
 const regions=controls.regions||[['','','',''],['','','','']],labels=controls.labels||['도시','주변'];
 const regionReady=!!controls.regionsConfirmed&&regions.every(row=>row.length===4&&row.every(x=>x!==''&&Number.isFinite(Number(x))));
 const parametersReady=(!method?.inputs?.threshold||(controls.threshold!==undefined&&controls.threshold!==''&&Number.isFinite(Number(controls.threshold))&&!!controls.basis?.trim()))&&(!method?.inputs?.comparison_regions||regionReady);
 const input={purpose_type:task?.domain,analysis_id:task?.id,method_id:method?.id,roi,start_date:start,end_date:end,reference_date:reference||null,
  comparison_regions:method?.inputs?.comparison_regions?regions.map(row=>({confirmed:!!controls.regionsConfirmed,mode:'bbox',bbox:row.map(Number),source:'manual_bbox'})):[],
  comparison_labels:method?.inputs?.comparison_regions?labels:null,threshold:method?.inputs?.threshold&&controls.threshold!==undefined&&controls.threshold!==''?Number(controls.threshold):null,
  threshold_basis:method?.inputs?.threshold?controls.basis?.trim()||null:null,
  qa_options:method?.inputs?.thermal_qa?{maximum_uncertainty_k:Number(controls.maximum_uncertainty_k??'2'),minimum_cloud_distance_km:Number(controls.minimum_cloud_distance_km??'1')}:{},qa_policy_version:method?.qa_policy_version,
  scenes:scenes.map(s=>({provider_id:s.provider_id,collection:s.collection,id:s.id,asset_keys:selectedBands(s,session?.bands||{})}))};
 const context=JSON.stringify(input),current=useRef(context);current.current=context;
 const version=useRef(0),abort=useRef<AbortController|null>(null);
 const [plan,setPlan]=useState<ProcessingPlan|null>(null),[checked,setChecked]=useState(false),[job,setJob]=useState<ProcessingJob|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState(''),[download,setDownload]=useState('');
 const applied=useRef('');
 const [lookup,setLookup]=useState(0),[unavailable,setUnavailable]=useState(false),[receiving,setReceiving]=useState(false),[downloadFailed,setDownloadFailed]=useState(false),[now,setNow]=useState(Date.now());
 useEffect(()=>{const timer=setInterval(()=>setNow(Date.now()),1000);return()=>clearInterval(timer);},[]);
 useEffect(()=>{version.current++;abort.current?.abort();applied.current='';setPlan(null);setChecked(false);setBusy(false);setError('');setDownload('');setDownloadFailed(false);},[context]);
 useEffect(()=>()=>{version.current++;abort.current?.abort();},[]);
 useEffect(()=>{
  if(!savedJob?.job_id||!/^[a-f0-9]{32}$/.test(savedJob.job_id))return;
  let stop=false;const controller=new AbortController();let timer:ReturnType<typeof setTimeout>;
  async function poll(){
   try{const response=await fetch(`/api/processing/jobs/${savedJob!.job_id}`,{cache:'no-store',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(8000)])});
    if(!response.ok){if(!stop)setUnavailable(true);throw new Error('작업 조회 불가 · 다른 세션/서버 재시작/보관 만료 여부를 확인하세요.');}
    const next=await response.json() as ProcessingJob;if(next.job_id!==savedJob!.job_id)throw new Error('작업 응답 식별자가 다릅니다.');
    if(!stop){setUnavailable(false);setJob(next);if(['queued','running'].includes(next.status)||next.retention?.state==='available')timer=setTimeout(()=>void poll(),['queued','running'].includes(next.status)?1000:15000);}
   }catch(e){if(!stop){setUnavailable(true);setError(e instanceof Error?e.message:'작업 조회 실패');}}
  }
  void poll();return()=>{stop=true;controller.abort();clearTimeout(timer);};
 },[savedJob?.job_id,lookup]);
 useEffect(()=>{
  if(!unavailable&&job?.status==='succeeded'&&job.result&&savedJob?.context===context&&applied.current!==job.job_id){applied.current=job.job_id;onResult(job.result);}
 },[job,context,savedJob,onResult,unavailable]);
 const expiry=job?.retention?.expires_at||job?.artifact?.expires_at;
 const seconds=expiry?Math.max(0,Math.floor((Date.parse(expiry)-now)/1000)):null;
 const quotaWait=job?.status==='failed'&&savedJob?.context===context&&job.failure?.code==='transfer_quota'&&Date.parse(job.failure.retry_at||'')>now;
 const alternatives=items.filter(s=>sceneKey(s)!==selected&&s.datetime?.slice(0,10)!==scenes[0]?.datetime?.slice(0,10)&&method?.products?.some(p=>p.provider_id===s.provider_id&&p.collection===s.collection&&p.platforms.includes(s.platform||'')&&p.levels.includes(s.processing_level||'')&&(!method.inputs?.thermal_qa||s.processing_level==='L2SP')));
 const downloadable=!!job?.artifact&&!unavailable&&(seconds===null||seconds>0)&&(!job.retention||job.retention.state==='available');
 const eligible=!!method&&(!polygon||!!boundary?.id&&method.spatial.polygon)&&scenes.length>=method.minimum_scenes&&scenes.length<=method.maximum_scenes&&scenes.every(s=>method.products?method.products.some(p=>p.provider_id===s.provider_id&&p.collection===s.collection&&p.platforms.includes(s.platform||'')&&p.levels.includes(s.processing_level||'')&&(method.inputs?.thermal_qa?s.processing_level==='L2SP':true)):method.providers.includes(s.provider_id||'')&&method.collections.includes(s.collection)&&method.levels.includes(s.processing_level||''));
 async function makePlan(){
  if(!confirmed||!aoiConfirmed||!bbox||!eligible||!parametersReady||busy||quotaWait)return;
  const v=++version.current,c=new AbortController();abort.current=c;setBusy(true);setError('');setPlan(null);setChecked(false);
  try{const result=await post<ProcessingPlan>('processing/plans',input,c.signal);if(v===version.current&&current.current===context)setPlan(result);}
  catch(e){if(v===version.current)setError(e instanceof Error?e.message:'계획 검사 실패');}
  finally{if(v===version.current)setBusy(false);}
 }
 async function startJob(){
  if(!plan||!checked||busy)return;
  const v=++version.current,c=new AbortController();abort.current=c;setBusy(true);setError('');
  try{const result=await post<ProcessingJob>('processing/jobs',{plan_id:plan.plan_id,confirmation_digest:plan.confirmation_digest,idempotency_key:plan.plan_id},c.signal);
   if(v===version.current&&current.current===context){onJob({job_id:result.job_id,context,method_id:method!.id,uses_pair:usePair});setUnavailable(false);setJob(result);setPlan(null);setChecked(false);}
  }catch(e){if(v===version.current)setError(e instanceof Error?e.message:'작업 시작 실패');}
  finally{if(v===version.current)setBusy(false);}
 }
 async function cancel(){
  if(!job)return;try{setJob(await post<ProcessingJob>(`processing/jobs/${job.job_id}/cancel`,{}));}
  catch(e){setError(e instanceof Error?e.message:'취소 실패');}
 }
 async function receive(){
  if(!job?.artifact||job.status!=='succeeded'||!downloadable||receiving)return;
  const v=version.current,c=new AbortController();abort.current=c;setReceiving(true);setDownloadFailed(false);setDownload('ZIP 전체 수신·해시 확인 중…');
  try{
   const response=await fetch(`/api/processing/jobs/${job.job_id}/download`,{signal:AbortSignal.any([c.signal,AbortSignal.timeout(120000)]),redirect:'error',cache:'no-store'});
   const length=Number(response.headers.get('content-length'));
   if(!response.ok){await response.body?.cancel();if(response.status===410||response.status===404)setUnavailable(true);throw new Error(response.status===429?'파일 전송 동시성/사용량 상한입니다. 잠시 뒤 다시 시도하세요.':response.status===410||response.status===404?'파일 보관 만료·누락 또는 세션 만료입니다. 상태를 다시 확인하세요.':`처리 결과 다운로드 실패 (HTTP ${response.status}). 다시 시도하세요.`);}
   if(response.headers.get('content-type')!=='application/zip'||!Number.isSafeInteger(length)||length<=0||length>16*1024**2||length!==job.artifact.bytes){await response.body?.cancel();throw new Error('검증된 ZIP 응답/크기 확인 실패. 보관 만료·파일 변경 여부를 확인하세요.');}
   if(!response.body)throw new Error('파일 본문이 없습니다.');
   const reader=response.body.getReader(),chunks:Uint8Array<ArrayBuffer>[]=[];let size=0;
   try{while(true){const part=await reader.read();if(part.done)break;size+=part.value.length;if(size>length)throw new Error('다운로드 상한 초과');chunks.push(new Uint8Array(part.value));}}catch(e){await reader.cancel();throw e;}finally{reader.releaseLock();}
   if(size!==length)throw new Error('불완전한 파일 수신입니다.');
   const blob=new Blob(chunks,{type:'application/zip'}),bytes=await blob.arrayBuffer();
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))).map(n=>n.toString(16).padStart(2,'0')).join('');
   if(hash!==job.artifact.sha256)throw new Error('수신 ZIP SHA-256 불일치');
   if(v!==version.current||c.signal.aborted)return;
   const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=/^[A-Za-z0-9_.-]+$/.test(job.artifact.filename)?job.artifact.filename:'processing-result.zip';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
   setDownload(`ZIP 전체 ${size.toLocaleString()} bytes 수신·SHA-256 확인. 디스크 저장 및 GIS 재열기는 별도 확인하세요.`);
  }catch(e){if(v===version.current){setDownloadFailed(true);setDownload(e instanceof Error?e.message:'파일 수신 실패');}}
  finally{setReceiving(false);}
 }
 return <section className="search-entry processing-foundation" aria-label="공통 픽셀 처리" data-testid="processing-foundation">
  <h2>② 실행 설정</h2>
  <details className="collection-help"><summary>처리 방식·선택 영상 정보</summary>
  <p>선택한 원본 Asset을 서버에서 범위 읽기합니다. 원본 전체 다운로드는 선택 사항이며, 브라우저 TIFF·로컬 업로드는 처리 입력이 아닙니다.</p><details><summary>추천·접근·품질·처리 상태의 차이</summary><p>추천 적합·검색 가능·원본 접근 확인·AOI 실제 QA·분석 성공·파일 전달은 별개입니다. 미리보기와 원본 다운로드 기록만으로 QA를 통과하지 않습니다.</p></details>
  <section aria-label="선택 장면의 품질 메타데이터"><h3>품질 확인 · 실제 AOI QA와 별개인 메타데이터</h3>{scenes.map(s=><p key={sceneKey(s)}>{s.datetime?.slice(0,10)} · {s.id}<br/>장면 전체 구름량: {s.scene_cloud_cover==null?'미제공':s.scene_cloud_cover+'%'} · AOI 기하 중첩: {s.overlap_percent==null?'미확인':s.overlap_percent+'%'}</p>)}<p>AOI 실제 QA·유효 관측률은 실행 후 아래 결과에서 확인합니다. 계획·미리보기·기하 중첩만으로 QA를 통과한 것이 아닙니다.</p></section>
  </details>
  {!method?<p>현재 세부 분석에 연결된 실행 방법이 없습니다. {task?.execution?.unsupported_reason||'서버 실행 카탈로그를 확인하세요.'}</p>:<>
   {methods.some(m=>m.id==='thermal_gapfill')&&<fieldset><legend>전처리 · 구름 제거</legend><label htmlFor="cloud-treatment">구름 전처리 방식</label><select id="cloud-treatment" value={['thermal_gapfill','thermal_ml'].includes(method.id)?method.id:'surface_temperature'} onChange={e=>{setChoice(e.target.value);if(e.target.value!=='surface_temperature'&&!usePair)onPair([selected||pair[0],pair[1]===selected?'':pair[1]]);}}><option value="surface_temperature">사용 안 함 · 유효 관측만 분석</option><option value="thermal_gapfill">다른 날짜의 실제 관측으로 보충</option>{methods.some(m=>m.id==='thermal_ml')&&<option value="thermal_ml">머신러닝으로 구름 결측 추정 · 검증 필요</option>}</select>{method.id!=='surface_temperature'&&<p>{method.id==='thermal_ml'?'맑은 공통 관측으로 학습하고 공간 검증을 통과할 때만 추정합니다. 원관측·추정·미해결을 구분해 저장합니다.':'보충값은 다른 날짜의 온도입니다. 대상·보충 영상을 아래에서 선택하면 출처와 남은 결측을 함께 저장합니다.'}</p>}</fieldset>}
   <label htmlFor="processing-method">서버 지원 처리 방법</label><select id="processing-method" value={method.id} onChange={e=>{setChoice(e.target.value);setPolygon(false);}}>{methods.map(m=><option value={m.id} key={m.id}>{m.label}</option>)}</select>
   {method.inputs?.thermal_qa&&!['thermal_gapfill','thermal_ml'].includes(method.id)&&scenes[0]&&<p>이번 실행은 {scenes[0].datetime?.slice(0,10)} (UTC) 한 촬영 시점의 지표면 온도입니다. 검색 기간 {start}–{end}의 월평균이나 기간 평균을 계산하지 않습니다.</p>}
   <details className="collection-help"><summary>지원 제품·처리 한도·주의사항</summary>
   <p>허용 제품: {method.providers.join(' · ')} / {method.collections.join(' · ')} · 입력 {method.minimum_scenes}–{method.maximum_scenes}개 · QA {method.required_qa.join(' · ')} · {method.qa_policy_version}</p>
   <p>최대 {method.spatial.maximum_aoi_km2} km² / {method.spatial.maximum_grid_pixels.toLocaleString()}셀 · {method.spatial.resolution_by_collection?.[scenes[0]?.collection]||method.spatial.resolution_m}m 격자 · {method.spatial.tile_edge?'고정 격자에서 제한 타일 처리':'제한된 AOI window 처리'}. 한도 초과 시 범위 축소가 필요하며 자동 변경하지 않습니다.</p>
   {method.caveats?.map(note=><p key={note}>{note}</p>)}</details>
   <ResearchGuide method={method}/>
   {scenes.map(scene=>{const product=method.products?.find(p=>p.provider_id===scene.provider_id&&p.collection===scene.collection);return product&&<details key={sceneKey(scene)}><summary>이 장면의 제품·필수 밴드/QA 확인</summary><p>{product.product} · {product.native_resolution} · 출력 {product.resolution_m}m · 검토 {product.checked_on}</p><p>필수: {product.required_keys.join(' · ')}. 다운로드 완료 기록과 서버 읽기 성공은 별개입니다.</p><button type="button" onClick={()=>session?.setBands(sceneKey(scene),product.required_keys.filter(k=>scene.download_assets?.some(a=>a.key===k)))}>카탈로그 필수 밴드 선택</button>{product.required_keys.map(key=><label className="workflow-check" key={key}><input type="checkbox" checked={selectedBands(scene,session?.bands||{}).includes(key)} onChange={e=>{const keys=selectedBands(scene,session?.bands||{});session?.setBands(sceneKey(scene),e.target.checked?Array.from(new Set([...keys,key])):keys.filter(k=>k!==key));}}/>{key}{!scene.download_assets?.some(a=>a.key===key)&&' · 메타데이터 미제공/실행 불가'}</label>)}</details>;})}
   {method.inputs?.threshold&&<fieldset><legend>사용자 기준 확인 · 자동 임계값 없음</legend><label htmlFor="product-threshold">{method.inputs.threshold_unit==='degC'?'고온 기준 (섭씨)':'수역 후보 MNDWI 임계값 (-1~1)'}</label><input id="product-threshold" type="number" step="0.01" value={controls.threshold??''} onChange={e=>update({threshold:e.target.value})}/><label htmlFor="threshold-basis">임계값 근거·확인 내용</label><input id="threshold-basis" maxLength={300} value={controls.basis??''} onChange={e=>update({basis:e.target.value})}/><p>{method.inputs.threshold_unit==='degC'?'입력한 섭씨 기준보다 높은 유효 지표면 온도 픽셀만 표시합니다. 기온이나 보편적 고온 분류 기준이 아닙니다.':'입력값보다 큰 유효 픽셀만 수역 후보입니다. 기준 ±0.05의 면적 민감도를 함께 출력하며 현장 검증이나 침수 확정은 아닙니다.'}</p></fieldset>}
   {method.inputs?.thermal_qa&&<fieldset><legend>온도 QA 운영 기준 · 보편적 정확도 보장 아님</legend><label htmlFor="maximum-uncertainty">허용 ST 불확실성 상한 (K)</label><input id="maximum-uncertainty" type="number" step="0.1" min="0.1" max="20" value={controls.maximum_uncertainty_k??'2'} onChange={e=>update({maximum_uncertainty_k:e.target.value})}/><label htmlFor="minimum-cloud-distance">구름으로부터 최소 거리 (km)</label><input id="minimum-cloud-distance" type="number" step="0.1" min="0" max="10" value={controls.minimum_cloud_distance_km??'1'} onChange={e=>update({minimum_cloud_distance_km:e.target.value})}/><details className="collection-help"><summary>QA 기준의 의미</summary><p>기본 제안값은 2K/1km입니다. 입력값을 계획에 적용하며 정확도 보장은 아닙니다. ST_QA와 CDIST 원자료로 검사합니다.</p></details></fieldset>}
   {!!method.inputs?.comparison_regions&&<fieldset><legend>동일 관측의 확정 비교 영역 두 개 · 서로 겹치지 않고 AOI 내부</legend>{regions.map((row,i)=><fieldset key={i}><legend>비교 영역 {i+1}</legend><label>영역 {i+1} 이름<input value={labels[i]} maxLength={80} onChange={e=>update({labels:labels.map((v,k)=>k===i?e.target.value:v),regionsConfirmed:false})}/></label>{row.map((value,j)=><label key={j}>영역 {i+1} {['서','남','동','북'][j]}<input type="number" step="0.00001" value={value} onChange={e=>update({regions:regions.map((r,k)=>k===i?r.map((v,l)=>l===j?e.target.value:v):r),regionsConfirmed:false})}/></label>)}</fieldset>)}<label className="workflow-check"><input type="checkbox" checked={!!controls.regionsConfirmed} onChange={e=>update({regionsConfirmed:e.target.checked})}/>두 비교 영역과 이름을 직접 확인했습니다</label></fieldset>}
   {method.maximum_scenes>1&&method.minimum_scenes===1&&<label className="workflow-check"><input type="checkbox" checked={pairMode} onChange={e=>setPairMode(e.target.checked)}/>현재 비교 쌍으로 품질 확인</label>}
   {usePair&&[0,1].map(i=><div key={i}><label htmlFor={'processing-scene-'+i}>공통 처리 영상 {i+1}{['thermal_gapfill','thermal_ml'].includes(method.id)?(i===0?' · 대상 날짜':method.id==='thermal_ml'?' · 참조 날짜':' · 보충 날짜'):''}</label><select id={'processing-scene-'+i} value={pair[i]} onChange={e=>{const next=[...pair] as [string,string];next[i]=e.target.value;onPair(next);}}><option value="">영상 선택</option>{items.map(s=><option key={sceneKey(s)} value={sceneKey(s)}>{s.datetime?.slice(0,10)} · {s.platform} · {s.id}</option>)}</select></div>)}
   {boundary?.id&&method.spatial.polygon&&<label className="workflow-check"><input type="checkbox" checked={polygon} onChange={e=>setPolygon(e.target.checked)}/>등록 행정경계를 실제 통계·클리핑 범위로 확정: {boundary.name} ({boundary.year})</label>}
   <p>분석 범위: {polygon?'확정 등록 polygon · 서버 원본 경계 재검증':'확정 bbox · 행정경계 밖을 포함할 수 있음'} · {bbox?.join(', ')||'AOI 미확정'}</p>
   {!eligible&&<p className="warning">{method.unsupported_reason} 입력 장면 수·선택 제품도 확인하세요.</p>}
   {!confirmed&&<p>먼저 위에서 세부 분석 의도를 확인하세요.</p>}
   {!parametersReady&&<p role="status">이 분석에 필요한 사용자 기준/비교 영역을 먼저 확인하세요.</p>}
   <button type="button" disabled={busy||quotaWait||!confirmed||!aoiConfirmed||!bbox||!eligible||!parametersReady||job?.status==='running'||job?.status==='queued'} onClick={()=>void makePlan()}>{busy?'서버 검사 중…':'공통 처리 계획 검사'}</button>
  </>}
  {error&&<p role="alert">{error}</p>}
  {unavailable&&<button type="button" onClick={()=>{setError('');setLookup(v=>v+1);}}>작업·보관 상태 다시 확인</button>}
  {job?.status==='failed'&&<><ProcessingFailure job={job} stale={savedJob?.context!==context} now={now}/>{savedJob?.context===context&&job.failure?.code!=='transfer_quota'&&!usePair&&alternatives.length>0&&<div><label htmlFor="alternative-scene">같은 검색에서 다른 촬영일 선택</label><select id="alternative-scene" value="" onChange={e=>{if(e.target.value)onSelect(e.target.value);}}><option value="">촬영일을 선택하세요 · 품질 미검사 후보</option>{alternatives.map(s=><option key={sceneKey(s)} value={sceneKey(s)}>{s.datetime?.slice(0,10)} · {s.platform} · {s.id}</option>)}</select><p>AOI·검색 기간·QA 기준은 유지합니다. 장면만 바꾸며 처리 계획과 실행은 직접 확인합니다.</p></div>}</>}
  {plan&&<div role="status"><p>계획 확인 대기 · 원본 상태: {plan.source_access} · 실제 타일 {plan.grid.tile_count}개 / {plan.grid.width}×{plan.grid.height}</p><p>{plan.notice}</p>{plan.grid.maximum_transfer_bytes&&<p>전체 입력 전송 상한 {(plan.grid.maximum_transfer_bytes/1024**2).toFixed(0)} MiB · 작업 {plan.grid.maximum_seconds}초 · 결과 ZIP 최대 {(Number(plan.grid.maximum_output_bytes)/1024**2).toFixed(0)} MiB. 타일 실패는 전체 작업 실패이며 AOI를 줄이지 않습니다.</p>}<p>필수 산출물: {plan.expected_artifacts.join(' · ')}</p><label className="workflow-check"><input type="checkbox" checked={checked} onChange={e=>setChecked(e.target.checked)}/>현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다</label><button type="button" disabled={!checked||busy} onClick={()=>void startJob()}>확인한 계획 실행</button></div>}
  {job&&<div data-testid="processing-job"><p role="status">작업 {job.status} · {job.stage}</p>{savedJob?.context!==context&&<p className="warning">이전 조건의 작업입니다. 현재 지도/분석에 자동 적용하지 않습니다.</p>}{job.error&&<p role="alert">{job.error}</p>}{['queued','running'].includes(job.status)&&<button onClick={()=>void cancel()}>공통 작업 취소</button>}{job.artifact&&<><strong>{job.artifact.filename}</strong><p>GeoTIFF·마스크·manifest 디스크 재열기/해시 검증 완료 · {job.artifact.bytes.toLocaleString()} bytes</p><p>서버 파일: {unavailable?'조회 불가':job.retention?.state||'보관 상태 미확인'} · {seconds===null?'만료 시각 미제공':`남은 보관 ${seconds}초 · 만료 ${new Date(expiry!).toLocaleString('ko-KR')}`}</p><button disabled={!downloadable||receiving} onClick={()=>void receive()}>{receiving?'처리 ZIP 수신 중…':savedJob?.context!==context?'이전 조건의 처리 ZIP 다운로드':'검증된 처리 ZIP 다운로드'}</button></>}<details className="collection-help"><summary>작업 보관·복원 안내</summary><p>같은 브라우저 소유 작업 · 로컬 단일 서버에 검증 파일과 설정을 보관합니다. 재시작 후에도 같은 쿠키·작업 ID로 조회하며 자동 재실행하지 않습니다. 쿠키·파일 보관 만료 후에는 복원할 수 없습니다.</p></details><ProcessingOutcome job={job} stale={savedJob?.context!==context}/></div>}
  {download&&<p role={downloadFailed?'alert':'status'}>{download}</p>}
  {job&&['succeeded','failed','cancelled'].includes(job.status)&&<ResearchRecord job={job} stale={savedJob?.context!==context}/>}
  {downloadFailed&&downloadable&&<button type="button" disabled={receiving} onClick={()=>void receive()}>처리 결과 다운로드 다시 시도</button>}
  {job?.status==='succeeded'&&savedJob?.context===context&&job.result&&'statistics' in job.result&&<details><summary>실제 계산 통계·기준 민감도·QA</summary><pre>{JSON.stringify({analysis:job.result.analysis_label,statistics:job.result.statistics,sensitivity:job.result.threshold_sensitivity,qa:job.result.qa_policy},null,2)}</pre></details>}
 </section>;
}
