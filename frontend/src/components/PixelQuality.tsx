'use client';
import {useEffect,useRef,useState} from 'react';
import {post} from '@/lib/api';
import {useWorkSession} from '@/lib/workSession';
import type {Scene,SearchResponse,PixelReport} from '@/lib/types';
import ChangeAnalysis from './ChangeAnalysis';
import {s2QualitySupported} from '@/lib/workflow';
const fmt=(v:number|null|undefined,unit='')=>v==null?'미확인':v.toLocaleString('ko-KR',{maximumFractionDigits:3})+unit;
const reasons:Record<string,string>={nodata:'SCL NoData',saturated:'포화·결함',dark_or_topographic_shadow:'어두운 영역·지형 그림자',cloud_shadow:'구름 그림자',unclassified:'분류불명',cloud_cirrus:'구름·권운',snow_ice:'눈·얼음',unknown_scl:'알 수 없는 SCL',band_nodata_or_mixed_invalid:'밴드 NoData·혼합된 제외 픽셀'};
export default function PixelQuality({a,b,data,reference,onQuality}:{a:Scene;b:Scene;data:SearchResponse;reference:string;onQuality?:(r:PixelReport)=>void}) {
  const session=useWorkSession();
  const [minimum,setMinimum]=useState(String(session?.settings.minimum||'70')),[report,setReport]=useState<PixelReport|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const version=useRef(0),controller=useRef<AbortController|null>(null);
  useEffect(()=>()=>{version.current++;controller.current?.abort();},[]);
  useEffect(()=>{version.current++;controller.current?.abort();setBusy(false);setReport(null);setError('');},[reference]);
  function invalidate(){version.current++;controller.current?.abort();setBusy(false);setReport(null);setError('');}
  const supported=s2QualitySupported(a,data.recommendation.purpose_type)&&s2QualitySupported(b,data.recommendation.purpose_type)&&a.collection===b.collection&&a.processing_level===b.processing_level&&a.instruments.join(',')===b.instruments.join(',');
  async function inspect(){
    if(session&&!session.canProcess([a,b]))return;
    invalidate();const current=version.current,abort=new AbortController();controller.current=abort;
    if(minimum.trim()===''||!Number.isFinite(Number(minimum))||Number(minimum)<0||Number(minimum)>100){setError('운영 기준은 0~100%로 입력하세요.');return;}
    if(reference&&(reference<data.query.start_date||reference>data.query.end_date)){setError('기준일은 검색 기간 안에 입력하세요.');return;}
    setBusy(true);
    try{
      const result=await post<PixelReport>('pixel-quality',{bbox:data.query.bbox,start_date:data.query.start_date,end_date:data.query.end_date,
        purpose_type:data.recommendation.purpose_type,reference_date:reference||null,minimum_valid_percent:Number(minimum),
        scene_a:{collection:a.collection,id:a.id},scene_b:{collection:b.collection,id:b.id}},abort.signal);
      if(current===version.current){setReport(result);onQuality?.(result);}
    }catch(e){if(current===version.current){const message=e instanceof Error?e.message:'픽셀 검사 요청 실패';setError(message);onQuality?.({status:'failed',error:message,common_valid_area_m2:null,common_valid_percent_aoi:null,common_valid_percent_observed:null,scenes:[]});}}
    finally{if(current===version.current)setBusy(false);}
  }
  return <section className="pixel-quality" aria-label="A3 픽셀 품질 진단">
<div><h3>A3 · 작은 AOI 픽셀 품질 진단</h3>
    <p>Sentinel-2 L2A 두 날짜의 SCL·필수 밴드를 실제로 읽습니다. 현재 AOI는 그대로 사용하며 최대 25 km²입니다. 큰 영역은 지도에서 작게 다시 선택하세요.</p>
    <p>공통 20 m 등적 격자 · 100,000셀 · 전송 64 MiB · 파일당 2 GB · 처리 60초 · 동시 작업 1개. 범위 읽기 미지원·상한 초과 시 중단합니다.</p>
    <label htmlFor="minimum-valid">최소 공통 유효율 운영 기준 (%)</label>
    <input id="minimum-valid" type="number" min="0" max="100" step="1" value={minimum} onChange={e=>{invalidate();setMinimum(e.target.value);session?.setSettings({minimum:e.target.value});}}/>
    <p>공통 촬영 영역 대비 기준입니다. 기본 70%는 조정 가능한 앱 운영 기준이며 과학적 적합성 판정이 아닙니다. 기준일은 위 A2 입력을 함께 사용합니다.</p>
    <button type="button" disabled={busy||!supported||!!session&&!session.canProcess([a,b])} onClick={()=>void inspect()}>{!supported?'Sentinel-2 L2A 쌍만 지원':busy?'실제 픽셀 진단 중…':'작은 AOI 픽셀 진단'}</button>
    {error&&<p role="alert">{error} · 검사 실패를 0%로 바꾸지 않습니다.</p>}
    {report&&<div data-testid="pixel-report">
      <p><strong>{{checked:'진단 완료',partial:'일부 진단 / 공통 유효율 미확인',failed:'진단 보류',limited:'상한 초과',busy:'다른 작업 실행 중'}[report.status]}</strong> · {report.error||report.conclusion}</p>
      <dl className="conditions-coverage">
        <div><dt>AOI 전체 면적</dt><dd>{fmt(report.aoi_area_m2,' m²')}</dd></div>
        <div><dt>두 시점 공통 촬영 면적</dt><dd>{fmt(report.common_observed_area_m2,' m²')}</dd></div>
        <div><dt>두 시점 공통 유효 면적</dt><dd>{fmt(report.common_valid_area_m2,' m²')}</dd></div>
        <div><dt>공통 유효 / AOI 전체</dt><dd data-testid="pixel-aoi-percent">{fmt(report.common_valid_percent_aoi,'%')}</dd></div>
        <div><dt>공통 유효 / 공통 촬영 영역</dt><dd data-testid="pixel-common-percent">{fmt(report.common_valid_percent_observed,'%')}</dd></div>
        <div><dt>공통 촬영 영역 내 제외 면적</dt><dd>{fmt(report.common_excluded_area_m2,' m²')}</dd></div>
      </dl>
      {report.operational_threshold&&<p>운영 기준 {report.operational_threshold.minimum_percent}%: {report.operational_threshold.met==null?'판정 보류':report.operational_threshold.met?'충족':'미충족'} · 분석 가능 확정 아님</p>}
      <div className="pixel-scene-grid">{report.scenes?.map((s,i)=><article key={s.id||i}>
        <h4>영상 {i+1} · {s.status==='checked'?'진단 완료':'미확인'}</h4><p>{s.id} · {s.datetime}</p>{s.error&&<p>{s.error}</p>}
        <p>개별 유효 면적: {fmt(s.valid_area_m2,' m²')}<br/>개별 유효 / AOI 전체: {fmt(s.valid_percent_aoi,'%')}<br/>공통 촬영 영역 안의 개별 유효 면적: {fmt(s.valid_in_common_area_m2,' m²')}<br/>공통 영역 내 개별 유효 / 공통 촬영 영역: {fmt(s.valid_percent_common,'%')}</p>
        {s.exclusions_m2&&<details open><summary>제외 이유 · 개별 촬영 영역 내 면적</summary><dl>{Object.entries(s.exclusions_m2).map(([k,v])=><div key={k}><dt>{reasons[k]||k}</dt><dd>{fmt(v,' m²')}</dd></div>)}</dl></details>}
        {s.radiometry?.some(r=>r.status==='unknown')&&<p className="warning">반사도 scale/offset 누락·상충이 있습니다. 보정값은 미확인이고, 결과는 SCL·DN NoData 기반 품질 진단입니다. 지수·반사도 값은 제공하지 않습니다.</p>}
        <details><summary>실제 파일 헤더·window·보정 근거</summary><pre>{JSON.stringify({headers:s.headers,radiometry:s.radiometry},null,2)}</pre></details>
      </article>)}</div>
      <details><summary>SCL 정책·공통 격자·처리 기록</summary><pre>{JSON.stringify({policy:report.policy,grid:report.grid,transfer:report.transfer,provenance:report.provenance,version:report.version,checked_at:report.checked_at},null,2)}</pre></details>
      <p>유효 분류는 SCL 4·5·6입니다. NoData·포화·그림자·구름·권운·분류불명·눈/얼음은 제외합니다. 분류 마스크는 최근접, 반사도는 제외 픽셀을 먼저 마스킹한 평균 재표본화를 사용합니다. 보정 미확인 시 DN만 처리합니다. 해상도 향상이나 변화 분석 결과가 아닙니다.</p>
    </div>}
    </div>{data.recommendation.purpose_type==='vegetation'&&<ChangeAnalysis a={a} b={b} data={data} reference={reference} minimum={minimum} onQuality={onQuality}/>}
  </section>;
}
