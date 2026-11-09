'use client';
import {useEffect,useRef,useState} from 'react';
import {sceneKey,type Scene} from './types';
import {authGeneration,inspectMedia,subscribeAuth,subscribePreview,retryPreview,type PreviewState} from './providerPreviewQueue';

export interface AccessState {source_provider_id?:string;source_label?:string;source_item_url?:string;source_reference?:{provider_id:string;collection:string;id:string};product_match?:{status:string;product_id:string;platform:string;datetime:string;processing_level:string;collection_version:string};original_access?:AccessState;alternate_preview?:AccessState&{provider_id:string};redirect_host?:string;status:string;message:string;access_verified:boolean;size_bytes?:number|null;http_status?:number|null;url?:string;download_url?:string;key?:string;source_asset?:string;original_status?:string;receipt_expires_at?:number;correspondence?:{product_id:string;usgs_item_url:string}|null}
export interface AccessReport {reference:{provider_id:string;collection:string;id:string};preview:AccessState|null;assets:AccessState[];
  landsat?:{product_id:string|null;scene_id:string;portal_url:string;instructions:string};notice:string}

export function useProviderAccess(scene:Scene,keys:string[],includePreview:boolean){
  const [report,setReport]=useState<AccessReport|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
  const [auth,setAuth]=useState(authGeneration);
  const version=useRef(0),controller=useRef<AbortController|null>(null);
  const reportContext=useRef('');
  const context=JSON.stringify([sceneKey(scene),keys,includePreview]);
  useEffect(()=>subscribeAuth(()=>setAuth(authGeneration())),[]);
  function reset(){version.current++;controller.current?.abort();setReport(null);setError('');setBusy(false);}
  useEffect(()=>{reset();return()=>{version.current++;controller.current?.abort();};},[context,auth]);
  async function inspect(){
    reset();const current=version.current,abort=new AbortController();controller.current=abort;setBusy(true);
    try{
      if(keys.length>8)throw new Error('한 번에 원본 파일 8개까지 선택해 확인하세요.');
      const next=await inspectMedia(scene,keys,includePreview,abort.signal);
      if(current===version.current){reportContext.current=JSON.stringify([context,auth]);setReport(next);}
    }catch(e){if(current===version.current&&!abort.signal.aborted)setError(e instanceof Error?e.message:'파일 접근 확인 실패');}
    finally{if(current===version.current)setBusy(false);}
  }
  return {report:reportContext.current===JSON.stringify([context,auth])?report:null,error,busy,inspect};
}

export function useAutomaticPreview(scene:Scene,active:boolean){
  const [auth,setAuth]=useState(authGeneration);
  const [state,setState]=useState<PreviewState>({report:null,error:'',busy:false});
  const identity=sceneKey(scene);
  useEffect(()=>subscribeAuth(()=>{setState({report:null,error:'',busy:false});setAuth(authGeneration());}),[]);
  useEffect(()=>{
    if(!active)return;
    return subscribePreview(scene,setState);
  },[identity,auth,active]);
  return {...state,auth,retry:(receiptFailure=false)=>retryPreview(scene,receiptFailure)};
}
