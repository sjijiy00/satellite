'use client';
import {useId,useState} from 'react';
import type {DayGroup,} from '@/lib/imageryExplorer';
import type {Scene} from '@/lib/types';
import SceneProvenance from './SceneProvenance';
import ProviderPreview from './ProviderPreview';

const amount=(v:number|null|undefined,unit='')=>v==null?'미확인':v.toLocaleString('ko-KR',{maximumFractionDigits:2})+unit;
function OriginalPreview({scene}:{scene:Scene}){
  return <ProviderPreview scene={scene} large/>;
}

function LayerOption({name,description,checked,available=true,unavailable='미실행/자료 없음',onChange}:{
  name:string;description:string;checked:boolean;available?:boolean;unavailable?:string;onChange:(value:boolean)=>void;
}){
  const id=useId();
  return <label className="imagery-layer" data-state={available?'available':'unavailable'}>
    <input type="checkbox" aria-labelledby={`${id}-name`} aria-describedby={`${id}-state ${id}-description`}
      checked={checked&&available} disabled={!available} onChange={e=>onChange(e.target.checked)}/>
    <span className="imagery-layer-copy"><span id={`${id}-name`} className="imagery-layer-name">{name}</span>{' '}
      <span id={`${id}-state`} className="imagery-layer-state">{available?(checked?'표시 중':'사용 가능'):unavailable}</span>
      <small id={`${id}-description`}>{description}</small>
    </span>
  </label>;
}

export default function ImageryExplorer({days,total,activeDay,onDay,scene,showPreview,onPreview,showFootprints,onFootprints,
  qualityReady,analysisReady,observedEstimateReady,estimateReady,showQuality,onQuality,showAnalysis,onAnalysis,
  showObservedEstimate,onObservedEstimate,showEstimated,onEstimated,outside,unknownDate}:{
  days:DayGroup[];total:number;activeDay:string|null;onDay:(day:string|null)=>void;scene:Scene|null;
  showPreview:boolean;onPreview:(value:boolean)=>void;showFootprints:boolean;onFootprints:(value:boolean)=>void;
  qualityReady:boolean;analysisReady:boolean;observedEstimateReady:boolean;estimateReady:boolean;showQuality:boolean;onQuality:(value:boolean)=>void;
  showAnalysis:boolean;onAnalysis:(value:boolean)=>void;showObservedEstimate:boolean;onObservedEstimate:(value:boolean)=>void;
  showEstimated:boolean;onEstimated:(value:boolean)=>void;outside:number;unknownDate:number;
}){
  return <section className="imagery-explorer" aria-label="날짜별 영상 탐색과 레이어">
    <div className="eyebrow">DATE × AOI × SCENE</div><h2>날짜별 실제 영상</h2>
    <p>현재 검색의 {total}건을 UTC 촬영일로 묶었습니다. 날짜를 누르면 아래 목록과 지도 강조가 같은 장면으로 이동합니다.</p>
    {(outside>0||unknownDate>0)&&<p className="warning" role="status">확정 기간 밖 {outside}건, 촬영일 미확인 {unknownDate}건은 날짜 탐색·지도·비교에 넣지 않았습니다. 제공처 원본의 날짜를 확인하세요.</p>}
    {!days.length?<p className="empty">현재 기간에 날짜가 확인된 실제 결과가 없습니다. 검색 상태를 확인하세요.</p>:<div className="imagery-days" role="group" aria-label="촬영 날짜">
      <button type="button" aria-pressed={activeDay===null} onClick={()=>onDay(null)}>전체 · {total}건</button>
      {days.map(group=><button type="button" key={group.day} aria-pressed={activeDay===group.day} onClick={()=>onDay(group.day)}>
        {group.day} <b>{group.count}건</b>{group.cloudUnknown>0&&<small>구름량 미확인 {group.cloudUnknown}</small>}
      </button>)}
    </div>}
    <div className="imagery-detail" data-testid="selected-scene-detail">
      <h3>지도·목록에서 선택한 영상</h3>
      {!scene?<p>선택한 영상이 없습니다. 날짜나 지도 촬영 범위, 결과 카드를 선택하세요.</p>:<>
        <div className="imagery-scene-heading">
          <strong>{scene.platform||'위성 미제공'}</strong>
          <time dateTime={scene.datetime||undefined}>{scene.datetime&&Number.isFinite(Date.parse(scene.datetime))?new Date(scene.datetime).toISOString().replace('T',' ').replace('.000Z',' UTC').replace('Z',' UTC'):'촬영일 미확인'}</time>
          <span className="imagery-product">제품 · {scene.processing_level||'미제공'}</span>
        </div>
        <dl className="imagery-facts"><div><dt>해상도 메타데이터</dt><dd>{scene.resolution_m.length?scene.resolution_m.join(' / ')+' m':'미제공'}</dd></div>
          <div><dt>제공처</dt><dd>{scene.provider||'미제공'}</dd></div>
          <div><dt>AOI 기하 중첩</dt><dd>{amount(scene.overlap_percent,'%')}<small>촬영 범위의 기하 중첩 · 픽셀 품질 아님</small></dd></div>
          <div><dt>장면 전체 구름량</dt><dd>{amount(scene.scene_cloud_cover,'%')}<small>장면 메타데이터 · AOI 구름량 아님</small></dd></div>
          <div className="imagery-quality"><dt>실제 AOI 픽셀 품질</dt><dd><span className="imagery-quality-state" data-state={scene.pixel_quality?.status||'not_checked'}>
            {scene.pixel_quality?.status==='checked'?'검사 결과 있음':scene.pixel_quality?.status==='failed'?'검사 실패·미확인':'미검사'}</span>
            <small>{scene.pixel_quality?.message||(scene.pixel_quality?.status==='checked'?'실제 검사 근거를 확인하세요. 분석 가능 확정은 아닙니다.':scene.pixel_quality?.status==='failed'?'품질 수치는 미확인입니다.':'실제 픽셀 검사를 실행한 뒤 확인할 수 있습니다.')}</small>
          </dd></div></dl>
        <details className="imagery-evidence" key={`${scene.provider_id}/${scene.collection}/${scene.id}`}><summary>Item ID·추천 근거</summary>
          <p>원본 Item ID: <code>{scene.id}</code></p>
          <p>컬렉션: {scene.collection} · 탑재체: {scene.instruments.join(' · ')||'미제공'}</p>
          <p>추천 근거: {scene.purpose_plan?.group_reason||scene.evaluation.sensor_reason}. 필수 밴드: {scene.purpose_plan?.analysis_keys.join(' · ')||'미확인'}.</p>
          <SceneProvenance scene={scene}/>
        </details>
      </>}
    </div>
    <fieldset className="imagery-layers"><legend>표시 레이어와 근거</legend>
      <LayerOption name="실제 Item 촬영 범위" description="STAC 기하 메타데이터 · 유효 관측 범위가 아님" checked={showFootprints} onChange={onFootprints}/>
      <LayerOption name="선택 영상 원본 미리보기" description={scene?.preview_diagnostic?.message||(scene?.thumbnail?'제공처 이미지 · 지도와 별도 패널에 표시':'선택 영상에 제공처 원본 이미지 URL 없음')}
        checked={showPreview} available={!!scene?.thumbnail||!!scene?.preview_diagnostic?.has_candidate} unavailable={scene?.preview_diagnostic?(scene.preview_diagnostic.status==='unsupported_format'?'형식 미지원':'Asset 없음'):'미제공'} onChange={onPreview}/>
      <LayerOption name="실제 AOI 품질 마스크" description={qualityReady?'실제 픽셀 검사에서 생성한 유효·제외 마스크':'실제 검사 결과의 지도 자료가 필요합니다.'}
        checked={showQuality} available={qualityReady} onChange={onQuality}/>
      <LayerOption name="실제 처리 결과" description={analysisReady?'실제 계산에서 생성한 래스터 시각화':'처리 결과의 지도 자료가 필요합니다.'}
        checked={showAnalysis} available={analysisReady} onChange={onAnalysis}/>
      {(observedEstimateReady||estimateReady)&&<>
        <LayerOption name="추정 작업의 실제 원관측 픽셀" description="실제 목표일 관측 · 별도 거짓색 레이어" checked={showObservedEstimate} available={observedEstimateReady} onChange={onObservedEstimate}/>
        <LayerOption name="ML 추정 픽셀" description="모델 추정값 · 원관측과 분리된 거짓색 레이어 · 실측 아님" checked={showEstimated} available={estimateReady} onChange={onEstimated}/>
      </>}
      <details className="imagery-layer-evidence"><summary>레이어 의미와 출처</summary>
        <p>촬영 범위는 STAC 기하 메타데이터입니다. 원본 미리보기는 제공처 이미지이며 지도 정합 래스터가 아닙니다.</p>
        <p>품질 마스크·처리 결과는 실제 픽셀 작업에서 생성된 지도 자료가 있을 때만 켤 수 있습니다. 미실행 또는 자료 미제공 상태는 수치 0을 뜻하지 않습니다.</p>
        <p>거짓색 미리보기는 정량 원본 밴드가 아닙니다. 추정 작업의 실제 관측과 ML 추정 픽셀은 별도 출처이며 추정값은 실측이 아닙니다. 정량 값·격자·픽셀 상태는 결과 GeoTIFF와 처리 기록에서 확인하세요.</p>
      </details>
    </fieldset>
    {scene&&showPreview&&<div className="imagery-preview"><OriginalPreview key={`${scene.collection}/${scene.id}`} scene={scene}/>
      <p className="asset-help">미리보기는 정량 분석 밴드나 구름 보정 결과가 아닙니다.</p></div>}
  </section>;
}
