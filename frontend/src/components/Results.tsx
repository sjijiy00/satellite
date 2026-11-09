'use client';
import {sceneKey} from '@/lib/types';
import {useEffect,useState,useId} from 'react';
import type {Scene, SearchResponse} from '@/lib/types';
import {sceneDay} from '@/lib/imageryExplorer';
import AssetDownloads from './AssetDownloads';
import SceneProvenance,{originalAccessLabel} from './SceneProvenance';
import ProviderPreview from './ProviderPreview';
import {useWorkSession} from '@/lib/workSession';
import {s2QualitySupported} from '@/lib/workflow';
function value(n: number | null,unit='') {return n==null?'미제공':n.toLocaleString('ko-KR',{maximumFractionDigits:2})+unit;}
function Preview({scene}:{scene:Scene}) {
  return <figure className="scene-preview"><ProviderPreview scene={scene} large/><figcaption>제공처 미리보기 · 원본 밴드/분석 결과/픽셀 QA가 아닙니다.</figcaption></figure>;
}
type BandState={bandKeys:Record<string,string[]>;onBands:(id:string,keys:string[])=>void};
function SceneCard({scene:s,rank,selected,onSelect,bandKeys,onBands}:{scene:Scene;rank:number;selected:string|null;onSelect:(id:string)=>void}&BandState) {
  const plan=s.purpose_plan,description=useId(),qualitySupported=s2QualitySupported(s,plan?.purpose||null);
  const selectedHere=selected===sceneKey(s),date=sceneDay(s),qa=s.pixel_quality;
  return <article data-testid="scene-card" data-scene-key={sceneKey(s)} className={'scene-card '+(selectedHere?'selected':'')}>
    <header className="scene-top"><span className="rank">{String(rank).padStart(2,'0')}</span><div>
      <p className="card-capture">{s.temporal_role==='daily_product'?'제품 날짜':s.end_datetime?'관측 시작일':'촬영일'} (UTC) <time dateTime={s.datetime||undefined}>{date||'미제공'}</time></p>
      <h3>{s.platform || '위성 미제공'} · {s.product_type||s.processing_level||s.collection}</h3>
      <p className="card-provider">{s.provider} · {s.collection}</p>
    </div></header>
    <section className="card-overview" aria-label="추천 이유와 처리 지원">
      <p><strong>{plan?.label||'목적 일치 미확인'}</strong> · {plan?.analysis||'활용 목적 미확인'}</p>
      <p data-testid="card-recommendation">추천 근거: {plan?.group_reason||s.evaluation.sensor_reason||'메타데이터 근거 미제공'}</p>
      {!!plan?.missing_bands.length&&<p className="warning">필요 밴드 미확인: {plan.missing_bands.join(' · ')}</p>}
      <p id={description} data-testid="card-processing" className="card-processing"><strong>앱 내 처리: {s.support?.analysis_methods?.length?'제품별 실행 후보':qualitySupported?'지원 조건 있음':s.provider_id==='planetary-computer'?'픽셀 처리 미지원':s.support?.processing||'실행 조건 확인 필요'}</strong><br/>{s.support?.analysis_methods?.length?s.support.processing:qualitySupported?'지원 S2 품질 검사·분석별 제품/밴드·원본 확보·면적 조건을 다시 확인합니다.':s.provider_id==='planetary-computer'?'PC 자료는 검색·원본 접근 경로를 제공하지만 현재 앱의 S2 픽셀 엔진 대상은 아닙니다.':s.support?.processing||'검색·원본 확보와 외부 GIS 활용을 확인하세요. 현재 제품에 S2 엔진을 자동 적용하지 않습니다.'}</p>
      <p className="card-access">원본 접근: {originalAccessLabel(s)}</p>
    </section>
    <button className="card-select" type="button" onClick={()=>onSelect(sceneKey(s))} aria-pressed={selectedHere} aria-describedby={description}>지도에서 선택</button>
    <p className="card-selection-state" role="status">{selectedHere?'현재 선택 영상':'미선택'}</p>
    <div className="scene-body"><Preview scene={s}/><dl className="card-quality" aria-label="구름·중첩·실제 픽셀 품질">
      <div><dt>전체 장면 구름량</dt><dd>{value(s.scene_cloud_cover,'%')}</dd><p>장면 메타데이터 · AOI 구름량 아님</p></div>
      <div><dt>AOI 기하학적 중첩</dt><dd>{value(s.overlap_percent,'%')}</dd><p>{s.geometry_role==='product_grid_extent'?'제품 격자 포함 · 유효 관측률 아님':'촬영 범위의 기하 중첩 · 유효 관측률 아님'}</p></div>
      <div className="card-pixel-qa"><dt>실제 AOI 픽셀 QA</dt><dd>{qa?.status==='checked'?'진단 결과 있음':qa?.status==='failed'?'검사 실패·미확인':'미검사'}</dd><p>{qa?.message||'AOI 유효 비율 미계산 · 구름량·중첩에서 추정하지 않습니다.'}</p></div>
    </dl></div>
    <details className="scene-metadata"><summary>촬영·제품·추천 상세</summary>
      <dl><div><dt>탑재체·센서</dt><dd>{s.instruments.join(' · ')||'미제공'}</dd></div><div><dt>촬영 시각 (UTC)</dt><dd>{s.datetime?.replace('T',' ').replace('Z','') || '미제공'}</dd></div>
      <div><dt>공간 해상도 · 메타데이터</dt><dd>{s.resolution_m.length?s.resolution_m.join(' / ')+' m':'미제공'}</dd></div>
      <div><dt>처리 수준 / 제품 유형</dt><dd>{s.processing_level || '미제공'} · {s.product_type||'미제공'}</dd></div>
      <div><dt>검색 시작일과 촬영일 차이</dt><dd>{value(s.evaluation.days_from_start,'일')}</dd></div></dl>
      <p>센서·밴드 근거: {s.evaluation.sensor_reason||'미제공'}</p><SceneProvenance scene={s}/>
      {plan&&<div className="purpose-plan"><strong>{plan.label} · 기본 추천 세트</strong><p>필요 제품 조건: {plan.product_status==='met'?'메타데이터 확인':plan.product_status==='not_met'?'미충족 · 참고 후보':'미확인'} · 픽셀 품질과 별개입니다.</p><p>기본 선택: <b>{plan.default_keys.join(' · ') || '추천 가능한 밴드 없음'}</b></p>
       <div className="visual-plan"><strong>추천 시각화: {plan.visual_title}</strong><p>{Object.entries(plan.visual_mapping).map(([name,key])=>name+': '+(key || '미제공')).join(' / ')}</p><p>{plan.visual_note}</p>{!!plan.visual_missing.length&&<p className="asset-restricted">시각화 밴드 부족: {plan.visual_missing.join(', ')}</p>}</div>
       <p>{plan.preprocessing}</p><p>제공처 visual은 자연색 참고 파일이며 목적별 추천 조합의 대체 자료가 아닙니다.</p>
      </div>}
      <details><summary>밴드별 해상도 메타데이터</summary>{s.band_details.length?<ul>{s.band_details.map(b=><li key={b.asset}>{b.asset} ({b.bands.join(', ')}) · {b.resolution_m.length?b.resolution_m.join('/')+' m':'미제공'}</li>)}</ul>:<p>밴드 메타데이터 미제공</p>}</details>
    </details>
    <AssetDownloads scene={s} selectedKeys={bandKeys[sceneKey(s)]} onKeys={keys=>onBands(sceneKey(s),keys)}/>
    <div className="scene-footer"><details><summary>Item ID·출처</summary><code>{s.id}</code><p>{s.provider}</p></details>{s.source_url?<a href={s.source_url} target="_blank" rel="noreferrer">원본 Item ↗</a>:<span>원본 링크 미제공</span>}</div>
  </article>;
}
function ResultGroup({title,description,items,selected,onSelect,primary,bandKeys,onBands}:{title:string;description:string;items:Scene[];selected:string|null;onSelect:(id:string)=>void;primary:boolean}&BandState) {
  const [page,setPage]=useState(0), count=Math.ceil(items.length/10);
  const itemKeys=items.map(sceneKey).join('|');
  useEffect(()=>{const index=items.findIndex(s=>sceneKey(s)===selected);if(index>=0)setPage(Math.floor(index/10));},[selected,itemKeys]);
  return <section className="result-group" aria-label={title} data-testid={primary?'primary-results':'other-results'}>
    <div className="group-heading"><h3>{title} <span>{items.length}건</span></h3></div>
    {!items.length?<p className="empty">이 그룹에 해당하는 영상이 없습니다. 다른 후보를 확인하거나 검색 조건을 바꿔 주세요.</p>:<div className="scene-grid">{items.slice(page*10,page*10+10).map((s,i)=><SceneCard key={sceneKey(s)} scene={s} rank={page*10+i+1} selected={selected} onSelect={onSelect} bandKeys={bandKeys} onBands={onBands}/>)}</div>}
    {count>1&&<nav className="pagination" aria-label={title+' 페이지'}><button disabled={page===0} onClick={()=>setPage(page-1)}>이전</button><span>{page+1} / {count} 페이지 · 페이지당 10건</span><button disabled={page+1===count} onClick={()=>setPage(page+1)}>다음</button></nav>}
  </section>;
}
export default function Results({data,selected,onSelect,activeDay}:{data:SearchResponse;selected:string|null;onSelect:(id:string)=>void;activeDay:string|null}) {
  const session=useWorkSession();
  const [localBands,setLocalBands]=useState<Record<string,string[]>>({});
  const bandKeys=session?.bands??localBands;
  const onBands=(id:string,keys:string[])=>session?session.setBands(id,keys):setLocalBands(previous=>({...previous,[id]:keys}));
  const visible=data.items.filter(s=>activeDay===null||sceneDay(s)===activeDay);
  const primary=visible.filter(s=>s.purpose_plan?.group==='primary');
  const other=visible.filter(s=>s.purpose_plan?.group!=='primary');
  return <section id="search-results" className="results" aria-label="검색 결과">
    <div className="section-title"><div><div className="eyebrow">SEARCH RESULTS</div><h2>위성영상 검색 결과 <span>{data.returned}</span></h2></div><span className="live-tag">{data.source==='live-stac'?'● 실제 제공처 검색 결과':'테스트 데이터 · 실제 검색 아님'}</span></div>
    <div className="search-status" data-testid="search-status" role="status">
      <strong>{data.outcome==='outside_scope'?'연결된 제품의 지원 범위 밖 · 검색 미실행':data.outcome==='failed'?'전체 검색 실패':data.outcome==='partial'?'부분 검색 완료 · 일부 컬렉션 미확인':data.outcome==='empty'?'전체 조회 완료 · 0건':'검색 응답 완료'}</strong>
      <details className="collection-help" key={JSON.stringify(data.query)} open={!!data.collection_statuses?.some(s=>!['success','empty'].includes(s.status))}><summary>제공처별 조회 내역·제한</summary>{data.collection_statuses?.map(s=><div className="collection-status" key={`${s.provider_id}/${s.collection}`}>
        <b>{s.provider_id&&`${s.provider_id} / `}{s.collection}</b> · {{success:'성공',empty:'빈 결과',partial:'부분 성공',failed:'실패',limited:'조회 제한',not_started:'미조회',outside_scope:'등록 지원 범위 밖 · 조회하지 않음'}[s.status]} · 반환 {s.returned}건 / 메타데이터 수신 {s.fetched}건 · 요청 {s.requests}회
        <p>{s.error||({total_limit:'전체 반환 한도',request_limit:'요청 횟수 상한',time_limit:'검색 시간 상한',invalid_metadata:'일부 메타데이터 처리 실패',exhausted:'마지막 페이지 확인',outside_supported_period:'앱에 연결한 제품·플랫폼의 기간 범위 밖 (전체 제공처 자료 부재 판정 아님)',purpose_not_supported:'선택 목적에 필요한 변수를 제공하는 등록 제품이 아님'}[s.reason]||s.reason)}</p>
        <small>{s.complete?'조회 완료':`미조회 범위: 현재 조건에서 남은 페이지·미반환 후보 (수량 ${s.has_more===true?'추가 후보 있음':s.has_more===false?'페이지는 끝났으나 일부 처리 실패':'미확인'})`} · 페이지에서 조회했으나 미반환 {s.buffered_not_returned}건 · 중복 제외 {s.duplicates}건 · 형식 오류 {s.invalid}건 · 추천 제품/밴드 조건 제외 {s.filtered??0}건{ s.last_datetime?` · 마지막 조회 촬영 시각 ${s.last_datetime}`:''}</small>
      </div>)}</details>
    </div>
    <p className="subtle">검색 기간 {data.query.start_date} — {data.query.end_date} · UTC</p>
    {!!data.access_guidance?.length&&<details className="access-guidance"><summary>부족한 제품·접근 제한 자료의 추가 제공처 안내 (장면 미확인)</summary><p>검색 0건·실패·지원 범위 밖·제품 미연결·인증 필요는 다른 상태입니다. 아래는 제품 취급 경로 안내이며 해당 AOI·기간을 추가 조회한 결과가 아닙니다. 다운로드 가능으로 보장하지 않습니다. 자격증명은 후속 단계의 서버 전용 설정에만 준비합니다.</p>{data.access_guidance.map(g=><article key={g.provider}><b>{g.provider} · {g.products}</b><p>필요 인증: {g.authentication}</p><p>{g.conditions}</p><a href={g.url} target="_blank" rel="noreferrer">공식 접근·발급 안내</a><small>이 경로의 현재 AOI·기간 장면: 미확인 · 확인일 {g.checked_on}</small></article>)}</details>}
    {data.collections&&<p className="subtle" data-testid="applied-search-selection">서버 최종 적용 컬렉션: {data.collections.join(' · ')} · {data.applied_recommendation?`추천 제품 조건 ${data.applied_recommendation}`:'컬렉션 선택 조건'} · AOI {data.query.bbox.join(', ')}</p>}
    {activeDay&&<p className="subtle" data-testid="active-day-results">{activeDay} 촬영 장면 {visible.length}건 표시 · 전체 검색 {data.returned}건</p>}
    <details className="collection-help"><summary>후보 분류·구름량·중첩을 읽는 방법</summary><strong>목적별 우선 추천 → 다른 위성·추가 후보</strong><p>분석 목적에 맞는 밴드와 시각화 세트를 기본 선택합니다. 센서 그룹은 고정 탐색 순서이며 그룹 안의 영상은 실제 메타데이터로 정렬합니다. 평가 점수가 아니며 실제 분석 적합성은 판정 보류입니다.</p>{data.recommendation?.purpose_type==='flood'&&<p><strong>침수·수역 목적: Sentinel-1 GRD 검색이 연결되어 있습니다. 이번에 조회한 컬렉션은 위 최종 적용 조건과 제공처 상태를 확인하세요. SAR 전처리·침수 분석은 미지원이며 광학 수역지수와 다른 관측량입니다.</strong></p>}<p>장면 구름량은 AOI 구름량이 아니며 기하학적 중첩은 유효 관측률이 아닙니다.</p></details>
    {data.truncated&&<p role="status" className="warning">일부 범위는 조회가 끝나지 않았습니다. 컬렉션별 상태와 중단 이유를 확인하세요. 총 상한은 {data.limit}건입니다. 기간·영역을 줄이거나 특정 위성만 선택해 추가 후보를 확인하세요.</p>}
    <details className="ranking"><summary>추천 순위 계산 근거와 조회 범위</summary><p>{data.ranking}</p><p>{data.notice}</p><p>식생·도시·수역의 광학 보완 후보는 Sentinel-2, 열환경은 Landsat를 먼저 제시하는 탐색 규칙입니다. 해상도·촬영일·관측 조건에 따라 대안이 더 유용할 수 있습니다.</p></details>
    {!data.items.length?<div className="empty"><h3>{data.outcome==='outside_scope'?'연결 제품의 지원 범위 밖입니다':data.outcome==='failed'?'검색 실패로 결과를 확인하지 못했습니다':data.outcome==='partial'?'확보한 영상이 없습니다 · 일부 검색 미확인':'검색 결과가 없습니다'}</h3><p>{data.outcome==='outside_scope'?'등록된 제품·기간·변수 범위 때문에 조회하지 않았습니다. 실제 자료 부재나 검색 0건을 의미하지 않습니다.':data.outcome==='failed'||data.outcome==='partial'?'검색 실패·미조회는 영상이 없다는 뜻이 아닙니다. 컬렉션 상태를 확인하고 다시 검색하세요.':'선택한 지역·기간·컬렉션의 영상을 찾지 못했습니다.'}</p></div>:<>
      <ResultGroup key={'primary-'+(activeDay||'all')} title="목적별 우선 추천" description="목적에 따라 먼저 탐색하는 센서 그룹입니다. 밴드 누락 여부와 영상 순위는 별도로 확인하세요." items={primary} selected={selected} onSelect={onSelect} primary bandKeys={bandKeys} onBands={onBands}/>
      <ResultGroup key={'other-'+(activeDay||'all')} title="다른 위성·추가 후보" description="다른 센서의 대안 후보입니다. 우선 그룹보다 항상 품질이 낮다는 뜻은 아닙니다. 각 카드의 추천 근거와 누락 항목을 확인하세요." items={other} selected={selected} onSelect={onSelect} primary={false} bandKeys={bandKeys} onBands={onBands}/>
    </>}
  </section>;
}
