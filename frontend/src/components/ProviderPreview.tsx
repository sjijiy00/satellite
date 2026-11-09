'use client';
import {useEffect,useRef,useState} from 'react';
import type {Scene} from '@/lib/types';
import {useAutomaticPreview} from '@/lib/useProviderAccess';
import {receiveMediaFile,subscribeAuth} from '@/lib/providerPreviewQueue';
import {useWorkSession} from '@/lib/workSession';

function ManagedPreview({scene,large}:{scene:Scene;large:boolean}){
  const session=useWorkSession(),landsat=scene.provider_id==='earth-search'&&scene.collection==='landsat-c2-l2';
  const container=useRef<HTMLDivElement>(null);
  const recovered=useRef(false);
  const [inViewport,setInViewport]=useState(false),[visible,setVisible]=useState(true),[failedUrl,setFailedUrl]=useState('');
  const [saveState,setSaveState]=useState(''),[saving,setSaving]=useState(false);
  const saveController=useRef<AbortController|null>(null),saveVersion=useRef(0);
  const hasCandidate=landsat||(scene.preview_diagnostic?.has_candidate??!!scene.thumbnail);
  const {report,error,busy,retry,auth}=useAutomaticPreview(scene,inViewport&&visible&&hasCandidate);
  const preview=report?.preview,imageError=!!preview?.url&&failedUrl===preview.url;
  const original=preview?.original_access||preview;
  const previewFailure=preview?.alternate_preview||preview;
  const delayed=preview?.status!=='available'&&(previewFailure?.status==='timeout'||previewFailure?.http_status===504);
  const failureMessage=delayed?(previewFailure?.http_status===504?'제공처 미리보기 서버가 시간 초과(HTTP 504)를 반환했습니다.':'제공처 미리보기 응답을 제한 시간 안에 받지 못했습니다.'):preview?.message;
  useEffect(()=>{
    const element=container.current;if(!element)return;
    const observer=new IntersectionObserver(([entry])=>setInViewport(entry.isIntersecting&&entry.intersectionRatio>0));
    observer.observe(element);return()=>observer.disconnect();
  },[]);
  useEffect(()=>{recovered.current=false;setFailedUrl('');},[auth]);
  useEffect(()=>{
    const cancel=()=>{saveVersion.current++;saveController.current?.abort();saveController.current=null;setSaving(false);setSaveState('');};
    cancel();const unsubscribe=subscribeAuth(cancel);
    return()=>{saveVersion.current++;saveController.current?.abort();unsubscribe();};
  },[visible]);
  useEffect(()=>{if(imageError&&inViewport&&visible&&!recovered.current){recovered.current=true;retry(true);}},[imageError,inViewport,visible]);
  async function save(){
    if(saveController.current||!preview?.download_url||!visible)return;
    const controller=new AbortController(),current=++saveVersion.current;saveController.current=controller;setSaving(true);setSaveState('미리보기 이미지 수신 중…');
    try{
      const {blob,filename}=await receiveMediaFile(scene,preview.download_url,controller.signal,{receiptExpiresAt:preview.receipt_expires_at,onRefresh:()=>{
        if(current===saveVersion.current)setSaveState('미리보기 접근 만료 · 저장을 위해 1회 갱신 중…');
      }});
      if(!blob)throw new Error('미리보기 저장 내용을 확인하지 못했습니다.');
      if(current!==saveVersion.current||controller.signal.aborted)return;
      const url=URL.createObjectURL(blob),anchor=document.createElement('a');anchor.href=url;
      anchor.download=filename||'provider-browse.'+({'image/png':'png','image/jpeg':'jpg','image/webp':'webp'}[blob.type]||'png');
      anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setSaveState('미리보기 이미지 수신 완료 · 브라우저 저장 결과를 확인하세요.');
    }catch(error){if(current===saveVersion.current&&!controller.signal.aborted)setSaveState(error instanceof Error&&error.name==='TimeoutError'?'미리보기 저장 제한 시간을 넘었습니다. 다시 시도하세요.':error instanceof TypeError?'미리보기 저장 연결이 끊어졌습니다. 다시 시도하세요.':error instanceof Error?error.message:'미리보기 저장 실패. 다시 시도하세요.');}
    finally{if(current===saveVersion.current){saveController.current=null;setSaving(false);}}
  }
  return <div ref={container} className="provider-preview" data-preview-visible={inViewport}>
    {/* Keep a verified, already requested image mounted while scrolling. Fetching
        and retry still require visibility; hiding/auth changes retain their gates. */}
    {preview?.status==='available'&&preview.url&&visible&&!imageError?<img className={large?undefined:'thumbnail'} src={preview.url} alt={`${scene.id} 제공처 미리보기`} onError={()=>setFailedUrl(preview.url!)}/>
      :<div className={large?'provider-preview-state':'thumbnail absent'} role="status">{!visible?'미리보기를 숨겼습니다.':imageError?'미리보기 보관 기간 만료·접근 실패. 재시도하세요.':busy?'미리보기 자동 수신 대기·확인 중…':failureMessage||(!hasCandidate?'이 영상에는 제공처 미리보기 후보가 없습니다.':'화면에 보이면 미리보기를 자동 확인합니다.')}</div>}
    <div className="provider-preview-actions">
      {delayed&&visible&&!busy&&<p>잠시 후 재시도하거나 다른 촬영일을 선택하세요. 선택 조건은 유지됩니다. 원본 접근·분석 가능 여부는 별도로 확인합니다.</p>}
      {(error||imageError||(preview&&preview.status!=='available'))&&<button type="button" disabled={busy||!hasCandidate||!inViewport||!visible} onClick={()=>{recovered.current=false;setFailedUrl('');retry();}}>미리보기 재시도</button>}
      {hasCandidate&&<button type="button" onClick={()=>setVisible(v=>!v)}>{visible?'미리보기 숨기기':'미리보기 보기'}</button>}
      {preview?.status==='available'&&visible&&!imageError&&<>{preview.download_url&&<button type="button" disabled={saving} onClick={()=>void save()}>미리보기 이미지 저장</button>}<small>{preview.source_label||'제공처 이미지'} · {preview.source_asset} · 분석용 원본/픽셀 QA 아님</small>{preview.source_provider_id==='planetary-computer'&&<p>동일 제품의 공개 미리보기입니다. 선택한 Earth Search 장면·밴드·원본 다운로드 권한은 유지합니다.</p>}</>}
      {saveState&&<p role="status">{saveState}</p>}
      {landsat&&session&&<button type="button" disabled={!session.canSearchPcLandsat} onClick={session.searchPcLandsat}>PC Landsat에서 검색</button>}
      {preview&&<details><summary>미리보기 출처·접근 상세</summary>
        <p>{preview.source_label||scene.provider} · {preview.source_asset||'미리보기 미확인'}{preview.http_status!=null&&<> · 제공처 HTTP {preview.http_status}</>}</p>
        {preview.product_match&&<p>정확한 제품 대응: {preview.product_match.product_id} · {preview.product_match.platform} · {preview.product_match.datetime} · {preview.product_match.processing_level} · Collection {preview.product_match.collection_version}</p>}
        {preview.source_item_url&&<a href={preview.source_item_url} target="_blank" rel="noreferrer">PC 원본 Item 메타데이터 ↗</a>}
        {original?.original_status==='requester_pays'&&<p>Earth Search 미리보기는 AWS requester-pays입니다. 비용 동의/인증 없이 수신하지 않습니다.</p>}
        {preview.original_access&&<p>기존 경로: {original?.message} · {original?.status} · HTTP {original?.http_status??'미확인'}</p>}
        {original?.redirect_host&&<p>로그인 이동 호스트: {original.redirect_host}</p>}
        {original?.correspondence&&<a href={original.correspondence.usgs_item_url} target="_blank" rel="noreferrer">동일 제품 USGS Item 확인 ↗</a>}
        {preview.alternate_preview&&<p>PC 공개 미리보기: {preview.alternate_preview.message} · {preview.alternate_preview.status} · HTTP {preview.alternate_preview.http_status??'미확인'}. 원래 실패 상태를 유지합니다.</p>}
        {landsat&&<p>USGS 로그인·AWS requester-pays·PC 공개 SAS는 별개입니다. NASA Earthdata 인증으로 USGS/AWS를 대신하지 않습니다.</p>}
      </details>}
      {report?.landsat&&<details><summary>EarthExplorer에서 이 장면 찾기</summary><code>{report.landsat.product_id||scene.id}</code><p>{report.landsat.instructions}</p><a href={report.landsat.portal_url} target="_blank" rel="noreferrer">EarthExplorer 열기 ↗</a></details>}
      {error&&<p role="alert">{error}</p>}
    </div>
  </div>;
}
export default function ProviderPreview({scene,large=false}:{scene:Scene;large?:boolean}){
  const [failed,setFailed]=useState(false);
  // Legacy test/older response compatibility. Current provider scenes always use
  // the same-origin canonical proxy; NASA signed redirect URLs never reach images.
  if(scene.provider_id)return <ManagedPreview key={`${scene.provider_id}/${scene.collection}/${scene.id}`} scene={scene} large={large}/>;
  return scene.thumbnail&&!failed?<img className={large?undefined:'thumbnail'} src={scene.thumbnail} alt={`${scene.id} 제공처 미리보기`} onError={()=>setFailed(true)}/>:
    <div className={large?'provider-preview-state':'thumbnail absent'}>{failed?'제공처 미리보기 접근 실패':'이 영상에는 제공처 원본 미리보기가 없습니다.'} 검색 결과와 파일 링크는 그대로 사용할 수 있습니다.</div>;
}
