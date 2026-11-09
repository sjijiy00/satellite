'use client';
import {useEffect,useRef,useState} from 'react';
import {post} from '@/lib/api';
import {createPortal} from 'react-dom';
import {useWorkSession} from '@/lib/workSession';
import type {ChangeReport,PixelReport,Scene,SearchResponse} from '@/lib/types';
import {ndviPairSupported} from '@/lib/workflow';

const number=(value:number|null|undefined,unit='')=>value==null?'미확인':value.toLocaleString('ko-KR',{maximumFractionDigits:4})+unit;

export default function ChangeAnalysis({a,b,data,reference,minimum,onQuality}:{a:Scene;b:Scene;data:SearchResponse;reference:string;minimum:string;onQuality?:(r:PixelReport)=>void}){
  const session=useWorkSession();
  const [outlet,setOutlet]=useState<HTMLElement|null>(null);
  useEffect(()=>{setOutlet(document.getElementById('analysis-outlet'));},[]);
  const [result,setResult]=useState<ChangeReport|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const version=useRef(0),controller=useRef<AbortController|null>(null);
  useEffect(()=>()=>{version.current++;controller.current?.abort();},[]);
  useEffect(()=>{version.current++;controller.current?.abort();setBusy(false);setResult(null);setError('');},[reference,minimum]);
  function clear(){version.current++;controller.current?.abort();setBusy(false);setResult(null);setError('');}
  async function run(){
    if(session&&(session.analysis.engine!=='ndvi_change'||!session.canProcess([a,b])))return;
    clear();const current=version.current,abort=new AbortController();controller.current=abort;
    if(minimum.trim()===''||!Number.isFinite(Number(minimum))||Number(minimum)<0||Number(minimum)>100){setError('공통 유효율 운영 기준은 0~100%로 입력하세요.');return;}
    if(reference&&(reference<data.query.start_date||reference>data.query.end_date)){setError('기준일은 검색 기간 안에 입력하세요.');return;}
    setBusy(true);
    try{
      const report=await post<ChangeReport>('change-analysis',{
        bbox:data.query.bbox,start_date:data.query.start_date,end_date:data.query.end_date,
        purpose_type:'vegetation',reference_date:reference||null,minimum_valid_percent:Number(minimum),
        scene_a:{collection:a.collection,id:a.id},scene_b:{collection:b.collection,id:b.id}},abort.signal);
      if(current===version.current){setResult(report);if(report.scenes?.length)onQuality?.({...report,status:report.status==='computed'?'checked':'failed'} as PixelReport);}
    }catch(e){if(current===version.current){const message=e instanceof Error?e.message:'변화 분석 요청 실패';setError(message);onQuality?.({status:'failed',error:message,common_valid_area_m2:null,common_valid_percent_aoi:null,common_valid_percent_observed:null,scenes:[]});}}
    finally{if(current===version.current)setBusy(false);}
  }
  function download(){
    if(!result?.artifact_base64)return;
    const bytes=Uint8Array.from(atob(result.artifact_base64),c=>c.charCodeAt(0));
    const url=URL.createObjectURL(new Blob([bytes.buffer as ArrayBuffer],{type:'application/zip'}));
    const link=document.createElement('a');link.href=url;link.download=result.artifact_name||'sentinel-2-ndvi-change.zip';
    document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);
  }
  const supported=ndviPairSupported(a,b,data.recommendation.purpose_type)&&(!session||session.analysis.engine==='ndvi_change');
  const content=<section className="change-analysis" aria-label="A4 식생 NDVI 변화 분석">
    <h3>④ 분석·내보내기 · A4 두 날짜 NDVI 변화</h3>
    <p>현재 AOI·기간·선택 영상으로 두 날짜 모두 유효한 픽셀의 NDVI를 계산합니다. 같은 위성 플랫폼·제품 기준선과 확인된 적색·근적외선 보정값이 필요합니다.</p>
    <button type="button" onClick={()=>void run()} disabled={busy||!supported||!!session&&!session.canProcess([a,b])}>{busy?'실제 NDVI 계산 중…':supported?'두 날짜 NDVI 계산':'A4 NDVI는 선택한 센서 조합 미지원'}</button>
    {error&&<p role="alert">{error}</p>}
    {result&&<div data-testid="change-report">
      <p><strong>{result.status==='computed'?'NDVI 계산 완료':'NDVI 계산 보류'}</strong> · {result.error||result.conclusion}</p>
      {result.status==='computed'&&<>
        <dl className="conditions-coverage">
          <div><dt>공통 촬영 면적</dt><dd>{number(result.common_observed_area_m2,' m²')}</dd></div>
          <div><dt>실제 분석 면적</dt><dd>{number(result.analysis_area_m2,' m²')}</dd></div>
          <div><dt>공통 촬영 중 제외 면적</dt><dd>{number(result.excluded_common_area_m2,' m²')}</dd></div>
          <div><dt>AOI 전체 중 제외 면적</dt><dd>{number(result.excluded_aoi_area_m2,' m²')}</dd></div>
          <div><dt>이전 NDVI 평균</dt><dd>{number(result.ndvi_before_mean)}</dd></div>
          <div><dt>이후 NDVI 평균</dt><dd>{number(result.ndvi_after_mean)}</dd></div>
          <div><dt>NDVI 차이 평균 (이후−이전)</dt><dd>{number(result.ndvi_difference_mean)}</dd></div>
        </dl>
        <p>AOI 경계는 부분 셀 면적으로 집계합니다. 변화량은 원인을 분류하거나 식생 증감을 확정하지 않습니다. 계절·촬영 조건을 함께 검토하세요.</p>
        <button type="button" onClick={download} disabled={!result.artifact_base64}>GeoTIFF 2개 + 처리기록 ZIP 저장</button>
        <p>ZIP: 전후·차이 3밴드 GeoTIFF, 공통 유효 마스크 GeoTIFF, 출처·보정·격자·처리 설정 JSON.</p>
      </>}
      <details><summary>검사 근거·제외 면적</summary><pre>{JSON.stringify({version:result.version,checked_at:result.checked_at,qa_excluded_area_m2:result.qa_excluded_area_m2,numeric_excluded_area_m2:result.numeric_excluded_area_m2,grid:result.grid,scenes:result.scenes,transfer:result.transfer,provenance:result.provenance},null,2)}</pre></details>
    </div>}
  </section>;
  return outlet?createPortal(content,outlet):content;
}
