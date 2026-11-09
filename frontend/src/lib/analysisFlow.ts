import type {AnalysisTask,Bbox,Purpose,Scene} from './types';
import {sceneKey} from './types';


// Presentation capabilities only: reuse the catalog and existing product gate.
// Acquisition, metadata and server pixel checks still control every execution.
export function processingCapabilities(task:AnalysisTask|null,scene:Scene|null,purpose:Purpose){
 const methods=task?.execution?.methods||[];
 const primary=methods.find(m=>m.engine===task?.engine);
 const common=!!scene&&!!primary&&primary.products?.some(p=>p.provider_id===scene.provider_id&&p.collection===scene.collection&&p.levels.includes(scene.processing_level||'')&&p.platforms.includes(scene.platform||''))||false;
 const quality=!!task&&task.domain===purpose&&!!scene&&methods.filter(m=>['s2_quality','ndvi_change','observed_composite','local_ridge'].includes(m.id)).some(m=>m.providers.includes(scene.provider_id||(m.providers.length===1?m.providers[0]:''))&&m.collections.includes(scene.collection)&&m.levels.includes(scene.processing_level||''));
 const analysis=quality&&task?.engine==='ndvi_change';
 const preprocessing=quality&&!!task?.preprocessing.some(p=>p.requirement!=='unnecessary'&&p.engine);
 return {quality,analysis,preprocessing,common};
}
export type ProcessingCapabilities=ReturnType<typeof processingCapabilities>;

export function taskInputs(task:AnalysisTask|null,selected:Scene|null,items:Scene[],pair:[string,string]){
 if(!task)return [];
 return task.comparison?pair.map(k=>items.find(s=>sceneKey(s)===k)).filter((s):s is Scene=>!!s):selected?[selected]:[];
}
export function variableKey(scene:Scene,variable:string){
 const aliases=variable==='nir'?['nir','nir08']:variable==='thermal'?['thermal','lwir11']:[variable];
 return scene.download_assets?.find(a=>a.common_names.length===1&&aliases.includes(a.common_names[0])&&!a.roles.includes('visual'))?.key;
}
export function automaticTaskBands(task:AnalysisTask|null,scenes:Scene[],bands:Record<string,string[]>){
 if(!task)return bands;
 let next=bands;
 const contract=task.execution?.methods.find(m=>m.engine===task.engine);
 for(const scene of scenes){
  const product=contract?.products?.find(p=>p.provider_id===scene.provider_id&&p.collection===scene.collection&&p.levels.includes(scene.processing_level||'')&&p.platforms.includes(scene.platform||''));
  const supported=contract&&(contract.products?!!product:contract.providers.includes(scene.provider_id||'')&&contract.collections.includes(scene.collection)&&contract.levels.includes(scene.processing_level||''));
  if(!supported)continue;
  const available=new Set(scene.download_assets?.map(a=>a.key)||[]);
  const required=[...task.required_variables.map(v=>variableKey(scene,v)),...(product?.required_keys||contract.required_qa)].filter((k):k is string=>!!k&&available.has(k));
  const id=sceneKey(scene),chosen=next[id]??scene.purpose_plan?.default_keys??[];
  const added=required.filter(k=>!chosen.includes(k));
  if(added.length)next={...next,[id]:[...new Set([...chosen,...added])]};
 }
 return next;
}
export function assessTask(task:AnalysisTask|null,scenes:Scene[],bands:Record<string,string[]>,bbox:Bbox|null,start:string,end:string,resolution:number|null=null){
 const missing:string[]=[],pending=['실제 AOI 픽셀 품질·제품 기준선·보정값·파일 접근은 기존 실행 서버가 다시 검사합니다.'];
 if(!task)return {metadataReady:false,missing:['세부 분석을 선택하고 확인하세요.'],pending,engineReady:false};
 if(!bbox||!start||!end||start>end)missing.push('확정 AOI와 유효 UTC 기간이 필요합니다.');
 const unique=new Set(scenes.map(sceneKey));
 if(unique.size<task.minimum_scenes)missing.push(`필요한 서로 다른 장면 ${task.minimum_scenes}개 / 현재 ${unique.size}개. 같은 지역·기간에서 추가 수집하세요.`);
 if(task.comparison&&new Set(scenes.map(s=>s.datetime?.slice(0,10)).filter(Boolean)).size<2)missing.push('서로 다른 두 촬영일이 필요합니다. 사건일은 임의 생성하지 않습니다.');
 for(const s of scenes){
  if(!s.datetime||s.datetime.slice(0,10)<start||s.datetime.slice(0,10)>end)missing.push(`${s.id}: 촬영일 미확인 또는 허용 기간 밖입니다.`);
  if(s.overlap_percent==null||s.overlap_percent<=0)missing.push(`${s.id}: AOI 기하 중첩이 확인되지 않았습니다. 유효 픽셀률과 별개입니다.`);
  const chosen=bands[sceneKey(s)]??s.purpose_plan?.default_keys??[];
  for(const v of task.required_variables){const key=variableKey(s,v);if(!key)missing.push(`${s.id}: 필요한 ${v} Asset 미제공/미확인`);else if(!chosen.includes(key))missing.push(`${s.id}: ${key} 밴드를 수집에서 선택하세요.`);}
  const contract=task.execution?.methods.find(m=>m.engine===task.engine);
  const product=contract?.products?.find(p=>p.provider_id===s.provider_id&&p.collection===s.collection&&p.levels.includes(s.processing_level||'')&&p.platforms.includes(s.platform||''));
  if(task.engine){
   if(!contract)missing.push('서버 실행 지원 계약을 확인하지 못했습니다.');
   else {
    if(!contract.providers.includes(s.provider_id||(contract.providers.length===1?contract.providers[0]:''))||!contract.collections.includes(s.collection)||!contract.levels.includes(s.processing_level||''))missing.push(`${s.id}: 서버 카탈로그가 이 제공처·제품의 실행을 지원하지 않습니다.`);
    if(contract.products&&!product)missing.push(`${s.id}: 목적·제품별 실행 allowlist에 없습니다.`);
    for(const key of product?.required_keys||contract.required_qa)if(!s.download_assets?.some(a=>a.key===key))missing.push(`${s.id}: ${key} 필수 밴드/품질 자료 미제공·미확인`);else if(!chosen.includes(key))missing.push(`${s.id}: ${key} 필수 밴드/품질 자료를 선택하세요.`);
   }
  }
 }
 if(task.engine&&task.execution){
  const contract=task.execution.methods.find(m=>m.engine===task.engine),limits=contract?.products?contract.spatial:task.execution.legacy_spatial;
  if(limits&&resolution!=null&&resolution<limits.resolution_m)missing.push(`기존 처리 경로는 ${limits.resolution_m}m 격자입니다. 요청 해상도를 몰래 바꾸지 않습니다.`);
  if(contract?.temporal.same_platform&&new Set(scenes.map(s=>s.platform)).size>1)missing.push('서버 계약에 따라 동일 플랫폼의 장면을 선택하세요.');
  if(bbox&&limits){const area=(bbox[2]-bbox[0])*111.32*(bbox[3]-bbox[1])*111.32*Math.cos((bbox[1]+bbox[3])*Math.PI/360);if(area>limits.maximum_aoi_km2)missing.push(`기존 처리 경로는 ${limits.maximum_aoi_km2} km² 이하입니다. 공통 처리 계획에서 별도 타일/자원 조건을 확인하세요.`);}
 }
 const metadataReady=missing.length===0;
 return {metadataReady,missing:[...new Set(missing)],pending,engineReady:metadataReady&&!!task.execution?.analysis_supported};
}
