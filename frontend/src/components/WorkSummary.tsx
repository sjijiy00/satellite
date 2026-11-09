'use client';
import Link from 'next/link';
import {useEffect,useState} from 'react';
import {useWorkSession,selectedBands,type SavedJob} from '@/lib/workSession';
import type {ProcessingCapabilities} from '@/lib/analysisFlow';
import {sceneKey,type Scene,type SearchResponse,type CloudJob,type EstimateJob} from '@/lib/types';
export default function WorkSummary({scene,data,processing,capabilities}:{scene:Scene|null;data:SearchResponse|null;processing:boolean;capabilities?:ProcessingCapabilities}){
 const session=useWorkSession();if(!session)return null;
 const keys=scene?selectedBands(scene,session.bands):[];
 const statuses=scene?session.acquisitions[sceneKey(scene)]||{}:{};
 const received=keys.filter(key=>statuses[key]?.status==='received');
 if(!processing)return <section className="search-entry work-summary" aria-label="현재 작업 요약" data-testid="work-summary">
  <h2>선택 영상</h2>
  {scene?<>
   <p><strong>{scene.datetime?.slice(0,10)||'촬영일 미제공'} · {scene.platform||'위성 미제공'}</strong> · {scene.processing_level||scene.collection}</p>
   <p>선택 밴드 {keys.length}개 · 원본 전체 수신 {received.length}/{keys.length}개</p>
   {keys.some(key=>statuses[key]?.status==='failed')&&<p role="alert">원본 다운로드 실패 · 해당 파일의 오류를 확인하세요.</p>}
   <details className="collection-help"><summary>선택 조건·다운로드 기록</summary>
    <p>{scene.provider} · {scene.collection} · {scene.id}</p>
    <p>{data?.query.start_date}–{data?.query.end_date} UTC · AOI {data?.query.bbox.join(', ')}</p>
    <p>선택 밴드: {keys.join(' · ')||'없음'}</p>
    <p>픽셀 품질: {scene.pixel_quality?.message||'미검사 · 분석 단계에서 확인합니다.'}</p>
    {session.linksSaved[sceneKey(scene)]&&<p>링크 목록 저장 기록 있음 · 원본 다운로드 완료와 별개</p>}
    <p>수신 수는 앱을 통한 브라우저 응답 완료 기록입니다. 외부 직접 링크의 완료·디스크 파일 현존 여부는 확인하지 않습니다.</p>
   </details>
  </>:<p>검색 결과에서 영상을 선택하세요.</p>}
  <div className="workflow-actions"><button type="button" disabled={!scene} onClick={()=>{const panel=document.querySelector(`[data-scene-key='${CSS.escape(scene?sceneKey(scene):'')}'] .asset-downloads`);panel?.setAttribute('open','');panel?.scrollIntoView({behavior:'smooth'});}}>원본 다운로드</button>
   {scene?<Link className="download-link" href="/processing">세부 분석 선택으로</Link>:<button disabled>세부 분석 선택으로</button>}
  </div><small>앱 분석은 원본 전체 다운로드 없이 진행할 수 있습니다.</small>
 </section>;
 return <section className="search-entry work-summary" aria-label="현재 작업 요약" data-testid="work-summary">
  <h2>현재 분석</h2>
  {keys.some(key=>statuses[key]?.status==='failed')&&<p role="alert">원본 다운로드 실패 · 아래 다운로드 기록에서 확인하세요.</p>}
  <p><strong>{session.analysis.label||'세부 분석 선택 필요'}</strong>{scene&&<> · {scene.datetime?.slice(0,10)||'촬영일 미확인'} · {scene.platform||'위성 미확인'}</>}</p>
  <p role="status">{!scene?'데이터 수집에서 영상을 선택하세요.':!session.analysis.id?'아래 ①에서 세부 분석을 선택하세요.':!session.analysis.confirmed?'아래 ①에서 선택한 분석을 확인하세요.':!capabilities?.quality&&!capabilities?.common?'현재 자료는 앱 내 분석 미지원 · 자료를 변경하세요.':'아래 실행 설정을 확인하고 처리 계획을 만드세요.'}</p>
  <details className="collection-help"><summary>선택 자료·품질·다운로드 기록</summary>
  <h2>{processing?'현재 전처리·분석 작업':'선택 영상·다운로드 요약'}</h2>
  {!scene?<p>선택 영상이 없습니다. 데이터 수집에서 검색·선택하세요.</p>:<>
   <p><strong>{data?.recommendation.label}</strong> · {scene.provider} · {scene.collection} · {scene.id}</p>
   <p>{data?.query.start_date}–{data?.query.end_date} UTC · AOI {data?.query.bbox.join(', ')}</p>
   <p>선택 밴드: {keys.join(' · ')||'없음'} · 원본 전체 수신 {received.length}/{keys.length}개</p>
   <p>세부 분석: {session.analysis.label||'다음 페이지에서 선택'} · {session.analysis.confirmed?'의도 확정 · 자료 적합성/실행 조건은 별도':'미확정 · 자동 처리 없음'}</p>
   <p>선택 영상 픽셀 품질: {scene.pixel_quality?.message||(processing&&!capabilities?.quality&&!capabilities?.common?'미검사 · 현재 자료·세부 분석의 앱 픽셀 QA 미지원':'미계산 · 지원 원본 검사가 필요합니다.')}</p>
   <p role="status">{received.length===keys.length&&keys.length?'선택 원본 전체 수신 기록 있음 · 서버 처리 시 원본 접근·필수 조건 재검사':processing?'브라우저 원본 미확보 · 서버 처리는 canonical Asset을 직접 읽으며 원본 전체 다운로드는 선택 사항입니다.':'확보 필요 · 선택/범위 접근/링크 목록 저장은 원본 전체 수신이 아닙니다.'}</p>
   {keys.some(key=>statuses[key]?.status==='failed')&&<p role="alert">원본 확보 실패. 제공처의 파일별 오류를 확인하세요.</p>}
   {session.linksSaved[sceneKey(scene)]&&<p>링크 목록 저장 기록 있음 · 원본 다운로드 완료와 별개</p>}
   <small>전체 수신은 앱 서버 경로의 브라우저 응답 완료 기록입니다. 직접 외부 링크의 완료는 추적하지 않습니다. 디스크 저장 여부·파일 현존·서버 원본 캐시를 보증하지 않습니다.</small>
   {processing&&<section aria-label="현재 가능한 다음 행동" data-testid="processing-next-action">
    <h3>현재 가능한 다음 행동</h3>
    <p>{!session.analysis.id?'아래에서 세부 분석을 선택하세요. 작업은 자동 실행하지 않습니다.':!session.analysis.confirmed?'선택한 세부 분석을 아래에서 확인하세요. 실행 조건은 확인 후에도 별도로 검사합니다.':capabilities?.common?'아래 공통 처리 패널에서 제품별 필수 밴드/QA와 필요한 사용자 기준을 확인하고 계획하세요. 서버가 실제 원본을 범위 읽기하므로 브라우저 원본 전체 수신 기록을 요구하지 않습니다.':!capabilities?.quality?'현재 선택 자료·세부 분석에는 앱 내부 계산 엔진이 연결되지 않았습니다. 원본 확보와 메타데이터 확인 후 외부 GIS에서 활용하세요.':!session.analysis.metadataReady?'세부 분석에 필요한 자료·기간·밴드를 보완하세요. 기존 조건과 선택은 유지합니다.':'서버에서 실제 접근·AOI 품질을 검사한 뒤 지원 작업을 진행하세요. 브라우저 원본 다운로드는 선택 사항입니다.'}</p>
    <Link className="download-link" href="/" onClick={()=>session.requestOriginal()}>원본 확보·선택 밴드 확인으로</Link>
    {session.analysis.id&&!capabilities?.quality&&!capabilities?.common&&<>
     <p>픽셀 QA·전처리·분석을 실행한 상태가 아닙니다. 원본을 모두 받아도 미지원 계산 엔진이 활성화되지는 않습니다.</p>
     {data?.recommendation.purpose_type==='thermal'&&<p>현재 선택 제공처·제품은 온도 실행 allowlist 밖입니다. 지원되는 PC Landsat 8/9 L2SP와 필수 QA를 수집하거나 외부 GIS를 활용하세요. Sentinel-2는 열적외선 지표면 온도 대안이 아닙니다.</p>}
     <details><summary>선택 영상 메타데이터 확인</summary><p>위성: {scene.platform||'미제공'} · 처리 수준: {scene.processing_level||'미제공'}</p><p>촬영: {scene.datetime||'미제공'} · 해상도: {scene.resolution_m.length?scene.resolution_m.join(' / ')+' m':'미제공'}</p><p>AOI 기하 중첩: {scene.overlap_percent==null?'미제공':scene.overlap_percent+'%'} · 장면 전체 구름량: {scene.scene_cloud_cover==null?'미제공':scene.scene_cloud_cover+'%'}</p><p>기하 중첩과 장면 구름량은 AOI 픽셀 품질이 아닙니다.</p></details>
     <p>외부 GIS 활용: 원본 밴드·품질 자료를 확보하고 제품의 scale·offset·단위와 결측 정책을 확인하세요. 앱에서 온도·침수·피복 계산을 완료했다고 표시하지 않습니다.</p>
    </>}
   </section>}
  </>}
  </details>
  <div className="workflow-actions">{processing?<Link className="download-link" href="/">데이터 수집으로 돌아가기</Link>:<>
   <button type="button" disabled={!scene} onClick={()=>{document.querySelector(`[data-scene-key='${CSS.escape(scene?sceneKey(scene):'')}'] .asset-downloads`)?.setAttribute('open','');document.querySelector(`[data-scene-key='${CSS.escape(scene?sceneKey(scene):'')}'] .asset-downloads`)?.scrollIntoView({behavior:'smooth'});}}>원본 다운로드</button>
   {scene?<Link className="download-link" href="/processing">세부 분석 선택으로</Link>:<button disabled>세부 분석 선택으로</button>}
  </>}</div>
  {!processing&&<p>원본 다운로드 후 여기서 종료해도 됩니다. 전처리·분석은 선택 사항입니다.</p>}
 </section>;
}

export function RestoredJobs({jobs,context}:{jobs:SavedJob[];context:string}){
 const [states,setStates]=useState<Record<string,CloudJob|EstimateJob|null>>({});
 useEffect(()=>{
  let active=true;const abort=new AbortController();
  async function poll(){for(const row of jobs){try{
   const response=await fetch(`/api/${row.kind}/jobs/${row.job.job_id}`,{cache:'no-store',signal:AbortSignal.any([abort.signal,AbortSignal.timeout(8000)])});
   const next=response.ok?await response.json():null;
   if(active)setStates(old=>({...old,[row.job.job_id]:next}));
  }catch{if(active&&!abort.signal.aborted)setStates(old=>({...old,[row.job.job_id]:null}));}}}
  void poll();const timer=setInterval(()=>void poll(),3000);
  return()=>{active=false;abort.abort();clearInterval(timer);};
 },[jobs]);
 if(!jobs.length)return null;
 return <section className="search-entry" aria-label="복원한 작업 상태"><h3>복원한 작업·산출물</h3>
  <p>기존 작업 조회만 재개합니다. 새 다운로드·분석은 자동 실행하지 않습니다. 서버 재시작/15분 보관 만료/다른 세션이면 복원할 수 없습니다.</p>
  {jobs.map(row=>{const job=states[row.job.job_id],stale=row.context!==context;return <div key={row.job.job_id}>
   <b>{row.kind==='cloud'?'전처리 · 실제 관측 합성':'ML 추정 · 실측 아님'}</b> · {job?.status||'조회 불가 · 만료/서버 재시작/소유권 확인 필요'}
   {stale&&<p className="warning">이전 조건의 산출물 · 현재 지도/분석에 적용하지 않습니다.</p>}
   {job?.error&&<p>{job.error}</p>}
   {job&&(job.status==='queued'||job.status==='running')&&<button type="button" onClick={async()=>{
    const response=await fetch(`/api/${row.kind}/jobs/${job.job_id}/cancel`,{method:'POST',headers:{'Content-Type':'application/json'},body:'{}',signal:AbortSignal.timeout(8000)}).catch(()=>null);
    if(response?.ok){const next=await response.json();setStates(old=>({...old,[job.job_id]:next}));}
   }}>복원한 작업 취소</button>}
   {job?.status==='succeeded'&&<a className="download-link" href={`/api/${row.kind}/jobs/${job.job_id}/download`} download>{stale?'이전 조건 ':''}{row.kind==='cloud'?'전처리 결과':'ML 추정 결과'} ZIP 다운로드</a>}
  </div>;})}
 </section>;
}
