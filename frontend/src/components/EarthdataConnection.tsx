'use client';
import {useEffect,useRef,useState} from 'react';
import {disposalUnconfirmed,notifyAuthChange} from '@/lib/providerPreviewQueue';

type Status={configured:boolean;connected:boolean;scope?:string;message?:string;storage_message?:string;reauthorization_required?:boolean;refresh_available?:boolean;persistence_enabled?:boolean;storage?:string;connection_expires_at?:number;access_token_expires_at?:number;session_expires_at?:number;access_expires_at?:number;expires_at?:number;integration?:string};
type Provider={id:string;name:string;configured:boolean;connected:boolean;integration?:string;storage?:string;message?:string;operator_mode?:boolean;access_state?:string};
const record=(value:unknown):Record<string,unknown>|null=>value!==null&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:null;
function parseStatus(value:unknown):Status|null{
  const data=record(value);if(!data||typeof data.configured!=='boolean'||typeof data.connected!=='boolean')return null;
  const next:Status={configured:data.configured,connected:data.connected};
  for(const key of ['scope','message','storage_message','storage','integration'] as const)if(typeof data[key]==='string')next[key]=data[key];
  for(const key of ['reauthorization_required','refresh_available','persistence_enabled'] as const)if(typeof data[key]==='boolean')next[key]=data[key];
  for(const key of ['connection_expires_at','access_token_expires_at','session_expires_at','access_expires_at','expires_at'] as const){
    const time=data[key];if(typeof time==='number'&&Number.isFinite(time)&&time>0&&time<=8.64e12)next[key]=time;
  }
  return next;
}
function parseLogout(value:unknown){
  const data=record(value);
  if(!data||data.connected!==false||typeof data.storage_disposed!=='boolean')return null;
  return {storageDisposed:data.storage_disposed,sessionMissing:data.session_missing===true,cleanupRequired:typeof data.cleanup_required==='boolean'?data.cleanup_required:undefined,revocationRecorded:typeof data.revocation_recorded==='boolean'?data.revocation_recorded:undefined,message:typeof data.message==='string'?data.message:undefined};
}
function disconnected(status:Status|null):Status|null{return status?{...status,connected:false,reauthorization_required:false,refresh_available:false,connection_expires_at:undefined,access_token_expires_at:undefined,session_expires_at:undefined,access_expires_at:undefined,expires_at:undefined}:null;}
function parseProviders(value:unknown):Provider[]{
  const data=record(value),source=data?.providers??value;
  const rows=Array.isArray(source)?source.map(item=>[undefined,item]):Object.entries(record(source)??{});
  return rows.flatMap(([id,value])=>{
    const item=record(value),providerId=item?.provider_id??item?.id??id;
    if(!item||typeof providerId!=='string'||typeof item.configured!=='boolean'||typeof item.connected!=='boolean')return [];
    const names:Record<string,string>={'earth-search':'Earth Search · Landsat/USGS','copernicus':'Copernicus Data Space','nasa-cmr':'NASA Earthdata'};
    return [{id:providerId,name:typeof item.name==='string'?item.name:names[providerId]??providerId,configured:item.configured,connected:item.connected,
      integration:typeof item.integration==='string'?item.integration:undefined,storage:typeof item.storage==='string'?item.storage:undefined,message:typeof item.message==='string'?item.message:undefined,operator_mode:item.operator_mode===true,access_state:typeof item.access_state==='string'?item.access_state:undefined}];
  });
}
function storageLabel(storage?:string){
  if(!storage)return '저장 방식 미제공';
  if(/dpapi|windows.*encrypt/i.test(storage))return '이 Windows 사용자 계정으로 암호화하여 로컬 저장';
  if(/memory/i.test(storage))return '서버 메모리 저장 · 서버 재시작 시 재연결 필요';
  if(/unsupported|unavailable|disabled|not_implemented/i.test(storage))return '영속 저장 미지원·비활성';
  if(storage==='none')return '로그인 정보 저장 없음';return storage;
}
function expiryLabel(value?:number|null){return typeof value==='number'&&Number.isFinite(value)?new Date(value*1000).toLocaleString('ko-KR'):null;}
const integrations:Record<string,string>={public_catalog_only:'공개 검색만 지원',public_catalog_and_selected_public_assets:'공개 검색·일부 공개 파일 지원',earthdata_local_oauth:'NASA 사용자별 계정 연결',not_implemented:'원본 인증 미지원'};
const messages:Record<string,string>={connected:'Earthdata 계정이 연결되었습니다. 파일별 접근은 아직 별도로 확인해야 합니다.',denied:'Earthdata에서 연결을 승인하지 않았습니다.',failed:'Earthdata 계정 연결에 실패했습니다. 앱 등록 정보와 권한을 확인하세요.',invalid_state:'로그인 요청이 만료되었거나 일치하지 않습니다. 다시 연결하세요.',unavailable:'Earthdata 연결 설정을 확인하세요.'};

export default function EarthdataConnection(){
  const [status,setStatus]=useState<Status|null>(null),[providers,setProviders]=useState<Provider[]>([]);
  const [notice,setNotice]=useState(''),[busy,setBusy]=useState(false),[disposal,setDisposal]=useState('');
  const unresolved=useRef(false),acting=useRef(false);
  const version=useRef(0),pending=useRef<AbortController|null>(null);
  function markUnconfirmed(message:string){unresolved.current=true;setDisposal(message);}
  async function load(){
    const current=++version.current;pending.current?.abort();const controller=new AbortController();pending.current=controller;
    const signal=AbortSignal.any([controller.signal,AbortSignal.timeout(15000)]);
    try{
      const response=await fetch('/api/auth/earthdata/status',{credentials:'same-origin',cache:'no-store',signal});
      if(!response.ok)throw new Error('계정 연결 상태를 확인할 수 없습니다.');
      const next=parseStatus(await response.json());if(!next)throw new Error('계정 상태 응답을 확인하지 못했습니다.');
      if(current!==version.current||controller.signal.aborted)return;
      setStatus(unresolved.current?disconnected(next):next);
      const providerResponse=await fetch('/api/auth/providers/status',{credentials:'same-origin',cache:'no-store',signal});
      if(providerResponse.ok){
        const values=parseProviders(await providerResponse.json());
        if(current===version.current&&!controller.signal.aborted)setProviders(values.map(provider=>unresolved.current&&provider.id==='nasa-cmr'?{...provider,connected:false}:provider));
      }
    }catch(error){if(!controller.signal.aborted&&current===version.current)setNotice(error instanceof Error?error.message:'계정 연결 상태를 확인할 수 없습니다.');}
  }
  useEffect(()=>{
    if(disposalUnconfirmed())markUnconfirmed('이 브라우저의 이전 연결은 디스크 폐기 미확인 상태입니다. 같은 브라우저에서 연결 폐기를 다시 시도하세요.');
    const result=new URLSearchParams(window.location.search).get('earthdata');
    if(result&&messages[result]){
      setNotice(unresolved.current?'연결 응답과 별개로 이전 연결의 디스크 폐기 미확인 상태를 유지합니다.':messages[result]);
      const url=new URL(window.location.href);url.searchParams.delete('earthdata');window.history.replaceState(null,'',url.pathname+url.search+url.hash);
      notifyAuthChange();
    }
    const expired=()=>{setStatus(previous=>previous?{...previous,connected:false,reauthorization_required:true}:previous);setNotice('NASA 인증 갱신이 실패했습니다. Earthdata를 다시 연결하세요.');};
    const external=(event:Event)=>{
      version.current++;pending.current?.abort();acting.current=false;setBusy(false);setStatus(null);setProviders([]);
      const outcome=(event as CustomEvent<{logout?:string}>).detail?.logout;
      if(outcome==='unconfirmed'||disposalUnconfirmed()){
        markUnconfirmed('다른 탭에서 연결 폐기를 확인하지 못했습니다. 디스크 폐기 미확인 상태이며 연결 폐기를 다시 시도해야 합니다.');
      }else if(outcome==='disposed'){
        // Only the explicit, validated logout path emits this acknowledgement.
        unresolved.current=false;setDisposal('');
      }
      setNotice('다른 탭에서 연결 상태가 바뀌어 현재 표시와 파일 접근을 무효화했습니다. 상태를 다시 확인합니다.');
      void load();
    };
    window.addEventListener('earthdata-reauthorization-required',expired);
    window.addEventListener('earthdata-external-change',external);void load();
    return()=>{version.current++;pending.current?.abort();acting.current=false;window.removeEventListener('earthdata-reauthorization-required',expired);window.removeEventListener('earthdata-external-change',external);};
  },[]);
  async function action(kind:'logout'|'refresh'){
    if(acting.current||(kind==='refresh'&&unresolved.current))return;
    const wasUnconfirmed=unresolved.current;
    acting.current=true;setBusy(true);setNotice('');
    const current=++version.current;pending.current?.abort();const controller=new AbortController();pending.current=controller;
    if(kind==='logout'){
      setStatus(disconnected);setProviders([]);
      markUnconfirmed('디스크 폐기 결과를 확인 중입니다. 확인이 끝날 때까지 연결 표시와 파일 접근을 무효화합니다.');
      notifyAuthChange('unconfirmed');
    }
    let reload=false;
    try{
      const response=await fetch(`/api/auth/earthdata/${kind}`,{method:'POST',credentials:'same-origin',cache:'no-store',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(15000)])});
      const body:unknown=await response.json().catch(()=>null);
      if(current!==version.current||controller.signal.aborted)return;
      if(kind==='logout'){
        const result=parseLogout(body);
        setStatus(disconnected);setProviders([]);reload=true;
        // A cookie-less success cannot prove that an earlier failed grant was deleted.
        // Current server rejects missing SID with 503/session_missing. Its new
        // cleanup/revocation fields distinguish it from cookie-less legacy 200s.
        const confirmedContract=result?.cleanupRequired===false&&typeof result.revocationRecorded==='boolean';
        if(response.ok&&result?.storageDisposed&&!result.sessionMissing&&result.cleanupRequired!==true&&(!wasUnconfirmed||confirmedContract)){
          unresolved.current=false;setDisposal('');setNotice('이 사이트의 Earthdata 연결을 해제했습니다. 저장 정보 폐기를 확인했습니다.');
          notifyAuthChange('disposed');
        }else{
          const reason=response.ok&&result?.storageDisposed?'현재 요청의 폐기 응답은 받았지만 원래 연결 정보의 전달을 확인하지 못했습니다. 이전 실패 대상의 폐기 성공으로 판단할 수 없습니다.':result?.message||'연결 폐기 응답이 실패했거나 올바른 확인 결과를 받지 못했습니다.';
          markUnconfirmed(`디스크 폐기 미확인. ${reason} 같은 브라우저에서 연결 폐기를 다시 시도하세요.`);
          notifyAuthChange('unconfirmed');
        }
      }else{
        const next=parseStatus(body);if(!response.ok||!next)throw new Error();setStatus(next);
        setNotice(next.reauthorization_required?'갱신이 거부되거나 만료됐습니다. 다시 연결하세요.':'계정 상태 확인. 실제 파일 접근은 별도 확인하세요.');
        setProviders([]);notifyAuthChange();
      }
    }catch{
      if(current!==version.current||controller.signal.aborted)return;
      if(kind==='logout'){
        setStatus(disconnected);setProviders([]);reload=true;
        markUnconfirmed('디스크 폐기 미확인. 서버 연결 실패 또는 응답 시간 초과로 폐기 결과를 확인하지 못했습니다. 같은 브라우저에서 연결 폐기를 다시 시도하세요.');
        notifyAuthChange('unconfirmed');
      }else setNotice('계정 갱신 상태를 확인하지 못했습니다. 다시 시도하세요.');
    }finally{
      if(current===version.current){acting.current=false;setBusy(false);if(reload)void load();}
    }
  }
  const connected=!!status?.connected&&!disposal;
  const nasaOperator=providers.find(p=>p.id==='nasa-cmr')?.operator_mode;
  return <div className="earthdata-connection" aria-label="NASA Earthdata 계정">
    {nasaOperator?<><span>NASA · 운영자 제공 자료 접근</span><small>방문자 제공처 로그인은 필요하지 않습니다. 미리보기·원본 접근·전체 파일 수신은 각각 확인합니다.</small></>:disposal?<>
      <span>Earthdata 연결 표시 해제 · 디스크 폐기 미확인</span>
      <p role="alert">{disposal}</p>
      <small>쿠키를 지우거나 다른 계정으로 바꾸기 전에 같은 브라우저에서 재시도하세요. 계속 실패하면 운영자의 저장소 권한 확인·격리와 NASA 측 권한 철회를 별도로 확인해야 합니다. 상태 조회만으로 이전 폐기를 확정하지 않습니다.</small>
      <button type="button" disabled={busy} onClick={()=>void action('logout')}>연결 폐기 다시 시도</button>
    </>:busy?<span>Earthdata 연결 상태 변경 중…</span>:connected?<>
      <span>Earthdata 연결됨</span><button type="button" onClick={()=>void action('refresh')}>계정 상태·갱신 확인</button><button type="button" onClick={()=>void action('logout')}>연결 해제</button>
    </>:status?.configured?<a className="earthdata-connect-button" href="/api/auth/earthdata/start">Earthdata 계정 연결</a>:<span>{status?'Earthdata 연결 준비 중':'Earthdata 상태 확인 중'}</span>}
    {!nasaOperator&&!disposal&&status?.reauthorization_required&&<span>Earthdata 재연결 필요</span>}
    {!nasaOperator&&!disposal&&status?.message&&<small>{status.message}</small>}
    {!nasaOperator&&status&&<small>{storageLabel(status.storage)}</small>}
    {!nasaOperator&&status?.storage_message&&<small>{status.storage_message}</small>}
    {!nasaOperator&&status&&(status.persistence_enabled===false||/memory/i.test(status.storage||''))&&<small>기본은 메모리 모드이며 서버 재시작 시 다시 연결해야 합니다. 로그인 유지를 원하면 운영자가 서버의 영속 저장을 명시적으로 켜야 합니다.</small>}
    {!nasaOperator&&connected&&status&&<>
      <small>NASA 원본 파일의 접근 권한·다운로드는 별도 확인이 필요합니다.</small>
      {expiryLabel(status.connection_expires_at??status.session_expires_at??status.expires_at)&&<small>사이트 연결 보관 만료: {expiryLabel(status.connection_expires_at??status.session_expires_at??status.expires_at)}</small>}
      {expiryLabel(status.access_token_expires_at??status.access_expires_at)&&<small>제공처 접근 토큰 만료: {expiryLabel(status.access_token_expires_at??status.access_expires_at)}</small>}
      <small>{status.refresh_available?'제공처가 발급한 갱신 권한 있음':'갱신 권한 미제공·없음'} · 만료·철회·저장소 변경 시 재연결이 필요할 수 있습니다.</small>
    </>}
    <details><summary>제공처별 연결 상태</summary>
      <p>NASA Earthdata 연결은 USGS·Copernicus 로그인을 대신하지 않습니다.</p>
      {providers.length?providers.map(provider=><div key={provider.id}><b>{provider.name}</b><small>{provider.operator_mode?`운영자 제공 · ${provider.access_state||'상태 확인 필요'}`:provider.connected&&!(disposal&&provider.id==='nasa-cmr')?'계정 연결됨':provider.configured?'인증 설정됨 · 사용자 연결 없음':'원본 인증 미설정·미연결'}{provider.integration&&integrations[provider.integration]?` · ${integrations[provider.integration]}`:''}</small><small>{storageLabel(provider.storage)}</small>{provider.message&&<small>{provider.message}</small>}</div>)
        :<small>제공처별 상태 미제공. USGS/CDSE 원본 인증 연결은 확인되지 않았습니다.</small>}
    </details>
    {notice&&<small role="status">{notice}</small>}
  </div>;
}
