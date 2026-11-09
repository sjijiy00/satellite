import type {Scene} from './types';
import type {AccessReport} from './useProviderAccess';

type Reference=Pick<Scene,'provider_id'|'collection'|'id'>;
export type PreviewState={report:AccessReport|null;error:string;busy:boolean};
type Entry={scene:Reference;listeners:Set<(state:PreviewState)=>void>;state:PreviewState;controller?:AbortController;expires:number;bytes:number;recovered:boolean};
const entries=new Map<string,Entry>(),authListeners=new Set<()=>void>();
const TTL=90_000,MAX_ENTRIES=60,MAX_BYTES=1024*1024;
let generation=0,running=0,installed=false,sessionRevision=0;
let session:{expires:number;generation?:string}|null=null;
let preparing:Promise<void>|null=null;
let sessionController:AbortController|null=null;
export const authGeneration=()=>generation;
const key=(scene:Reference)=>JSON.stringify([scene.provider_id,scene.collection,scene.id,generation]);
const sameOriginMedia=(url:unknown,kind:string)=>typeof url==='string'&&new RegExp(`^/api/media/${kind}/[A-Za-z0-9_-]+(?:\\?download=1)?$`).test(url);
function install(){
  if(installed||typeof window==='undefined')return;
  installed=true;
  window.addEventListener('earthdata-connection-change',invalidate);
  window.addEventListener('storage',event=>{if(event.key==='satellite-auth-change'){
    let logout:'unconfirmed'|'disposed'|undefined;
    try{const value=JSON.parse(event.newValue||'null');if(value?.logout==='unconfirmed'||value?.logout==='disposed')logout=value.logout;}catch{/* Older tabs send a nonce string. */}
    invalidate();window.dispatchEvent(new CustomEvent('earthdata-external-change',{detail:{logout}}));
  }});
}
function invalidate(){
  generation++;session=null;preparing=null;sessionController?.abort();sessionController=null;
  for(const entry of entries.values())entry.controller?.abort();
  entries.clear();for(const listener of authListeners)listener();
}
export function disposalUnconfirmed(){
  install();
  try{return localStorage.getItem('satellite-earthdata-disposal-unconfirmed')==='1';}catch{return false;}
}
export function notifyAuthChange(logout?:'unconfirmed'|'disposed'){
  install();window.dispatchEvent(new Event('earthdata-connection-change'));
  try{
    if(logout==='unconfirmed')localStorage.setItem('satellite-earthdata-disposal-unconfirmed','1');
    if(logout==='disposed')localStorage.removeItem('satellite-earthdata-disposal-unconfirmed');
    localStorage.setItem('satellite-auth-change',JSON.stringify({nonce:`${Date.now()}-${Math.random()}`,...(logout?{logout}:{})}));
  }catch{/* Storage can be disabled; same-tab invalidation still applies. */}
}
export function subscribeAuth(listener:()=>void){install();authListeners.add(listener);return()=>{authListeners.delete(listener);};}
async function ready(force=false){
  if(preparing)return preparing;
  if(!force&&session&&session.expires>Date.now())return;
  const epoch=generation,controller=new AbortController();sessionController=controller;
  const pending=(async()=>{
    const response=await fetch('/api/media/session',{cache:'no-store',credentials:'same-origin',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(8000)])});
    const data=await response.json().catch(()=>null);
    if(!response.ok||data?.ready!==true)throw new Error('파일 접근 서버를 확인하세요. 미디어 세션 준비에 실패했습니다.');
    if(epoch!==generation)throw new DOMException('인증 상태 변경','AbortError');
    if(session?.generation&&data.session_generation&&session.generation!==data.session_generation){
      for(const [id,entry] of entries)if(!entry.listeners.size&&!entry.state.busy)entries.delete(id);
    }
    session={generation:typeof data.session_generation==='string'?data.session_generation:undefined,
      expires:Math.min(Date.now()+60_000,typeof data.expires_at==='number'?data.expires_at*1000-5000:Date.now()+30_000)};
    sessionRevision++;
  })();
  preparing=pending;
  try{await pending;}finally{if(preparing===pending)preparing=null;if(sessionController===controller)sessionController=null;}
}
export async function inspectMedia(scene:Reference,keys:string[],preview:boolean,signal:AbortSignal,force=false):Promise<AccessReport>{
  install();const epoch=generation;
  await ready(force);signal.throwIfAborted();
  if(epoch!==generation)throw new DOMException('인증 상태 변경','AbortError');
  for(let attempt=0;attempt<2;attempt++){
    if(epoch!==generation)throw new DOMException('인증 상태 변경','AbortError');
    const revision=sessionRevision;
    const response=await fetch('/api/media/inspect',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({provider_id:scene.provider_id,collection:scene.collection,id:scene.id,asset_keys:keys,include_preview:preview}),
      signal:AbortSignal.any([signal,AbortSignal.timeout(120000)])});
    const data=await response.json().catch(()=>null);
    if(epoch!==generation)throw new DOMException('인증 상태 변경','AbortError');
    signal.throwIfAborted();
    if(response.status===409&&data?.error?.code==='MEDIA_SESSION_REQUIRED'&&attempt===0){await ready(revision===sessionRevision);signal.throwIfAborted();continue;}
    if(!response.ok)throw new Error(data?.error?.message||`파일 접근 확인 실패 (${response.status})`);
    if(data?.reference?.provider_id!==scene.provider_id||data?.reference?.collection!==scene.collection||data?.reference?.id!==scene.id||!Array.isArray(data?.assets))throw new Error('장면 접근 응답이 일치하지 않습니다. 다시 시도하세요.');
    if(data.preview?.url&&!sameOriginMedia(data.preview.url,'previews'))throw new Error('안전한 미리보기 경로를 확인하지 못했습니다.');
    if(data.preview?.download_url&&!sameOriginMedia(data.preview.download_url,'previews'))delete data.preview.download_url;
    for(const asset of data.assets)if(asset.download_url&&!sameOriginMedia(asset.download_url,'downloads'))delete asset.download_url;
    if(data.preview?.status==='reconnection_required'||data.assets.some((a:{status:string})=>a.status==='reconnection_required'))window.dispatchEvent(new Event('earthdata-reauthorization-required'));
    return data;
  }
  throw new Error('미디어 세션을 다시 준비하지 못했습니다. 재시도하세요.');
}

// Invoked exclusively by explicit original-download / browse-save handlers.
// Receipt recovery never retries provider auth failures, partial bodies or quotas.
export type MediaDiskWriter={write:(data:Uint8Array)=>Promise<void>;close:()=>Promise<void>;abort:()=>Promise<void>};
export async function receiveMediaFile(scene:Reference,receipt:string,externalSignal:AbortSignal,options:{assetKey?:string;receiptExpiresAt?:number;onRefresh?:()=>void;writable?:MediaDiskWriter}={}){
  install();const epoch=generation,preview=options.assetKey===undefined,kind=preview?'previews':'downloads';
  const largeSar=!preview&&scene.provider_id==='copernicus'&&scene.collection==='sentinel-1-grd';
  if(largeSar&&!options.writable)throw new Error('Sentinel-1 대용량 원본은 브라우저 파일 저장 기능이 필요합니다. Chrome 또는 Edge에서 다시 시도하세요.');
  const signal=AbortSignal.any([externalSignal,AbortSignal.timeout(largeSar?26*60_000:120_000)]);
  const limit=largeSar?2*1024**3:(preview?8:256)*1024**2;
  let url=receipt,refreshed=false;
  function check(){signal.throwIfAborted();if(epoch!==generation)throw new DOMException('인증 상태 변경','AbortError');}
  async function refresh(){
    check();refreshed=true;options.onRefresh?.();
    const report=await inspectMedia(scene,preview?[]:[options.assetKey!],preview,signal,true);
    check();
    const access=preview?report.preview:report.assets.find(asset=>asset.key===options.assetKey);
    if(access?.status!=='available'||!access.download_url)throw new Error(access?.message||'파일 접근을 다시 확인하지 못했습니다. 접근 확인 후 다시 시도하세요.');
    url=access.download_url;
  }
  check();
  if(!sameOriginMedia(url,kind))throw new Error('안전한 파일 수신 경로를 확인하지 못했습니다. 접근을 다시 확인하세요.');
  if(typeof options.receiptExpiresAt==='number'&&options.receiptExpiresAt*1000<=Date.now())await refresh();
  for(let attempt=0;attempt<2;attempt++){
    check();if(!sameOriginMedia(url,kind))throw new Error('안전한 파일 수신 경로를 확인하지 못했습니다.');
    const response=await fetch(url,{credentials:'same-origin',cache:'no-store',redirect:'error',signal});
    check();
    if(!response.ok){
      const data=await response.json().catch(()=>null),detail=data?.error??data?.detail;
      const code=detail&&typeof detail==='object'?detail.code:undefined;
      const message=detail&&typeof detail==='object'?detail.message:typeof detail==='string'?detail:undefined;
      if(!refreshed&&((response.status===404||response.status===410)&&(!code||code==='MEDIA_RECEIPT_INVALID')||response.status===409&&code==='MEDIA_SESSION_REQUIRED')){
        await refresh();continue;
      }
      if(code==='reconnection_required'||code==='login_required')window.dispatchEvent(new Event('earthdata-reauthorization-required'));
      throw new Error(refreshed?`${message||'파일 수신에 실패했습니다.'} 접근 갱신은 1회만 시도했습니다. 접근 확인 후 다시 시도하세요.`:message||'파일 수신 실패. 접근 확인 후 다시 시도하세요.');
    }
    const lengthHeader=response.headers.get('content-length'),length=lengthHeader===null?null:Number(lengthHeader);
    if(length!==null&&(!Number.isSafeInteger(length)||length<=0||length>limit)){
      await response.body?.cancel();throw new Error('파일 크기가 없거나 수신 상한을 넘습니다.');
    }
    if(preview&&!/^image\/(png|jpeg|webp)(?:;|$)/i.test(response.headers.get('content-type')||'')){
      await response.body?.cancel();throw new Error('미리보기 이미지 응답을 확인하지 못했습니다. 접근 확인 후 다시 시도하세요.');
    }
    if(!response.body)throw new Error('파일 응답 본문이 없습니다. 다시 시도하세요.');
    const reader=response.body.getReader(),chunks:Uint8Array<ArrayBuffer>[]= [];let size=0;
    try{
      while(true){
        const {done,value}=await reader.read();check();if(done)break;
        size+=value.byteLength;if(size>limit)throw new Error('파일 수신 상한을 넘습니다.');
        if(options.writable)await options.writable.write(value);
        else chunks.push(new Uint8Array(value));
      }
    }catch(error){await reader.cancel().catch(()=>{});throw error;}finally{reader.releaseLock();}
    if(!size||(length!==null&&size!==length))throw new Error('파일 전체 수신을 확인하지 못했습니다. 접근 확인 후 다시 시도하세요.');
    check();
    const filename=(response.headers.get('content-disposition')?.match(/filename="([A-Za-z0-9_.-]+)"/)||[])[1];
    return {blob:options.writable?null:new Blob(chunks,{type:response.headers.get('content-type')||'application/octet-stream'}),bytes:size,filename,receipt:url};
  }
  throw new Error('접근 갱신은 1회만 시도했습니다. 접근 확인 후 다시 시도하세요.');
}
function emit(entry:Entry){for(const listener of entry.listeners)listener(entry.state);}
function prune(){
  let bytes=0;for(const entry of entries.values())bytes+=entry.bytes;
  for(const [id,entry] of entries){
    if(!entry.listeners.size&&!entry.controller&&(entry.expires<=Date.now()||entries.size>MAX_ENTRIES||bytes>MAX_BYTES)){entries.delete(id);bytes-=entry.bytes;}
  }
}
function pump(){
  prune();
  for(const [id,entry] of entries){
    if(running>=2)break;
    if(!entry.listeners.size||entry.controller||!entry.state.busy)continue;
    running++;const controller=new AbortController();entry.controller=controller;
    void inspectMedia(entry.scene,[],true,controller.signal,entry.recovered).then(report=>{
      if(controller.signal.aborted||entries.get(id)!==entry)return;
      entry.state={report,error:'',busy:false};entry.bytes=JSON.stringify(report).length*2;
      entry.expires=Math.min(Date.now()+TTL,report.preview?.receipt_expires_at?report.preview.receipt_expires_at*1000-5000:Infinity);
      emit(entry);
    }).catch(error=>{
      if(controller.signal.aborted||entries.get(id)!==entry)return;
      entry.state={report:null,error:error instanceof Error?error.message:'미리보기 접근 실패',busy:false};entry.expires=Date.now()+TTL;emit(entry);
    }).finally(()=>{running--;entry.controller=undefined;prune();pump();});
  }
}
export function subscribePreview(scene:Reference,listener:(state:PreviewState)=>void){
  install();const id=key(scene);let entry=entries.get(id);
  if(!entry||(!entry.listeners.size&&!entry.controller&&entry.expires<=Date.now())){
    entry={scene:{provider_id:scene.provider_id,collection:scene.collection,id:scene.id},listeners:new Set(),state:{report:null,error:'',busy:true},expires:0,bytes:0,recovered:false};entries.set(id,entry);
  }else if(!entry.state.busy&&entry.state.report&&entry.expires<=Date.now()&&!entry.recovered){
    entry.state={report:null,error:'',busy:true};entry.bytes=0;emit(entry);
  }
  const current=entry;current.listeners.add(listener);listener(current.state);queueMicrotask(pump);
  return()=>{
    current.listeners.delete(listener);
    // React StrictMode immediately re-subscribes; defer cancellation one microtask.
    queueMicrotask(()=>{if(!current.listeners.size){
      if(current.state.busy){current.controller?.abort();if(entries.get(id)===current)entries.delete(id);}
      prune();
    }});
  };
}
export function retryPreview(scene:Reference,receiptFailure=false){
  const entry=entries.get(key(scene));
  if(!entry||!entry.listeners.size||entry.state.busy)return;
  if(receiptFailure&&entry.recovered)return;
  entry.recovered=receiptFailure;entry.bytes=0;entry.state={report:null,error:'',busy:true};emit(entry);queueMicrotask(pump);
}
