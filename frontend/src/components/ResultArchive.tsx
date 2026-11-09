'use client';
import {useEffect,useRef,useState} from 'react';
import type {ProcessingJob} from '@/lib/types';

type ArchivedJob=Pick<ProcessingJob,'job_id'|'status'|'created_at'|'input'|'artifact'|'retention'>;
const limit=16*1024**2;
function validRow(value:unknown):value is ArchivedJob {
 if(!value||typeof value!=='object')return false;
 const j=value as ArchivedJob,a=j.artifact;
 return typeof j.job_id==='string'&&/^[a-f0-9]{32}$/.test(j.job_id)&&
  ['queued','running','succeeded','failed','cancelled'].includes(j.status)&&typeof j.created_at==='string'&&
  (!a||typeof a.filename==='string'&&Number.isSafeInteger(a.bytes)&&a.bytes>0&&a.bytes<=limit&&
   (j.retention?.state!=='available'||typeof a.sha256==='string'&&/^[a-f0-9]{64}$/.test(a.sha256)));
}
function available(job:ArchivedJob,now:number){
 const expiry=job.retention?.expires_at;
 return job.status==='succeeded'&&!!job.artifact&&job.retention?.state==='available'&&
  (!expiry||Number.isFinite(Date.parse(expiry))&&Date.parse(expiry)>now);
}

export default function ResultArchive(){
 const [rows,setRows]=useState<ArchivedJob[]>([]),[error,setError]=useState(''),[busy,setBusy]=useState(false),[loaded,setLoaded]=useState(false);
 const [receiving,setReceiving]=useState(''),[message,setMessage]=useState(''),[now,setNow]=useState(Date.now());
 const active=useRef<AbortController|null>(null),mounted=useRef(true);
 useEffect(()=>{mounted.current=true;const timer=setInterval(()=>setNow(Date.now()),1000);return()=>{mounted.current=false;active.current?.abort();clearInterval(timer);};},[]);
 async function load(){
  if(active.current)return;
  const controller=new AbortController();active.current=controller;setBusy(true);setError('');setMessage('');setRows([]);setLoaded(false);
  try{
   const r=await fetch('/api/processing/jobs',{cache:'no-store',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(8000)])});
   if(!r.ok)throw new Error('보관 작업 조회 실패. 같은 브라우저의 소유권 쿠키와 서버 상태를 확인하세요.');
   const d=await r.json();
   if(!d||!Array.isArray(d.jobs)||d.jobs.length>100||!d.jobs.every(validRow))throw new Error('보관 작업 응답을 확인하지 못했습니다. 다시 조회하세요.');
   if(mounted.current){setRows(d.jobs);setLoaded(true);setNow(Date.now());}
  }catch(e){if(mounted.current)setError(e instanceof Error&&e.name!=='TimeoutError'?e.message:'보관 작업 조회 시간이 초과되었습니다. 다시 조회하세요.');}
  finally{active.current=null;if(mounted.current)setBusy(false);}
 }
 async function receive(job:ArchivedJob){
  if(active.current||!available(job,Date.now())||!job.artifact)return;
  const controller=new AbortController();active.current=controller;setReceiving(job.job_id);setError('');setMessage('ZIP 전체 수신·해시 확인 중…');
  try{
   const r=await fetch(`/api/processing/jobs/${job.job_id}/download`,{cache:'no-store',redirect:'error',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(120000)])});
   if(!r.ok){
    await r.body?.cancel();
    if(r.status===404||r.status===410){
     if(mounted.current)setRows(old=>old.map(j=>j.job_id===job.job_id?{...j,retention:{state:'missing',remaining_seconds:0,expires_at:j.retention?.expires_at||null}}:j));
     throw new Error('파일 보관 만료·누락 또는 세션 만료입니다. 보관 결과를 다시 조회하세요.');
    }
    throw new Error(r.status===429?'파일 전송 동시성/사용량 상한입니다. 잠시 뒤 다시 시도하세요.':`처리 결과 다운로드 실패 (HTTP ${r.status}). 다시 시도하세요.`);
   }
   const length=Number(r.headers.get('content-length'));
   if(r.headers.get('content-type')!=='application/zip'||!Number.isSafeInteger(length)||length<=0||length>limit||length!==job.artifact.bytes){await r.body?.cancel();throw new Error('검증된 ZIP 응답/크기 확인 실패. 보관 결과를 다시 조회하세요.');}
   if(!r.body)throw new Error('파일 본문이 없습니다.');
   const reader=r.body.getReader(),chunks:Uint8Array<ArrayBuffer>[]=[];let size=0;
   try{while(true){const part=await reader.read();if(part.done)break;size+=part.value.length;if(size>length)throw new Error('다운로드 상한 초과');chunks.push(new Uint8Array(part.value));}}
   catch(e){await reader.cancel();throw e;}finally{reader.releaseLock();}
   if(size!==length)throw new Error('불완전한 파일 수신입니다. 다시 시도하세요.');
   const blob=new Blob(chunks,{type:'application/zip'});
   const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer()))).map(n=>n.toString(16).padStart(2,'0')).join('');
   if(hash!==job.artifact.sha256)throw new Error('수신 ZIP SHA-256 불일치. 파일을 저장하지 않았습니다. 보관 결과를 다시 조회하세요.');
   if(!mounted.current||controller.signal.aborted)return;
   const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download=/^[A-Za-z0-9_.-]+$/.test(job.artifact.filename)?job.artifact.filename:'processing-result.zip';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
   setMessage(`ZIP 전체 ${size.toLocaleString()} bytes 수신·SHA-256 확인. 디스크 저장 및 GIS 재열기는 별도 확인하세요.`);
  }catch(e){if(mounted.current){setMessage('');setError(e instanceof Error&&e.name!=='TimeoutError'?e.message:'파일 수신 시간이 초과되었습니다. 다시 시도하세요.');}}
  finally{active.current=null;if(mounted.current)setReceiving('');}
 }
 return <details className="result-archive"><summary>내 결과 보관함 · 재시작 후 찾기</summary>
  <p>현재 브라우저 소유 작업만 조회합니다. 과거 결과를 현재 조건에 적용하거나 다시 실행하지 않습니다. 로컬 서버 파일·쿠키 보관 기간 안에서만 접근할 수 있습니다.</p>
  <button type="button" disabled={busy||!!receiving} onClick={()=>void load()}>{busy?'조회 중…':'보관 결과 조회'}</button>
  {error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
  {loaded&&!rows.length&&<p>이 브라우저에서 보관 중인 작업이 없습니다. 이전 서버에서 생성한 메모리 작업·만료 쿠키는 복원할 수 없습니다.</p>}
  <ul>{rows.map(j=><li key={j.job_id}>
   <strong>{typeof (j.input as {analysis_id?:unknown})?.analysis_id==='string'?(j.input as {analysis_id:string}).analysis_id:'분석 종류 미제공'} · {j.status}</strong>
   <p>{j.created_at} · {j.retention?.state==='available'&&!available(j,now)?'expired':j.retention?.state} · 만료 {j.retention?.expires_at||'파일 없음'}</p>
   {j.artifact&&<p>{j.artifact.filename} · {j.artifact.bytes.toLocaleString()} bytes</p>}
   {available(j,now)&&<button type="button" disabled={!!receiving||busy} onClick={()=>void receive(j)}>{receiving===j.job_id?'처리 ZIP 수신 중…':'이전 결과 ZIP 저장'}</button>}
   <p>수신·해시 확인과 디스크 저장·GIS 재열기는 별도 확인입니다.</p>
  </li>)}</ul>
 </details>;
}
