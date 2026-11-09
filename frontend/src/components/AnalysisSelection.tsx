'use client';
import Link from 'next/link';
import type {AnalysisCatalog,AnalysisTask,Purpose,RequestIntent,Scene} from '@/lib/types';
import {sceneKey} from '@/lib/types';
import type {assessTask,ProcessingCapabilities} from '@/lib/analysisFlow';

export default function AnalysisSelection({catalog,error,domain,intent,task,items,pair,assessment,confirmed,capabilities,onChoose,onPair,onConfirm,onOriginal}:{catalog:AnalysisCatalog|null;error:string;domain:Purpose;intent?:RequestIntent;task:AnalysisTask|null;items:Scene[];pair:[string,string];assessment:ReturnType<typeof assessTask>;confirmed:boolean;capabilities:ProcessingCapabilities;onChoose:(id:string|null)=>void;onPair:(pair:[string,string])=>void;onConfirm:()=>void;onOriginal:()=>void}){
 const options=catalog?.analyses.filter(a=>a.domain===domain)||[];
 return <section className="search-entry" aria-label="세부 분석 선택" data-testid="analysis-selection">
  <h2>① 세부 분석 확정</h2><p>큰 분야: {catalog?.domains.find(d=>d.id===domain)?.label||'분야 확인 필요'} · {intent?.summary||'원문 요청과 수집 조건을 유지합니다.'}</p>
  {error&&<p role="alert">{error} · 세부 분석 목록을 확인하기 전에는 처리를 실행하지 않습니다.</p>}
  {intent?.detail&&<p>원문의 세부 의도: {catalog?.analyses.find(a=>a.id===intent.detail)?.label||intent.detail} · {intent.basis==='explicit'?'명시':'AI 추론 · 확인 필요'} {intent.evidence&&<>· 근거: <q>{intent.evidence}</q></>} <button onClick={()=>onChoose(null)}>원문의 세부 의도로</button></p>}
  {!options.length&&<p>분야가 미지정이거나 지원 목록이 없습니다. 수집 단계에서 분야를 수정하세요. 요청을 다른 분야에 임의 배정하지 않습니다.</p>}
  <fieldset><legend>어떤 질문에 답할까요?</legend>{options.map(a=><label key={a.id} className="analysis-choice">
   <input type="radio" name="detail-analysis" value={a.id} checked={task?.id===a.id} onChange={()=>onChoose(a.id)}/><span><strong>{a.label}</strong><br/>{a.question}</span>
  </label>)}</fieldset>
  {task&&<details key={task.id} className="collection-help analysis-choice-details"><summary>{task.label} · 조건과 산출물</summary>
   <p><strong>필요 입력</strong> · {task.required_variables.join(' · ')} · {task.minimum_scenes}장면 이상{task.comparison?' · 다른 날짜/공통 영역/호환 제품 필요':''}</p>
   {!!task.additional_requirements?.length&&<><strong>주의사항</strong><ul>{task.additional_requirements.map(requirement=><li key={requirement}>{requirement}</li>)}</ul></>}
   <p><strong>산출물</strong> · {task.output}</p><p>{task.engine_note}</p>
  </details>}
  {task?.comparison&&<fieldset><legend>이 분석에 사용할 비교 영상 · 자동 교체하지 않음</legend>{[0,1].map(i=><div key={i}><label htmlFor={'detail-scene-'+i}>{i===0?'세부 분석 첫 번째 영상':'세부 분석 두 번째 영상'}</label><select id={'detail-scene-'+i} value={pair[i]} onChange={e=>{const next=[...pair] as [string,string];next[i]=e.target.value;onPair(next);}}><option value="">영상 선택 필요</option>{items.map(s=><option key={sceneKey(s)} value={sceneKey(s)}>{s.datetime?.slice(0,10)||'날짜 미확인'} · {s.platform||s.collection} · {s.id}</option>)}</select></div>)}</fieldset>}
  {task&&<>
   <h3>선택 자료 적합성 · 메타데이터 사전 확인</h3>
   {(capabilities.quality||capabilities.common)&&<p>필수 밴드·품질 자료는 자동으로 포함합니다.</p>}
   <p role="status">{assessment.metadataReady?'필요 입력 메타데이터/선택 확인 · 픽셀 QA·실행 가능 판정은 별도':'자료 보완 필요'}</p>
   {assessment.missing.map(m=><p key={m} className="warning">{m}</p>)}
   {capabilities.quality||capabilities.common?!!assessment.pending.length&&<details className="collection-help"><summary>실행 전 확인할 항목</summary>{assessment.pending.map(m=><p key={m}>{m}</p>)}</details>:<p>메타데이터 확인과 파일 접근은 픽셀 QA·계산 완료가 아닙니다. 현재 자료·세부 분석의 앱 처리 경로는 미지원입니다.</p>}
   {task.engine&&!capabilities.quality&&!capabilities.common&&<p className="warning">이 제공처·제품 조합은 서버 실행 allowlist에 없습니다. 선택은 의도 확인이며 분석 실행 허가가 아닙니다.</p>}
   {!task.engine&&<p className="warning">{task.engine_note}. 선택은 의도 확인이며 분석 실행 허가가 아닙니다.</p>}
   {!assessment.metadataReady&&<p>필요 변수 {task.required_variables.join(' · ')}와 {task.minimum_scenes}개 시점을 갖춘 제품을 보완하세요. 아래 수집 복귀는 원문·AOI·기간·기존 선택을 보존하며 이 세부 의도를 추천에 반영합니다.</p>}
   <button type="button" disabled={confirmed} onClick={onConfirm}>{confirmed?'세부 분석 확정됨':'이 세부 분석 확인'}</button>
  </>}
  <Link className="download-link" href="/" onClick={onOriginal}>같은 조건으로 자료 보완하기</Link>
  {confirmed&&(capabilities.preprocessing||capabilities.common)&&<section aria-label="세부 분석 전처리 계획"><details className="collection-help"><summary>이 분석에 적용하는 전처리</summary><p>자동 실행하지 않습니다. 필수는 해당 계산을 할 때의 조건이며, 미지원 작업은 실행할 수 없습니다. 원본을 덮어쓰지 않습니다.</p>{task?.preprocessing.map(p=><div key={p.id}><b>{p.label} · {{required:'필수',optional:'선택',unnecessary:'불필요'}[p.requirement]}</b><p>{p.reason}</p><small>{p.requirement==='unnecessary'?'이번 세부 분석에 제안하지 않음':p.engine?'기존 '+p.engine+' 내부에서 지원 · 자료/QA 게이트 통과 필요':'실행 엔진 미지원 · 독립 처리 버튼 없음'}</small></div>)}</details></section>}
 </section>;
}
