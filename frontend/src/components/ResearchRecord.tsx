'use client';
import {useEffect,useState} from 'react';
import type {ProcessingJob} from '@/lib/types';
import {researchRecord} from '@/lib/researchRecord';
export default function ResearchRecord({job,stale}:{job:ProcessingJob;stale:boolean}){
 const [note,setNote]=useState(''),[message,setMessage]=useState('');
 useEffect(()=>{setNote('');setMessage('');},[job.job_id]);
 function save(){
  try{
   const blob=new Blob([JSON.stringify(researchRecord(job,note,new Date().toISOString()),null,2)],{type:'application/json'});
   const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`research-record-${job.job_id.replace(/[^a-zA-Z0-9_-]/g,'')}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);setMessage('연구 기록 JSON 저장을 요청했습니다. 다운로드 파일을 확인하세요.');
  }catch{setMessage('연구 기록 파일을 만들지 못했습니다. 다시 시도하세요.');}
 }
 return <section aria-label="연구 기록 저장"><h3>{stale?'이전 작업의 연구 기록':'이 작업의 연구 기록'}</h3>
  <p>조건·출처·검증 지표를 JSON으로 저장합니다.</p>
  {stale&&<p>현재 바꾼 조건이 아닌 위 작업 ID의 실행 당시 조건을 저장합니다.</p>}
  <details className="collection-help"><summary>연구 메모 추가·저장 내용</summary>
  <label htmlFor="research-note">연구 메모 · 장면 선택 이유와 기준 채택 근거 (선택)</label><textarea id="research-note" value={note} maxLength={2000} onChange={e=>setNote(e.target.value)}/>
  <p>메모는 저장할 JSON에만 포함됩니다. 이 파일에는 원본 픽셀이 없으므로 성공 ZIP·manifest도 함께 보관하세요.</p>
  </details><button type="button" onClick={save}>연구 기록 JSON 저장</button>{message&&<p role="status">{message}</p>}
 </section>;
}
