'use client';
import {useEffect,useRef,useState} from 'react';
import {sceneKey,type Scene} from '@/lib/types';
import {useProviderAccess} from '@/lib/useProviderAccess';
import {inspectMedia,receiveMediaFile,subscribeAuth,type MediaDiskWriter} from '@/lib/providerPreviewQueue';
import {useWorkSession} from '@/lib/workSession';

export default function ManagedAssetAccess({scene,keys}:{scene:Scene;keys:string[]}){
  const session=useWorkSession();
  const {report,error,busy,inspect}=useProviderAccess(scene,keys,false);
  const [states,setStates]=useState<Record<string,string>>({});
  const controllers=useRef(new Set<AbortController>()),generation=useRef(0);
  const activeKeys=useRef(new Set<string>()),receipts=useRef(new Map<string,string>());
  const context=JSON.stringify([sceneKey(scene),keys]),currentContext=useRef(context);currentContext.current=context;
  useEffect(()=>{
    const reset=()=>{generation.current++;for(const c of controllers.current)c.abort();controllers.current.clear();activeKeys.current.clear();receipts.current.clear();setStates({});};
    reset();const unsubscribe=subscribeAuth(reset);
    return()=>{generation.current++;for(const c of controllers.current)c.abort();controllers.current.clear();activeKeys.current.clear();unsubscribe();};
  },[context,report]);
  async function receive(key:string,url?:string){
    if(activeKeys.current.has(key)||!keys.includes(key))return;
    activeKeys.current.add(key);
    const largeSar=scene.provider_id==='copernicus'&&scene.collection==='sentinel-1-grd';
    let writable:MediaDiskWriter|undefined;
    if(largeSar){
      const picker=(window as Window & {showSaveFilePicker?:(options:{suggestedName:string})=>Promise<{createWritable:()=>Promise<MediaDiskWriter>}>}).showSaveFilePicker;
      if(!picker){activeKeys.current.delete(key);setStates(s=>({...s,[key]:'대용량 Sentinel-1 원본은 Chrome 또는 Edge의 파일 저장 기능이 필요합니다.'}));return;}
      try{
        const safeName=(scene.id+'-'+key).replace(/[^A-Za-z0-9_.-]/g,'_');
        const handle=await picker.call(window,{suggestedName:safeName+(key==='Product'?'.zip':'.tiff')});
        writable=await handle.createWritable();
      }catch(error){
        activeKeys.current.delete(key);
        if(error instanceof Error&&error.name!=='AbortError')setStates(s=>({...s,[key]:'파일 저장 위치를 열지 못했습니다. 다시 시도하세요.'}));
        return;
      }
      if(context!==currentContext.current){activeKeys.current.delete(key);await writable.abort();return;}
    }
    const current=generation.current,c=new AbortController();controllers.current.add(c);
    const valid=()=>current===generation.current&&context===currentContext.current&&!c.signal.aborted;
    setStates(s=>({...s,[key]:url?'파일 수신 중…':'다운로드 접근 확인 중…'}));
    session?.recordAsset(scene,key,{status:'receiving',at:Date.now()});
    try{
      if(!url){
        const checked=await inspectMedia(scene,[key],false,c.signal);
        if(!valid()){await writable?.abort();return;}
        const asset=checked.assets.find(a=>a.key===key);
        if(asset?.status!=='available'||!asset.download_url)throw new Error(asset?.message||'이 파일의 다운로드 접근을 확인하지 못했습니다.');
        url=asset.download_url;
        setStates(s=>({...s,[key]:'파일 수신 중…'}));
      }
      const {blob,bytes,filename,receipt}=await receiveMediaFile(scene,receipts.current.get(key)||url,c.signal,{assetKey:key,writable,onRefresh:()=>{
        if(valid())setStates(s=>({...s,[key]:'접근 만료 · 같은 파일의 접근을 1회 갱신 중…'}));
      }});
      if(!valid()){await writable?.abort();return;}
      await writable?.close();receipts.current.set(key,receipt);
      session?.recordAsset(scene,key,{status:'received',bytes,at:Date.now()});
      if(blob){const object=URL.createObjectURL(blob),a=document.createElement('a');a.href=object;
        a.download=filename||scene.id+'-'+key;a.click();setTimeout(()=>URL.revokeObjectURL(object),1000);}
      setStates(s=>({...s,[key]:writable?'파일 전체 수신·디스크 저장 완료':'파일 전체 수신 완료 · 브라우저 저장 결과를 확인하세요.'}));
    }catch(e){await writable?.abort().catch(()=>{});if(valid()){session?.recordAsset(scene,key,{status:'failed',at:Date.now()});setStates(s=>({...s,[key]:e instanceof Error&&e.name==='TimeoutError'?'파일 수신 제한 시간을 넘었습니다. 접근 확인 후 다시 시도하세요.':e instanceof TypeError?'파일 수신 연결이 끊어졌습니다. 접근 확인 후 다시 시도하세요.':e instanceof Error?e.message:'파일 수신 실패. 다시 시도하세요.'}));}}
    finally{controllers.current.delete(c);if(current===generation.current)activeKeys.current.delete(key);}
  }
  return <div className="managed-asset-access" aria-label="제공처별 원본 접근">
    {!report&&keys.map(key=><div key={key}><button type="button" disabled={busy||activeKeys.current.has(key)} onClick={()=>void receive(key)}>{key} 바로 다운로드</button>{states[key]&&<p role="status">{states[key]}</p>}</div>)}
    <button type="button" disabled={busy||!keys.length||controllers.current.size>0} onClick={()=>void inspect()}>{busy?'선택 원본 확인 중…':'선택 원본 접근 확인'}</button>
    <small>접근 확인 후 다운로드할 수 있습니다. 접근 확인만으로 파일을 받지는 않습니다.</small>
    <details className="collection-help"><summary>다운로드 한도·접근 안내</summary>
      <small>제공처의 원본 정보를 다시 확인합니다. 계정 연결·파일 접근·다운로드 완료는 각각 확인합니다. 한 번에 8개, 일반 파일당 256 MiB, Sentinel-1 CDSE 원본 파일당 2 GiB까지 지원합니다.</small>
      <small>접근이 만료되면 같은 선택 파일의 접근 갱신을 최대 1회 시도합니다.</small>
    </details>
    {scene.collection==='sentinel-1-grd'&&<small>자료 출처: Copernicus Sentinel data {/^\d{4}/.test(scene.datetime||'')?scene.datetime!.slice(0,4):'(촬영 연도 미확인)'}. 전체 장면을 받으며 SAR 분석·AOI 추출은 별도입니다.</small>}
    {error&&<p role="alert">{error}</p>}
    {report?.assets.map(a=><div key={a.key}><b>{a.key}</b><p role="status">{states[a.key||'']||a.message}</p>
      <details><summary>원본 접근 상세</summary><small>접근 상태: {a.status}{a.http_status!=null&&<> · 제공처 HTTP {a.http_status}</>}{a.redirect_host&&<> · 로그인 이동 호스트: {a.redirect_host}</>}</small>{a.correspondence&&<p><a href={a.correspondence.usgs_item_url} target="_blank" rel="noreferrer">동일 제품 USGS Item ↗</a></p>}<p>USGS 로그인, AWS requester-pays, NASA Earthdata는 서로 다른 접근 조건입니다.</p></details>
      {a.size_bytes!=null&&<small>원본 전체 파일 크기 {a.size_bytes.toLocaleString()} bytes · {session?.acquisitions[sceneKey(scene)]?.[a.key||'']?.status==='received'?'브라우저 전체 수신 기록 있음':'전체 수신 전'}</small>}
      <button type="button" disabled={a.status!=='available'||!a.download_url||activeKeys.current.has(a.key||'')} onClick={()=>void receive(a.key!,a.download_url!)}>원본 다운로드</button>
    </div>)}
    {report?.landsat&&<details><summary>이 Landsat 장면의 공식 접근 경로</summary><code>{report.landsat.product_id||scene.id}</code><p>{report.landsat.instructions}</p><a href={report.landsat.portal_url} target="_blank" rel="noreferrer">EarthExplorer 열기 ↗</a><p>Earthdata 연결로 AWS requester-pays/USGS 인증을 대체하지 않습니다.</p></details>}
  </div>;
}
