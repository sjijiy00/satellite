import type {ProcessingJob} from '@/lib/types';
import {asObject} from '@/lib/researchRecord';
const n=(v:unknown,unit='')=>typeof v==='number'&&Number.isFinite(v)?v.toLocaleString('ko-KR',{maximumFractionDigits:3})+unit:'미계산';
export default function ResearchStatistics({job}:{job:ProcessingJob}){
 const result=asObject(job.result),stats=asObject(result.statistics),input=asObject(job.input),method=input.method_id;
 const rows:{label:string;value:unknown;unit:string}[]=[];
 const series=(label:string,value:unknown,unit:string)=>{const s=asObject(value);if(Object.keys(s).length)rows.push({label:label+' 평균',value:s.mean,unit},{label:label+' 최솟값',value:s.minimum,unit},{label:label+' 최댓값',value:s.maximum,unit});};
 if(stats.celsius)series('지표면 온도',stats.celsius,' ℃');
 else if(stats.target_celsius){series('대상 날짜 유효 영역 온도',stats.target_celsius,' ℃');series(stats.estimated_celsius?'ML 추정 영역 온도':'다른 날짜로 보충한 영역 온도',stats.estimated_celsius||stats.other_date_fill_celsius,' ℃');}
 else if(stats.before||stats.after){series('이전 지수',stats.before,'');series('이후 지수',stats.after,'');series('변화량 (이후−이전)',stats.difference,'');}
 else if('mean' in stats)series(String(result.analysis_label||'지수'),stats,'');
 else if('ndvi_before_mean' in result)for(const [label,key] of [['이전 NDVI 평균','ndvi_before_mean'],['이후 NDVI 평균','ndvi_after_mean'],['NDVI 변화 평균 (이후−이전)','ndvi_difference_mean']])rows.push({label,value:result[key],unit:''});
 if(!rows.length)return null;
 const regions=Array.isArray(stats.regions)?stats.regions.map(asObject):[];
 return <section aria-label="연구 결과 수치 요약"><h3>수치로 읽는 결과</h3>
  <dl className="processing-metrics">{rows.map(row=><div key={row.label}><dt>{row.label}</dt><dd>{n(row.value,row.unit)}</dd></div>)}</dl>
  {stats.target_celsius?<p>{stats.estimated_celsius?'실제 관측 영역과 ML 추정 영역의 통계를 분리했습니다. 추정 평균은 실측 평균이 아니며, 두 영역의 차이를 온도 변화로 해석하지 마세요.':'두 통계는 날짜와 공간 범위가 다릅니다. 합성 결과를 대상 날짜의 평균 온도나 날짜 간 온도 변화로 해석하지 마세요.'} 각각 해당 셀의 AOI 교차 면적으로 가중했습니다.</p>:<p>{stats.celsius?'온도는 섭씨이며 기온이 아닙니다.':'지수와 지수 변화량은 무차원이며 면적이나 변화율(%)이 아닙니다.'} 평균은 공통 유효 영역만 대상으로 합니다. 제외된 지역의 값은 채우지 않았으므로 전체 AOI나 도시 전체 평균으로 일반화하지 마세요.</p>}
  {['ndvi','ndbi','mndwi','mndwi_change','surface_temperature','hotspots','temperature_comparison'].includes(String(method))&&<p>평균은 유효 출력 셀과 AOI가 겹치는 면적을 가중치로 계산합니다. 최솟값·최댓값은 유효 셀 값이며 신뢰구간이 아닙니다.</p>}
  {'hot_area_m2' in stats&&<p>사용자 기준 초과 영역: {n(typeof stats.hot_area_m2==='number'?stats.hot_area_m2/1e6:null,' km²')} · 기준 {n(input.threshold,' ℃')} · 근거 {String(input.threshold_basis||'미기록')}</p>}
  {regions.length>0&&<><h4>확정한 두 영역 비교</h4>{regions.map((r,i)=><p key={i}>{String(r.label)}: 평균 {n(r.mean_celsius,' ℃')} · 유효 면적 {n(typeof r.valid_area_m2==='number'?r.valid_area_m2/1e6:null,' km²')} · 해당 영역 기준 유효율 {n(r.valid_percent,'%')}</p>)}<p>{String(regions[0]?.label)} − {String(regions[1]?.label)}: {n(stats.mean_difference_celsius_first_minus_second,' ℃')} · 영역 평균 차이이며 인과 효과나 통계적 유의성 검정이 아닙니다.</p></>}
  {'candidate_gain_area_m2' in stats&&<p>수역 후보 증가 {n(typeof stats.candidate_gain_area_m2==='number'?stats.candidate_gain_area_m2/1e6:null,' km²')} · 감소 {n(typeof stats.candidate_loss_area_m2==='number'?stats.candidate_loss_area_m2/1e6:null,' km²')} · 공통 유효 영역의 임계값 분류이며 실제 침수 확정이 아닙니다.</p>}
 </section>;
}
