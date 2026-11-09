'use client';
import ThermalValidation from './ThermalValidation';
import {asObject} from '@/lib/researchRecord';
import type {ProcessingJob} from '@/lib/types';
const labels:Record<string,string>={band_nodata_or_unobserved:'미관측·필수 밴드 NoData',base_qa_or_required_data:'관측 중 기본 QA·필수 자료 검사 제외',cloud_cirrus:'구름·권운 표식',cloud_dilated_cirrus:'구름·확장 구름·권운 표식',cloud_shadow:'구름 그림자 표식',snow:'눈·얼음 표식',saturated:'포화 표식',dark_or_unclassified:'어두운 영역·분류불명 표식',fill:'채움값 표식',st_uncertainty:'온도 불확실성 상한 초과·결측',cloud_distance:'구름 최소 거리 미달·결측',uncertainty_or_cloud_proximity:'온도 불확실성 또는 구름 거리로 제외',qa_nodata_numeric:'QA·NoData·수치 검사 전체 제외'};
const area=(value:number)=>Number.isFinite(value)?(value/1e6).toLocaleString('ko-KR',{maximumFractionDigits:4})+' km²':'미확인';
export default function ProcessingFailure({job,stale,now}:{job:ProcessingJob;stale:boolean;now:number}){
 if(job.status!=='failed')return null;
 const failure=job.failure,qa=failure?.qa;
 const retry=failure?.retry_at?Date.parse(failure.retry_at):NaN;
 const remaining=Number.isFinite(retry)?Math.max(0,Math.ceil((retry-now)/1000)):null;
 return <section aria-label="분석 보류 이유와 다음 행동">
  <h3>{stale?'이전 조건의 분석 보류':'분석 보류 이유와 다음 행동'}</h3>
  {asObject(failure).ml_validation?<><p>검증 기준을 통과하지 못했거나 추정 가능한 구름 결측이 없어 ML 파일을 만들지 않았습니다. 위 오류와 검증 기록을 확인하세요.</p><ThermalValidation value={asObject(failure).ml_validation}/></>:failure?.code==='transfer_quota'?<>
   <p>서버 전송 예산을 예약하지 못해 원본 픽셀 읽기를 시작하지 않았습니다. 영상 품질이 나쁘다는 뜻은 아닙니다.</p>
   <p>처리 시작 시 작업의 최대 입력 예산을 개인·공용 시간당 한도에 예약합니다. 실제 수신량과 다르며, 시작한 작업이 실패해도 예약은 해당 시간 창이 끝날 때까지 유지됩니다.</p>
   <p>{remaining===null?'재시도 가능 시각이 기록되지 않은 작업입니다.':remaining>0?`재시도 가능 시각: ${new Date(retry).toLocaleString('ko-KR')} · 약 ${Math.ceil(remaining/60)}분 남음`:'기록된 대기시간이 지났습니다. 현재 사용량을 다시 확인하도록 처리 계획 검사를 누르세요.'} 다른 작업의 사용량에 따라 다시 제한될 수 있습니다. 자동 재실행하지 않습니다.</p>
  </>:qa?.status==='checked_no_valid'?<>
   <p>필수 자료의 실제 픽셀 검사를 마쳤지만 분석에 사용할 공통 유효 픽셀이 없습니다. 아래 0은 검사된 유효 면적이며, 온도·지수 평균이 0이라는 뜻은 아닙니다. 분석 지도·ZIP은 생성하지 않았습니다.</p>
   <dl className="processing-metrics"><div><dt>검사한 AOI 면적</dt><dd>{area(qa.aoi_area_m2)}</dd></div><div><dt>공통 관측 면적</dt><dd>{area(qa.observed_area_m2)}</dd></div><div><dt>검사된 공통 유효 면적</dt><dd>{area(qa.valid_area_m2)}</dd></div></dl>
   {qa.qa_options.maximum_uncertainty_k!=null&&<p>이 작업의 온도 QA: 불확실성 상한 {qa.qa_options.maximum_uncertainty_k}K · 구름 최소 거리 {qa.qa_options.minimum_cloud_distance_km}km.</p>}
   <p>표식·제외 사유는 서로 겹칠 수 있으므로 면적을 더하지 마세요. 구름 표식은 출력 격자의 QA 근사이며 장면 전체 구름량과 다릅니다. 온도 불확실성·거리는 기본 QA를 통과한 영역에서 추가 검사한 값입니다.</p>
   {qa.scenes.map(scene=><details key={scene.id} open><summary>{scene.datetime.slice(0,10)} (UTC) · 실제 제외 사유</summary><p>{scene.id}</p><ul>{Object.entries(scene.exclusions_m2).map(([key,value])=><li key={key}>{labels[key]||key}: {area(value)}</li>)}</ul></details>)}
   <p>같은 검색 결과의 다른 촬영일을 선택해 새 계획을 검사하세요. 모든 날짜가 실패하면 기간·AOI를 직접 검토하세요. 이 결과만으로 기준을 완화하거나 구름 아래 온도를 추정하지 않습니다. QA 정책: {qa.qa_policy_version}</p>
  </>:<p>이 작업에는 상세 제외 통계가 기록되지 않았습니다. 위 오류만으로 구름·불확실성 등 개별 원인을 단정할 수 없습니다. 조건을 확인하고 다시 계획하면 새 검사 기록을 남깁니다.</p>}
 </section>;
}
