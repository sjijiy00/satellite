'use client';
import type {CloudPlan,EstimatePlan,MapPreview,PixelReport,ProcessingJob} from '@/lib/types';
import ThermalValidation from './ThermalValidation';
import RasterLegend from './RasterLegend';
import ResearchStatistics from './ResearchStatistics';
const number=(value:number|null|undefined,unit='')=>value==null||!Number.isFinite(value)?'미계산':value.toLocaleString('ko-KR',{maximumFractionDigits:2})+unit;
const status:Record<string,string>={completed:'실행·검증됨',skipped:'생략',not_recorded:'개별 근거 미기록',running:'실행 중',failed:'실패',cancelled:'취소'};
export default function ProcessingOutcome({job,stale}:{job:ProcessingJob;stale:boolean}){
 const report=job.result as Partial<PixelReport>|null,record=job.artifact?.execution_record;
 const composite=job.result as Partial<CloudPlan>|null,estimate=job.result as Partial<EstimatePlan>|null;
 const fill=(job.result as {cloud_fill?:{mode?:string;target_date:string;donor_date:string;original_valid_area_m2:number;filled_area_m2:number;composite_valid_percent_aoi:number;remaining_gap_area_m2:number}}|null)?.cloud_fill;
 const ml=fill?.mode==='ml_estimate';
 const layers=job.result?.map_layers;
 const summary=(job.result as {output_summary?:{sources:{id:string;datetime:string}[];crs:string;resolution_m:number;width:number;height:number;units:string[];formula:string;qa_policy_version:string}}|null)?.output_summary;
 const previews:MapPreview[]=layers?('quality' in layers?[layers.analysis,...layers.quality]:[layers.observed,layers.estimated]).filter((v):v is MapPreview=>!!v):[];
 return <section className="processing-outcome" aria-label="실제 처리 결과·실행 기록">
  {job.events?.length? <details><summary>서버 작업 진행 기록</summary><ol>{job.events.map(row=><li key={row.id}>{row.label} · {status[row.status]||row.status}{row.at&&<time dateTime={row.at}> · {new Date(row.at).toLocaleString('ko-KR')}</time>}</li>)}</ol></details>:null}
  {job.status==='succeeded'&&<>
   <h3>{stale?'이전 조건의 결과':'③ 결과'}</h3>
   {!fill&&<p>{report?.analysis_label||'카탈로그 방법'}</p>}
   {fill&&<section aria-label="구름 제거 전처리 결과"><h4>{ml?'ML 구름 결측 추정 결과':'다른 날짜 관측으로 보충한 결과'}</h4><p>대상 {fill.target_date} · {ml?'참조':'보충'} {fill.donor_date} (UTC)</p><dl className="processing-metrics cloud-result-metrics">
    <div><dt>실제 관측 면적</dt><dd>{number(fill.original_valid_area_m2/1e6,' km²')}</dd></div>
    <div><dt>{ml?'ML 추정 면적':'보충 면적'}</dt><dd>{number(fill.filled_area_m2/1e6,' km²')}</dd></div>
    <div><dt>남은 결측 면적</dt><dd>{number(fill.remaining_gap_area_m2/1e6,' km²')}</dd></div>
    <div><dt>{ml?'실측＋추정':'보충 후'} AOI 비율 · 정확도 아님</dt><dd>{number(fill.composite_valid_percent_aoi,'%')}</dd></div>
   </dl><p>{ml?'보라색은 ML 추정이며 실측이 아닙니다.':fill.filled_area_m2===0?'이번 실행에서 채워진 구름 영역은 없습니다.':'다른 날짜의 관측으로 보충한 값이며 대상 날짜의 실측이 아닙니다.'}</p></section>}
   <ThermalValidation value={(job.result as unknown as {ml_validation?:unknown})?.ml_validation}/>
   {!fill&&<dl className="processing-metrics" aria-label="AOI 실제 픽셀 품질">
    <div><dt>AOI 실제 QA</dt><dd>{report?.common_valid_percent_aoi==null?'유효율 미계산 · 아래 엔진 기록 확인':'실제 픽셀 검사·제외 적용'}</dd></div>
    <div><dt>확정 AOI 면적</dt><dd>{number(report?.aoi_area_m2,' m²')}</dd></div>
    <div><dt>공통 관측 면적</dt><dd>{number(report?.common_observed_area_m2,' m²')}</dd></div>
    <div><dt>유효 관측 면적</dt><dd>{number(report?.common_valid_area_m2,' m²')}</dd></div>
    <div><dt>AOI 기준 유효율</dt><dd>{number(report?.common_valid_percent_aoi,'%')}</dd></div>
    <div><dt>미관측·남은 결측</dt><dd>{number(report?.aoi_area_m2!=null&&report?.common_valid_area_m2!=null?report.aoi_area_m2-report.common_valid_area_m2:null,' m²')}</dd></div>
    <div><dt>관측 중 품질·수치 제외</dt><dd>{number(report?.common_excluded_area_m2,' m²')}</dd></div>
    <div><dt>관측 영역 기준 유효율</dt><dd>{number(report?.common_valid_percent_observed,'%')}</dd></div>
   </dl>}
   <details className="collection-help"><summary>상세 통계·계산식·출처</summary>
   <p>분모는 확정 AOI / 실제 관측 영역으로 구분합니다. 기하 중첩·장면 전체 구름량은 이 유효율이 아닙니다. 실패·미계산은 0%로 표시하지 않습니다.</p>
   <ResearchStatistics job={job}/>
   {summary&&<section aria-label="결과 출처·격자·계산식"><p>촬영일 (UTC): {summary.sources.map(s=>s.datetime.slice(0,10)).join(' · ')} · 출력 {summary.resolution_m}m / {summary.width}×{summary.height}셀 · 단위 {summary.units.join(' / ')}</p><p>계산식: {summary.formula} · QA {summary.qa_policy_version}</p><details><summary>실제 출력 좌표계·장면 식별자</summary><p>{summary.crs}</p>{summary.sources.map(s=><p key={s.id}>{s.id} · {s.datetime}</p>)}</details></section>}
   {record&&<p>사용 장면: {record.inputs.map((v,i)=>{const s=v as {id?:string};return <span key={i}>{s.id} </span>;})} · 촬영일과 QA·계산식은 아래 기록 및 manifest에 보관합니다.</p>}
   </details>
   {composite?.composite_valid_area_m2!=null&&<p>원래 유효 관측 {number(composite.original_valid_area_m2,' m²')} → 다른 날짜의 실측 픽셀 선택 후 {number(composite.composite_valid_area_m2,' m²')} · AOI 기준 {number(composite.composite_valid_percent_aoi,'%')} · 남은 결측 {number(composite.remaining_gap_area_m2,' m²')}. 사용 날짜·원본은 출처 파일로 확인하세요.</p>}
   {estimate?.areas&&<p>실제 관측 {number(estimate.areas.observed_m2,' m²')} / ML 추정 {number(estimate.areas.estimated_m2,' m²')} / 남은 결측 {number(estimate.areas.remaining_gap_m2,' m²')}. 추정은 실측 또는 구름 아래 참값이 아닙니다.</p>}
   {previews.length>0&&<div className="processing-previews" aria-label="실제 배열 결과 미리보기">{previews.map((layer,i)=><figure key={i}><img alt={layer.label} src={'data:image/png;base64,'+layer.png_base64}/><figcaption>{layer.label}<br/>{layer.source}</figcaption><RasterLegend layer={layer}/></figure>)}</div>}
   {record?<details className="collection-help"><summary>실행된 전처리·계산·파일 검증 기록</summary><p>아래는 성공 작업의 실제 기록입니다. 실행 전 설명이나 계획과 구분합니다.</p><ol>{record.steps.map(row=><li key={row.id}><strong>{row.label} · {status[row.status]||row.status}</strong><p>{row.detail}</p></li>)}</ol><details><summary>사용 입력·출력·격자</summary><pre>{JSON.stringify({inputs:record.inputs,outputs:record.outputs,grid:record.grid},null,2)}</pre></details></details>:<p>개별 실행 단계 기록이 없는 이전 작업입니다. 전처리 완료로 추정하지 않습니다.</p>}
   <details><summary>실제 수치·품질 정책·한계·출처</summary><pre>{JSON.stringify(job.result,(_key,value)=>_key==='png_base64'?undefined:value,2)}</pre></details>
  </>}
 </section>;
}
