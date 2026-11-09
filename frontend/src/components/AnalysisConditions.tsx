'use client';
import {useEffect,useRef,useState} from 'react';
import {post} from '@/lib/api';
import {useWorkSession} from '@/lib/workSession';
import type {Scene,SearchResponse,ConditionsReport,PixelReport} from '@/lib/types';
import PixelQuality from './PixelQuality';
const statusNames={pass:'통과',conditional:'조건부',unknown:'미확인',blocked:'불가'};
const number=(n:number|null,unit:string)=>n===null?'미확인':n.toLocaleString('ko-KR',{maximumFractionDigits:3})+unit;
export default function AnalysisConditions({a,b,data,onQuality}:{a:Scene;b:Scene;data:SearchResponse;onQuality?:(r:PixelReport)=>void}) {
  const session=useWorkSession();
  const [reference,setReference]=useState(String(session?.settings.reference||data.query.requested_reference_date||'')),[report,setReport]=useState<ConditionsReport|null>(null);
  const [busy,setBusy]=useState(false),[error,setError]=useState('');
  const version=useRef(0),controller=useRef<AbortController|null>(null);
  const supported=[a,b].every(s=>(!s.provider_id||s.provider_id==='earth-search')&&['sentinel-2-l2a','landsat-c2-l2'].includes(s.collection));
  useEffect(()=>()=>{version.current++;controller.current?.abort();},[]);
  function invalidate(){version.current++;controller.current?.abort();setBusy(false);setReport(null);setError('');}
  async function inspect(){
    if(!supported)return;
    invalidate();const current=version.current,abort=new AbortController();controller.current=abort;
    if(reference&&(reference<data.query.start_date||reference>data.query.end_date)){setError('기준일은 검색 기간 안에 입력하세요.');return;}
    setBusy(true);
    try{
      const result=await post<ConditionsReport>('analysis-conditions',{bbox:data.query.bbox,start_date:data.query.start_date,end_date:data.query.end_date,
        purpose_type:data.recommendation.purpose_type,reference_date:reference||null,
        scene_a:{collection:a.collection,id:a.id},scene_b:{collection:b.collection,id:b.id}},abort.signal);
      if(current===version.current)setReport(result);
    }catch(e){if(current===version.current)setError(e instanceof Error?e.message:'조건 검사 요청 실패');}
    finally{if(current===version.current)setBusy(false);}
  }
  return <section className="analysis-conditions" aria-label="두 영상 분석 조건 검사">
<div><h3>A2 · 두 영상 분석 조건 검사</h3>
    <p>선택한 두 원본 Item과 필수/품질 Asset 접근을 확인합니다. 파일 픽셀·구름 마스크는 읽지 않습니다.</p>
    <label htmlFor="reference-date">사건·변화 기준일 (UTC, 선택 입력)</label>
    <input id="reference-date" type="date" value={reference} min={data.query.start_date} max={data.query.end_date} onChange={e=>{invalidate();setReference(e.target.value);session?.setSettings({reference:e.target.value});}}/>
    <p>영상 1: 기준일 전날까지 · 영상 2: 기준일부터. 미입력 시 기준일 조건은 미확인입니다. 현재 검색 기간 {data.query.start_date} ~ {data.query.end_date}을 유지합니다.</p>
    {!supported&&<p className="warning">새 제공처 제품은 검색·메타데이터 비교만 지원합니다. A2–A4·관측 합성·ML 처리를 적용하지 않습니다.</p>}
    <button type="button" onClick={()=>void inspect()} disabled={busy||!supported||!data.recommendation.purpose_type}>{busy?'원본 조건 검사 중…':'두 영상 조건 검사'}</button>
    {error&&<p role="alert">{error} 검사 실패를 통과나 0%로 표시하지 않습니다.</p>}
    {report&&<div data-testid="conditions-report">
      <p><strong>A2 상태: {statusNames[report.status]}</strong> · {report.conclusion}</p>
      <dl className="conditions-coverage">
        <div><dt>영상 1 / AOI 기하 중첩</dt><dd>{number(report.coverage.scene_a_percent,'%')}</dd></div>
        <div><dt>영상 2 / AOI 기하 중첩</dt><dd>{number(report.coverage.scene_b_percent,'%')}</dd></div>
        <div><dt>두 시점 공통 촬영 면적</dt><dd>{number(report.coverage.common_area_m2,' m²')}</dd></div>
        <div><dt>공통 촬영 영역 / AOI 전체</dt><dd>{number(report.coverage.common_percent,'%')}</dd></div>
      </dl>
      <p>{report.coverage.method||'기하 메타데이터 미확인'} · 공통 유효 픽셀 비율은 미검사입니다.</p>
      <div className="condition-checks">{report.checks.map(c=><article key={c.id} data-testid={'condition-'+c.id}>
        <strong>{c.label} · {statusNames[c.status]}</strong><p>{c.reason}</p><p>다음 행동: {c.next_action}</p>
        {c.evidence!=null&&<details><summary>검사 근거</summary><pre>{JSON.stringify(c.evidence,null,2)}</pre></details>}
      </article>)}</div>
      <p>검사 시각 {report.checked_at} · {report.version} · 요청 {report.request_count}/{report.limits.max_requests}회</p>
      <p>HTTP HEAD는 접근 응답 검사입니다. 래스터 파일 헤더·픽셀은 읽지 않았으며, 분석 가능 판정은 보류합니다.</p>
    </div>}
    </div><PixelQuality a={a} b={b} data={data} reference={reference} onQuality={onQuality}/>
  </section>;
}
