'use client';
import type {useConditionInput} from '@/lib/useConditionInput';
type InputState=ReturnType<typeof useConditionInput>;
const labels:Record<string,string>={purpose_type:'분석 목적',analysis_target:'분석 대상',temporal_mode:'비교 형태',observation_need:'구름·야간 관측',resolution_m:'요청 해상도(m)',target_size_m:'대상 크기(m)',max_cloud_cover:'장면 구름량 상한(%)',reference_date:'비교 기준일'};
const places:Record<string,string>={resolved:'위치 확인 완료',absent:'지역 미지정',ambiguous:'후보 선택 필요',unsupported:'공간 자료 미지원',failed:'위치 검색 실패',lookup_required:'위치 검색 대기',loading:'위치 검색 중',not_configured:'위치 서비스 미설정',needs_confirmation:'범위 확인 필요',no_results:'검색 0건',limited:'요청 제한',timeout:'위치 검색 시간 초과',authentication_failed:'위치 서비스 인증 실패',invalid_response:'위치 응답 검증 실패'};
export default function AutomaticConditions({state:s}:{state:InputState}){
 const {proposal:p,form,aiConfig:c}=s,region=p?.region,boundary=region?.boundary;
 if(s.manualMode)return <div className="automatic-conditions" data-testid="automatic-conditions" data-config-ready={!!c}>
  <strong>직접 입력 모드</strong><p>목적·기간·AOI를 지정하세요. AI 호출 없이 검색합니다.</p>
  <button type="button" onClick={s.showAI}>자연어 입력으로 전환</button>
  {s.error&&<details><summary>이전 AI 오류 확인</summary><p>{s.error}</p></details>}
 </div>;
 const status=s.manualMode?'직접 입력 모드':s.pending?'해석·위치 확인 중':s.phase==='interrupted'?'해석 결과 확인 필요':s.phase==='failed'?'AI 해석 실패':s.blocking&&p?'AI 해석 완료 · 조건 확인 필요':['succeeded','cached','cached_local'].includes(p?.engine?.status||'')?'AI 해석 성공':s.aoiConfirmed&&form.purposeType&&form.start&&form.end&&form.start<=form.end?'검색 조건 준비됨':'조건 입력';
 const action=s.pending?'해석을 기다리세요. 영상 검색은 자동 실행하지 않습니다.':s.phase==='interrupted'&&!s.manualMode?'이전 요청의 완료 여부가 미확인입니다. 자동으로 다시 전송하지 않습니다.':s.phase==='failed'&&!s.manualMode?p?.engine?.status==='quota_exceeded'?'운영자의 OpenAI API 크레딧·한도 확인이 필요합니다. 반복 재시도 대신 직접 입력으로 계속할 수 있습니다.':'아래 실패 원인을 확인한 뒤 재시도하거나 직접 입력으로 계속하세요.':s.conflicts.length?'직접 수정값을 유지할지 문장 값을 다시 적용할지 선택하세요.':region?.status==='ambiguous'?'아래 후보의 주소를 확인하고 지역을 선택하세요.':p?.event_reference_required&&!form.referenceDate?'전후 비교 기준일을 직접 확인하세요. AI 해석을 다시 할 필요는 없습니다.':!form.purposeType?'분석 목적을 입력하거나 아래에서 직접 선택하세요.':!form.start||!form.end?'분석 시작일과 종료일을 확인하세요.':!s.aoiConfirmed?'지도에서 영역을 선택하거나 좌표를 입력·확정하세요.':s.blocking?'확인이 필요한 조건을 해결한 뒤 검색하세요.':'추천 제품을 확인한 뒤 위성영상 검색을 누르세요.';
 return <div className="automatic-conditions" data-testid="automatic-conditions" data-config-ready={!!c}>
  <div className="condition-status" role="status" aria-live="polite"><strong>{status}</strong><p>{action}</p></div>
  <p className="ai-cost-notice" id="ai-cost-notice">문장이 OpenAI로 자동 전송되며 사용량·비용이 발생할 수 있습니다.</p>
  {s.manualMode&&<p>현재 문장 대신 직접 지정한 조건을 사용합니다.</p>}
  {p&&<p>해석된 조건: {region?.mentioned_text||'지역 미지정'} / {p.period.status==='resolved'?p.period.start+'–'+p.period.end+' (UTC)':'기간 미지정/확인 필요'}</p>}
  {p&&s.blocking&&region&&!['absent','resolved'].includes(region.status)&&<p>{places[region.status]} · {region.message}</p>}
  {p&&s.blocking&&s.phase!=='failed'&&p.messages.map((v,i)=><p key={i} className="warning">{v}</p>)}
   {region?.status==='ambiguous'&&<fieldset><legend>지역 후보·주소·상위 지역 확인</legend>{region.candidates?.map(v=><div key={v.id}><button type="button" onClick={()=>s.chooseRegion(v.id)}>{v.name}</button><p>{v.official_name} · {v.parent} · {v.admin_level}{v.center&&<> · 경도 {v.center[0]}, 위도 {v.center[1]}</>}</p></div>)}</fieldset>}
  {s.location&&<section aria-label="선택한 지도 위치"><strong>{s.location.name} · 위치 확인 완료</strong><p>지도 중심점입니다. 행정경계나 분석 범위를 확정한 것이 아닙니다. 분석할 영역은 지도·좌표로 직접 지정하세요.</p>{form.confirmed&&<p>기존 AOI를 유지했습니다. 이 위치와 다를 수 있습니다.</p>}<a href="#collection-map" onClick={s.newAoi}>새 위치에서 AOI 다시 지정</a><p>현재 AOI를 유지하려면 좌표와 지도 영역을 확인하세요.</p></section>}
  {form.boundary&&<p data-testid="confirmed-boundary">확정 AOI: {form.boundary.name} 행정경계 외접 범위 · 자동 설정 · 폴리곤 클리핑 미지원</p>}
  {s.conflicts.length>0&&<div role="alert"><p>직접 수정값 또는 AI 추론값 확인이 필요합니다. 해결 전 검색하지 않습니다.</p>{s.conflicts.map(v=><p key={v}>{v}</p>)}<button type="button" onClick={s.keepManual}>직접 수정값 유지</button><button type="button" onClick={s.reapply}>문장에서 다시 적용</button></div>}
  {s.error&&<p role="alert">{s.error}</p>}
  <div className="aoi-actions">{(p||s.error)&&<button type="button" disabled={s.pending||s.composing||!p&&!s.error} onClick={s.runAI}>AI 해석 재시도</button>}{s.pending&&<button type="button" onClick={s.cancel}>해석 취소</button>}<button type="button" onClick={s.useManual}>직접 입력으로 계속</button></div>
  <details className="ai-technical"><summary>AI 해석 상세·출처·사용량</summary>
  <p>{c?.message||'AI 설정 확인 중'} 설정 준비와 실제 AI 응답 성공은 별개입니다.</p>
   <p>입력 안정화 1.2초 또는 입력 종료 후 자동 해석합니다. 규칙 기반 대체 해석은 사용하지 않습니다. 새 문장을 입력하면 다시 AI 확인을 진행합니다.</p>
  {p&&<>
   <p>{p.engine?.status==='not_called'?'AI 미호출 · 직접 지명 입력':`AI ${p.engine?.provider||'미연결'} / ${p.engine?.model||'미설정'} · ${p.engine?.status}`} · 위치·AOI 확정은 별도 단계입니다.</p>
   <dl data-testid="condition-stages"><dt>목적 추출</dt><dd>{p.fields?.purpose_type?.value||'미지정'}</dd><dt>기간 검증</dt><dd>{p.period.status==='resolved'?'UTC 날짜 유효성 확인됨':p.period.status==='absent'?'날짜 미지정':'날짜 확인 필요'}</dd><dt>지명 추출</dt><dd>{region?.mentioned_text||'미지정'}</dd><dt>위치 검색</dt><dd>{region&&places[region.status]} · {region?.message}</dd><dt>공간 범위</dt><dd>{boundary?.status==='proposed'?'실제 행정경계 외접 범위 확인됨':region?.extent?'확인된 점·지정 거리의 외접 범위':boundary?.message||'자동 범위 설정 불가 · 직접 AOI 또는 주변 거리 필요'}</dd><dt>AOI 상태</dt><dd>{s.aoiConfirmed?'AOI 확정 완료':s.blocking?'미해결 조건 · 검색 차단':'직접 지정 필요'}</dd></dl>
   <details><summary>AI 값·원문 근거·명시/추론</summary>{Object.entries(p.fields||{}).map(([key,v])=><p key={key}><b>{labels[key]||key}</b>: {v.value??'미지정'} · {v.basis==='explicit'?'명시':v.basis==='inferred'?'AI 추론 · 확인 필요':'미지정'}{v.evidence&&<> · 근거: <q>{v.evidence}</q></>}</p>)}{p.period.status==='resolved'&&<p>기간: {p.period.start}–{p.period.end} UTC</p>}{p.comparison_periods?.map((v,i)=><p key={i}>{v.role==='before'?'전':'후'} 기간: {v.start||'미확정'}–{v.end||'미확정'}</p>)}</details>
   {(!s.blocking||s.phase==='failed')&&p.messages.map((v,i)=><p key={i} className="warning">{v}</p>)}
  </>}
  {s.location&&<small>출처: {s.location.source} · {s.location.parent} · 확인 {s.location.checked_at}. 카카오 점 좌표 자체는 행정경계가 아닙니다.</small>}
  {boundary?.status==='proposed'&&<div data-testid="boundary-proposal"><p><a href={boundary.source_url} target="_blank" rel="noreferrer">{boundary.source}</a> · {boundary.year} · 코드 {boundary.code} ({boundary.code_system})</p><p>{boundary.original_crs} → {boundary.crs} · 경도, 위도 순서 · {boundary.terms}</p><p>행정경계 외접 범위: {boundary.bbox?.join(' / ')}. 사각형에는 경계 바깥 지역도 포함됩니다. 폴리곤 클리핑 미지원.</p><small>{boundary.display_simplification}</small></div>}
   <button type="button" onClick={s.refreshAI}>AI 사용량 새로고침</button>
  {c&&<p data-testid="ai-usage">AI 호출 {c.usage.requests}회 · 캐시 {c.usage.cache_hits}회 · 실패 {c.usage.failed}회 · 보고 토큰 {c.usage.input_tokens}/{c.usage.output_tokens} · 비용 {c.usage.estimated_usd_reported_tokens==null?'미확인':'약 $'+c.usage.estimated_usd_reported_tokens.toFixed(6)} · 청구량 미확인 호출 {c.usage.unknown_usage_calls}회. 앱 한도: 분당 {c.limits.requests_per_minute}회·프로세스 {c.limits.requests_per_process}회·대기 {c.limits.timeout_seconds}초·출력 {c.limits.max_output_tokens||'미제공'}토큰. OpenAI 계정 한도와는 별개입니다.</p>}
  {region?.extent&&<p>확인된 위치 중심 반경 {region.extent.radius_m}m의 외접 사각형을 제안합니다. 좌표가 자동 입력되면 지도에서 확인하고 좌표 적용을 누르세요. 원형 영역이나 행정구역 전체가 아닙니다.</p>}
  <p>AI는 목적·UTC 기간·지명을 제안합니다. 실제 위치와 명시한 거리로 좌표를 자동 입력하고 영역 확정은 사용자가 합니다. 수동 좌표는 덮어쓰지 않습니다. 위성 검색·다운로드·픽셀 분석은 실행 버튼을 눌러야 시작합니다.</p>
  </details>
 </div>;
}
