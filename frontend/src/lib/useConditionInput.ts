'use client';
import {useCallback,useEffect,useRef,useState} from 'react';
import {post} from './api';
import {readConditionSnapshot,type ConditionPhase,type ConditionSnapshot} from './conditionSnapshot';
import type {Bbox,CameraLocation,ConditionProposals,InterpretationConfig,WorkflowInterpretation,Purpose,PlaceProposal,PlaceConfig,BoundaryProposal,PlaceCandidate,RequestIntent} from './types';
type Origin='default'|'auto'|'manual';
type Coordinates=[string,string,string,string];
type Scalar='start'|'end'|'purposeType'|'temporalMode'|'observationNeed'|'targetSize'|'resolution'|'cloud'|'referenceDate'|'analysisTarget';
export interface FormConditions {
 intent?:RequestIntent;
 start:string;end:string;coordinates:Coordinates;confirmed:boolean;boundary:BoundaryProposal|null;
 purposeType:Purpose;temporalMode:'single'|'change'|'unspecified';observationNeed:string;targetSize:string;
 resolution:string;cloud:string;referenceDate:string;analysisTarget:string;
 origins:Record<Scalar,Origin>&{coordinates:[Origin,Origin,Origin,Origin]};
}
export function coordinateBounds(values:readonly string[]):Bbox|null{
 if(values.some(v=>!v.trim()))return null;
 const b=values.map(Number) as Bbox;
 return b.every(Number.isFinite)&&b[0]>=-180&&b[0]<b[2]&&b[2]<=180&&b[1]>=-80&&b[1]<b[3]&&b[3]<=80&&b[2]-b[0]<=5&&b[3]-b[1]<=5?b:null;
}
const scalars:Scalar[]=['start','end','purposeType','temporalMode','observationNeed','targetSize','resolution','cloud','referenceDate','analysisTarget'];
const emptyValue=(key:Scalar)=>key==='temporalMode'||key==='observationNeed'?'unspecified':'';
const initial=():FormConditions=>({start:'',end:'',coordinates:['','','',''],confirmed:false,boundary:null,purposeType:'',temporalMode:'unspecified',observationNeed:'unspecified',targetSize:'',resolution:'',cloud:'',referenceDate:'',analysisTarget:'',origins:{...Object.fromEntries(scalars.map(k=>[k,'default'])) as Record<Scalar,Origin>,coordinates:['default','default','default','default']}});
const normalize=(s:string)=>s.trim(); // request identity only
export const originLabel=(s:Origin)=>s==='auto'?'자동 설정':s==='manual'?'직접 수정':'미지정';
const fieldKeys:Partial<Record<Scalar,string>>={purposeType:'purpose_type',temporalMode:'temporal_mode',observationNeed:'observation_need',targetSize:'target_size_m',resolution:'resolution_m',cloud:'max_cloud_cover',referenceDate:'reference_date',analysisTarget:'analysis_target'};
function proposedValues(p:ConditionProposals){
 const values:Partial<Record<Scalar,{value:string;explicit:boolean}>>={};
 if(p.period.status==='resolved'&&p.period.start&&p.period.end){values.start={value:p.period.start,explicit:true};values.end={value:p.period.end,explicit:true};}
 for(const [key,field] of Object.entries(fieldKeys)){
  const v=p.fields?.[field];if(v&&v.value!==null&&v.basis!=='unspecified')values[key as Scalar]={value:String(v.value),explicit:v.basis==='explicit'};
 }
 return values;
}
const regionBox=(r:PlaceProposal):Bbox|null=>r.extent_requires_confirmation?null:r.extent?.bbox||(r.boundary?.status==='proposed'?r.boundary.bbox||null:null);
export function useConditionInput(purpose:string,onChanged:()=>void){
 const [form,setForm]=useState(initial),current=useRef(form),changed=useRef(onChanged);changed.current=onChanged;
 const [proposal,setProposal]=useState<ConditionProposals|null>(null),proposalRef=useRef(proposal);proposalRef.current=proposal;
 const [phase,setPhase]=useState<ConditionPhase>('idle'),[error,setError]=useState('');
 const [aiConfig,setAiConfig]=useState<InterpretationConfig|null>(null),[placeConfig,setPlaceConfig]=useState<PlaceConfig|null>(null);
 const aiConfigRef=useRef(aiConfig);aiConfigRef.current=aiConfig;
 const [location,setLocation]=useState<PlaceProposal|null>(null),[camera,setCamera]=useState<CameraLocation|null>(null),[locating,setLocating]=useState(false);
 const [composing,setComposing]=useState(false),composition=useRef(false),[placeComposing,setPlaceComposing]=useState(false),placeIME=useRef(false);
 const [placeInput,setPlaceInput]=useState(''),placeText=useRef(''),[radius,setRadius]=useState('');
 const text=useRef(purpose),edited=useRef(false),generation=useRef(0),viewRevision=useRef(0);
 const aiAbort=useRef<AbortController|null>(null),geoAbort=useRef<AbortController|null>(null),timer=useRef<ReturnType<typeof setTimeout>|null>(null);
 const cache=useRef(new Map<string,{value:ConditionProposals;expires:number}>()),completed=useRef(''),inflight=useRef(''),recent=useRef<number[]>([]);
 const [ack,setAck]=useState(''),[manualSentence,setManualSentence]=useState<string|null>(null);
 const displayedRegion=useRef<{query:string;region:PlaceProposal;expires:number}|null>(null);
 function commit(next:FormConditions){const old=current.current;current.current=next;setForm(next);if(JSON.stringify(next)!==JSON.stringify(old))changed.current();}
 function setCurrentProposal(p:ConditionProposals|null){proposalRef.current=p;setProposal(p);}
 useEffect(()=>{const c=new AbortController();void Promise.all([
  fetch('/api/request/config',{signal:c.signal,cache:'no-store'}).then(r=>r.ok?r.json():null).then(v=>{if(!c.signal.aborted)setAiConfig(v);}),
  fetch('/api/places/config',{signal:c.signal,cache:'no-store'}).then(r=>r.ok?r.json():null).then(v=>{if(!c.signal.aborted)setPlaceConfig(v);}),
 ]).catch(()=>{});return()=>c.abort();},[]);
 const apply=useRef<(p:ConditionProposals,force?:boolean,move?:boolean)=>void>(()=>{});
 apply.current=(p,force=false,move=true)=>{
  if(p.status==='failed'||p.engine?.mode!=='ai')return;
  const old=current.current,next={...old,origins:{...old.origins}};
  const detail=p.fields?.detail_intent;
  next.intent={summary:p.request_summary||'',detail:typeof detail?.value==='string'?detail.value:null,evidence:detail?.evidence||null,basis:detail?.basis||'unspecified',domains:p.domain_candidates||[]};
  for(const [k,v] of Object.entries(proposedValues(p)) as [Scalar,{value:string;explicit:boolean}][]){
   if(force||v.explicit&&old.origins[k]!=='manual'){(next as unknown as Record<string,unknown>)[k]=v.value;next.origins[k]='auto';}
  }
  if(next.start&&next.end&&next.start>next.end){next.start=old.start;next.end=old.end;next.origins.start=old.origins.start;next.origins.end=old.origins.end;}
  // Language/lookup never owns the analysis AOI. Only an explicitly chosen
  // gazetteer candidate can move the camera; manual AOI remains untouched.
  commit(next);
 };
 const lookup=useRef<(p:ConditionProposals,sentence:string,version:number,view:number,explicit?:string,selected?:PlaceCandidate)=>Promise<void>>(async()=>{});
 lookup.current=async(p,sentence,version,view,explicit,selected)=>{
  const mentions=explicit?[{text:explicit,ambiguous:false,kind:'administrative' as const,basis:'explicit' as const,radius_m:null}]:p.extraction?.places?.length?p.extraction.places:selected&&p.region.mentioned_text?[{text:p.region.mentioned_text,kind:'administrative' as const,basis:'explicit' as const,ambiguous:false,radius_m:null}]:[];
  if(!mentions.length)return;
  if(mentions.length>1&&!selected){setCurrentProposal({...p,region:{status:'ambiguous',mentioned_text:mentions.map(v=>v.text).join(' / '),message:'분석할 한 지역을 선택하세요.',candidates:mentions.map(v=>({id:'query:'+v.text,name:v.text,query:v.text}))}});return;}
  const mention=mentions[0],query=mention.text,lookupKey=JSON.stringify([query,mention.kind,mention.radius_m]);
  geoAbort.current?.abort();const abort=new AbortController();geoAbort.current=abort;setLocating(true);
  setCurrentProposal({...p,region:{status:'loading',mentioned_text:query,message:'실제 위치 검색 중'}});
  try{
   let r:PlaceProposal;
   if(selected)r={...selected,status:'resolved',mentioned_text:query};
   else if(displayedRegion.current?.query===lookupKey&&displayedRegion.current.expires>Date.now())r=displayedRegion.current.region;
   else r=await post<PlaceProposal>('places/search',{place:query,kind:mention.kind||'administrative',radius_m:mention.basis==='explicit'?mention.radius_m||null:null},AbortSignal.any([abort.signal,AbortSignal.timeout(9000)]));
   if(version!==generation.current||abort.signal.aborted||sentence!==normalize(text.current))return;
   if(r.status==='resolved'&&!selected&&!regionBox(r))r={...r,status:'ambiguous',candidates:r.candidates?.length?r.candidates:r.id&&r.name?[r as PlaceCandidate]:[],message:'지명 후보와 상위 지역을 선택하세요. 범위가 없으면 지도만 이동합니다.'};
   if('spatial_scope' in mention&&mention.spatial_scope==='unspecified'&&r.status==='resolved')r={...r,extent_requires_confirmation:true,message:'장소는 확인했으나 문장의 공간 범위가 미지정입니다. 행정구역 전체인지 주변 거리인지 확인하세요.'};
   displayedRegion.current={query:lookupKey,region:r,expires:Date.now()+60000};
   const next={...p,region:r};setCurrentProposal(next);
   if(r.status==='resolved'&&view===viewRevision.current){
    setLocation(r);placeText.current=r.name||query;setPlaceInput(placeText.current);if(r.id&&r.name&&r.center)setCamera({id:r.id,name:r.name,center:r.center,token:Date.now()});
    const box=regionBox(r),old=current.current;
    if(box&&!old.origins.coordinates.includes('manual'))commit({...old,coordinates:box.map(String) as Coordinates,confirmed:false,boundary:r.boundary?.status==='proposed'?r.boundary:null,origins:{...old.origins,coordinates:['auto','auto','auto','auto']}});
   }
  }catch(e){if(version===generation.current&&!abort.signal.aborted)setCurrentProposal({...p,region:{status:e instanceof Error&&e.name==='TimeoutError'?'timeout':'failed',mentioned_text:query,message:'위치 검색 실패. 임의 좌표로 대체하지 않습니다. 재시도하거나 직접 AOI를 지정하세요.'}});}
  finally{if(version===generation.current)setLocating(false);}
 };
 const run=useCallback(async(_regionId?:string,_legacyMode?:'rules'|'ai',retry=false)=>{
  const sentence=normalize(text.current);if(!sentence||composition.current||placeIME.current||!edited.current)return;
  if(timer.current)clearTimeout(timer.current);
  if(inflight.current===sentence||!retry&&completed.current===sentence)return;
  aiAbort.current?.abort();geoAbort.current?.abort();const version=++generation.current,view=viewRevision.current;
  const abort=new AbortController();aiAbort.current=abort;inflight.current=sentence;setLocating(false);setManualSentence(null);setPhase('loading');setError('');setCurrentProposal(null);setAck('');
  try{
   let p:ConditionProposals;const saved=cache.current.get(sentence);
   if(saved&&saved.expires>Date.now())p={...saved.value,engine:{...saved.value.engine!,status:'cached_local'}};
   else{
    recent.current=recent.current.filter(t=>Date.now()-t<60000);
    const minuteLimit=aiConfigRef.current?.limits.requests_per_minute||6;
    if(recent.current.length>=minuteLimit)throw new Error(`화면의 AI 요청 상한(분당${minuteLimit}회)입니다. 잠시 후 재시도하거나 직접 입력하세요.`);
    recent.current.push(Date.now());
    const deadline=(Math.min(90,Math.max(10,aiConfigRef.current?.limits.timeout_seconds||45))+5)*1000;
    const result=await post<WorkflowInterpretation>('request/interpret',{purpose:sentence,resolve_conditions:true,interpretation_mode:'ai'},AbortSignal.any([abort.signal,AbortSignal.timeout(deadline)]));
    if(!result.condition_proposals)throw new Error('최신 AI 조건 API 응답이 없습니다. 서버 버전을 확인하세요.');
    p=result.condition_proposals;
    if(p.engine?.mode!=='ai'||p.status!=='failed'&&!p.fields)throw new Error('AI 전용 조건 계약이 아닌 응답을 차단했습니다. 규칙 결과로 대체하지 않습니다.');
    if(p.status!=='failed'){if(cache.current.size>=16)cache.current.delete(cache.current.keys().next().value!);cache.current.set(sentence,{value:p,expires:Date.now()+600000});}
   }
   if(version!==generation.current||abort.signal.aborted||sentence!==normalize(text.current))return;
   setCurrentProposal(p);if(p.engine?.usage)setAiConfig(c=>c?{...c,usage:p.engine!.usage!}:c);
   if(p.status==='failed'){setPhase('failed');setError(p.messages.join(' '));return;}
   apply.current(p,false,view===viewRevision.current);await lookup.current(p,sentence,version,view);
   if(version===generation.current){completed.current=sentence;setPhase('ready');}
  }catch(e){if(version===generation.current&&!abort.signal.aborted){setPhase('failed');setCurrentProposal(null);setError(e instanceof Error&&e.name==='TimeoutError'?'AI 해석 응답 시간 상한입니다. 직접 입력 또는 재시도를 선택하세요.':e instanceof Error?e.message:'AI 해석 실패. 규칙 대체 없음.');}}
  finally{if(version===generation.current)inflight.current='';}
 },[]);
 function invalidateInput(){generation.current++;aiAbort.current?.abort();geoAbort.current?.abort();inflight.current='';completed.current='';setLocating(false);setAck('');setManualSentence(null);if(timer.current)clearTimeout(timer.current);}
 function editText(value:string){
  edited.current=true;if(normalize(value)===normalize(text.current))return;
  text.current=value;invalidateInput();const old=current.current,next={...old,origins:{...old.origins}};
  next.intent=undefined;
  for(const key of scalars)if(old.origins[key]==='auto'){(next as unknown as Record<string,unknown>)[key]=emptyValue(key);next.origins[key]='default';}
  if(!old.origins.coordinates.includes('manual')){next.coordinates=['','','',''];next.confirmed=false;next.boundary=null;next.origins.coordinates=['default','default','default','default'];}
  commit(next);setLocation(null);placeText.current='';setPlaceInput('');setCamera(null);setCurrentProposal(null);setPhase('idle');setError('');
 }
 useEffect(()=>{text.current=purpose;if(!purpose.trim()||composing||!edited.current)return;timer.current=setTimeout(()=>void run(),1200);return()=>{if(timer.current)clearTimeout(timer.current);};},[purpose,composing,run]);
 useEffect(()=>()=>{generation.current++;aiAbort.current?.abort();geoAbort.current?.abort();if(timer.current)clearTimeout(timer.current);},[]);
 function manualField(key:Scalar,value:string){commit({...current.current,[key]:value,origins:{...current.current.origins,[key]:'manual'}});}
 function manualCoordinate(i:number,value:string){viewRevision.current++;const old=current.current,c=[...old.coordinates] as Coordinates,o=[...old.origins.coordinates] as FormConditions['origins']['coordinates'];c[i]=value;o[i]='manual';commit({...old,coordinates:c,confirmed:false,boundary:null,origins:{...old.origins,coordinates:o}});}
 function manualBbox(b:Bbox,confirmed=true){viewRevision.current++;commit({...current.current,coordinates:b.map(String) as Coordinates,confirmed,boundary:null,origins:{...current.current.origins,coordinates:['manual','manual','manual','manual']}});}
 const conflicts:string[]=[];
 if(proposal?.status!=='failed'&&proposal){for(const [key,v] of Object.entries(proposedValues(proposal)) as [Scalar,{value:string;explicit:boolean}][]){if(v.value!==form[key]&&(!v.explicit||form.origins[key]==='manual'))conflicts.push(key+': 직접/미확정 '+(form[key]||'미지정')+' / 문장 '+v.value+(v.explicit?'':' (AI 추론)'));}
 }
 const conflictKey=JSON.stringify([normalize(purpose),conflicts]),acknowledged=ack===conflictKey;
 const regionNeeds=proposal?.extraction?.places?.length&&proposal.region.status!=='resolved';
 const manual=manualSentence===normalize(purpose);
 const pending=!!purpose.trim()&&(phase==='idle'||phase==='loading'||locating);
 const coreMissing=!!purpose.trim()&&(!form.purposeType||!form.start||!form.end);
 const blocking=coreMissing||!!purpose.trim()&&!manual&&(pending||phase==='failed'||phase==='interrupted'||!!regionNeeds||conflicts.length>0&&!acknowledged||!!proposal?.event_reference_required&&!form.referenceDate||proposal?.period.status==='needs_confirmation'&&!(form.origins.start==='manual'&&form.origins.end==='manual'));
 const directLookup=(value=placeText.current)=>{
  if(!value.trim()||composition.current||placeIME.current)return;
  if(timer.current)clearTimeout(timer.current);
  geoAbort.current?.abort();const version=++generation.current;aiAbort.current?.abort();inflight.current='';setPhase('ready');
  const p=proposalRef.current||{status:'partial',period:{status:'absent'},region:{status:'absent'},messages:[],event_reference_required:false,scope:'직접 입력한 지명',fields:{},engine:{mode:'ai',status:'not_called',provider:null,model:null}} as ConditionProposals;
  void lookup.current(p,normalize(text.current),version,viewRevision.current,value.trim());
 };
 return {form,bbox:coordinateBounds(form.coordinates),aoiConfirmed:form.confirmed&&!blocking,blocking,pending,composing:composing||placeComposing,proposal,phase,error,conflicts:acknowledged?[]:conflicts,camera,location,locating,aiConfig,placeConfig,placeInput,radius,
  snapshot:{version:1,sentence:normalize(purpose),phase,proposal,error,manual,ack} as ConditionSnapshot,
  restore:(saved:FormConditions,sentence:string,savedLocation?:PlaceProposal|null,validated=false,savedInterpretation?:unknown)=>{
   generation.current++;aiAbort.current?.abort();geoAbort.current?.abort();if(timer.current)clearTimeout(timer.current);
   edited.current=false;text.current=sentence;current.current=saved;setForm(saved);inflight.current='';completed.current='';setLocating(false);setLocation(savedLocation||null);placeText.current=savedLocation?.name||'';setPlaceInput(placeText.current);
   const state=readConditionSnapshot(savedInterpretation,sentence);
   if(state){
    let p=state.proposal;
    // Completed AI extraction is reusable even if location lookup was interrupted.
    if(p?.region.status==='loading')p={...p,region:{...p.region,status:'failed',message:'위치 확인 중 화면을 벗어났습니다. 위치 검색만 다시 시도하세요. AI 재해석은 필요하지 않습니다.'}};
    const interrupted=!!sentence.trim()&&!state.manual&&['idle','loading','interrupted','ready'].includes(state.phase)&&!p;
    setCurrentProposal(p);setManualSentence(state.manual?normalize(sentence):null);setAck(state.ack);
    setPhase(interrupted?'interrupted':p?.status==='failed'?'failed':p&&state.phase==='loading'?'ready':state.phase);
    setError(interrupted?'이전 해석의 완료 결과가 저장되지 않았습니다. 자동 재전송하지 않습니다. AI 재시도 또는 직접 입력을 선택하세요.':state.error);
    if(p&&p.status!=='failed'){completed.current=normalize(sentence);cache.current.set(normalize(sentence),{value:p,expires:Date.now()+600000});}
   }else{
    const legacyValidated=validated&&savedInterpretation==null;
    setManualSentence(legacyValidated?normalize(sentence):null);setCurrentProposal(null);setAck('');
    setPhase(legacyValidated||!sentence.trim()?'ready':'interrupted');setError(!legacyValidated&&sentence.trim()?'이전 해석 결과·오류 상세가 저장되지 않은 기록입니다. 실패 원인은 미확인입니다. 자동 재전송하지 않으며 AI 재시도 또는 직접 입력을 선택하세요.':'');
   }
  },
  boundaryProposal:null,
  newAoi:()=>{viewRevision.current++;commit({...current.current,confirmed:false});},
  run,editText,manualField,manualDate:(k:'start'|'end',v:string)=>manualField(k,v),manualCoordinate,manualBbox,
  manualPurposeType:(v:Purpose)=>manualField('purposeType',v),manualTemporalMode:(v:FormConditions['temporalMode'])=>manualField('temporalMode',v),
  compositionStart:()=>{composition.current=true;setComposing(true);invalidateInput();setPhase('idle');},
  compositionEnd:(v:string)=>{text.current=v;edited.current=true;composition.current=false;setComposing(false);},
  editPlaceInput:(v:string)=>{placeText.current=v;setPlaceInput(v);geoAbort.current?.abort();generation.current++;setLocating(false);},
  lookupDirect:()=>directLookup(),retryDirect:()=>{displayedRegion.current=null;directLookup();},
  placeCompositionStart:()=>{placeIME.current=true;setPlaceComposing(true);geoAbort.current?.abort();generation.current++;},placeCompositionEnd:(v:string)=>{placeText.current=v;setPlaceInput(v);placeIME.current=false;setPlaceComposing(false);},
  setRadius:(v:string)=>setRadius(v),
  applyRadius:()=>{const p=proposalRef.current;if(!p?.extraction?.places?.length||!Number.isFinite(Number(radius))||Number(radius)<=0)return;const next={...p,extraction:{...p.extraction,places:p.extraction.places.map(v=>({...v,radius_m:Number(radius),spatial_scope:'radius' as const,basis:'explicit' as const}))}};displayedRegion.current=null;void lookup.current(next,normalize(text.current),++generation.current,viewRevision.current);},
  chooseRegion:(id:string)=>{const p=proposalRef.current,c=p?.region.candidates?.find(v=>v.id===id);if(!p||!c)return;if(c.query){void lookup.current({...p,extraction:{...p.extraction!,places:p.extraction?.places?.filter(v=>v.text===c.query)}},normalize(text.current),++generation.current,viewRevision.current);}else void lookup.current(p,normalize(text.current),++generation.current,viewRevision.current,p.region.mentioned_text||undefined,c);},
  retryLocation:()=>{displayedRegion.current=null;if(proposalRef.current)void lookup.current(proposalRef.current,normalize(text.current),++generation.current,viewRevision.current);},
  reapply:()=>{if(proposalRef.current){const p={...proposalRef.current,region:{...proposalRef.current.region,extent_requires_confirmation:false}};setCurrentProposal(p);apply.current(p,true);setAck('');}},keepManual:()=>setAck(conflictKey),
  useManual:()=>{generation.current++;if(timer.current)clearTimeout(timer.current);edited.current=false;aiAbort.current?.abort();geoAbort.current?.abort();inflight.current='';setLocating(false);setPhase('ready');setManualSentence(normalize(text.current));},manualMode:manual,
  showAI:()=>{edited.current=false;setManualSentence(null);setPhase(proposalRef.current?.status==='failed'?'failed':proposalRef.current?'ready':text.current.trim()?'interrupted':'idle');if(!proposalRef.current&&text.current.trim()&&!error)setError('문장을 확인한 뒤 AI 해석 재시도를 누르세요. 자동 전송하지 않습니다.');},
  confirmAoi:()=>{if(coordinateBounds(current.current.coordinates))commit({...current.current,confirmed:true});},manualCamera:()=>{viewRevision.current++;},
  refreshAI:()=>void fetch('/api/request/config',{cache:'no-store'}).then(r=>r.json()).then(setAiConfig).catch(()=>{}),runAI:()=>{edited.current=true;void run(undefined,'ai',true);},
  cancel:()=>{invalidateInput();setPhase('failed');setError('AI 해석을 취소했습니다. 기존 직접 입력값을 유지합니다.');},
 };
}
