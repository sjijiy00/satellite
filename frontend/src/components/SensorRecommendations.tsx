'use client';
import type {Recommendation,Scene,SensorCard} from '@/lib/types';
import {portalForProfile} from '@/lib/externalAccess';
export default function SensorRecommendations({recommendation,selectedScene,busy,onSelect,selectedCardId,start,end,bbox,aoiConfirmed}:{recommendation:Recommendation|null;selectedScene?:Scene;busy:boolean;onSelect:(card:SensorCard)=>void;selectedCardId:string|null;start:string;end:string;bbox:number[]|null;aoiConfirmed:boolean}) {
  if(!recommendation)return null;
  return <section className="sensor-recommendations" aria-label="탑재체·센서 추천">
    <h2>목적에 맞는 탑재체·센서</h2>
    <p>{recommendation.observation_requirement||recommendation.reasons[0]}</p>
    {!!recommendation.assumptions?.length&&<details className="sensor-assumptions"><summary>추천에 사용한 가정</summary><ul>{recommendation.assumptions.map(a=><li key={a}>{a}</li>)}</ul></details>}
    <div className="sensor-cards">{recommendation.cards?.map(card=>{
      const quality=selectedScene?.purpose_plan?.profile_id===card.id?selectedScene.pixel_quality:undefined;
      const portal=!card.app_support.search?portalForProfile(card.id):null;
      return <article className="sensor-card" key={card.id} data-testid={'sensor-'+card.id}>
        <span className="eyebrow">{card.observation}</span><h3>{card.payload}</h3><p>{card.platform_label}</p>
        <p><b>필요 제품:</b> {card.product}<br/><small>제공처: {card.provider_id||'기존 제공처'} · 검색 컬렉션: {card.collection||'미연결'}</small></p>
        <p><b>필수 밴드·변수:</b> {card.required_bands.map(b=>`${b.name}: ${b.description}`).join(' · ')}</p>
        <p><b>품질 자료:</b> {card.quality_materials.join(' · ')} <small>(존재·픽셀 검사와 별개)</small></p>
        <p data-testid="sensor-fit"><b>목적 관측 조건:</b> {{met:'관측 방식·제품 조건 충족 후보',conditional:'조건부 보완 후보',not_met:'필수 조건 미충족'}[card.fit.status]}<br/>{card.fit.reason}</p>
        <p><b>원관측:</b> {card.native_resolution}<br/><b>출력 격자:</b> {card.output_grid}</p>
        {!!card.analysis_options?.length&&<details><summary>가능한 대표 세부 분석·추가 조건</summary>{card.analysis_options.map(a=><p key={a.id}><b>{a.label}</b> · {a.data_candidate?'필요 변수의 제품 후보':'추가 변수/다른 제품 필요'} · {a.minimum_scenes}장면 이상<br/><small>{a.engine_supported?'앱 엔진 연결 후보 · 실제 조건 검사 필요':a.note}</small></p>)}</details>}
        <details><summary>불확실한 조건·제약</summary><ul>{card.constraints.map(c=><li key={c}>{c}</li>)}</ul></details>
        <div className="sensor-statuses">
          <p><b>앱 검색:</b> {card.app_support.search?'연결됨':'권장되지만 앱 내 검색 미지원'}<br/><b>처리:</b> {card.app_support.processing}<br/><b>다운로드:</b> {card.app_support.download}</p>
          <p data-testid="sensor-availability"><b>AOI·기간 가용성:</b> {{unsearched:'미검색 / 미확인',searched:'검색됨',none:'없음',failed:'검색 실패',outside_scope:'지원 범위 밖'}[card.availability.status]}<br/>{card.availability.message}</p>
          <p data-testid="sensor-qa"><b>선택 장면 픽셀 품질:</b> {quality?({not_checked:'미검사',checked:'기존 검사 결과',failed:'검사 실패'}[quality.status]):'미검사'}<br/>{quality?.message||'이 센서 카드 자체에 대한 픽셀 QA 판정은 없습니다.'}</p>
        </div>
        <details><summary>공식 근거 · {recommendation.checked_on}</summary><ul>{card.sources.map(s=><li key={s.url}><a href={s.url} target="_blank" rel="noreferrer">{s.title} ↗</a> · 확인 {s.checked_on}</li>)}</ul><small>규칙 {card.rule_version}</small></details>
        <button type="button" aria-pressed={selectedCardId===card.id} disabled={busy||!card.search_enabled} onClick={()=>onSelect(card)}>{!card.app_support.search?'앱 내 검색 미지원':card.fit.status==='not_met'?'필수 관측 조건 미충족':selectedCardId===card.id?'선택한 제품':'이 제품 선택'}</button>
        {portal&&<div className="external-source"><a href={portal.url} target="_blank" rel="noreferrer">{portal.name}에서 {card.payload} 직접 찾기 ↗</a><p>앱에서 검색한 결과가 아닙니다. 포털에서 {card.product}과 UTC 기간 {start||'미설정'} ~ {end||'미설정'}을 입력하세요. {aoiConfirmed&&bbox?`AOI 참고 좌표: ${bbox.join(', ')}.`:'분석 AOI는 아직 확정되지 않았습니다.'} {portal.access}</p></div>}
        {card.search_conditions&&<small className="sensor-search-note">{card.search_conditions.product_levels.join(' / ')} · 제품·필수 밴드 메타데이터 조건 적용. 현재 AOI·기간 유지.</small>}
      </article>;
    })}</div>
  </section>;
}
