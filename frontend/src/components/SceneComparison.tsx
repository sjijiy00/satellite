'use client';
import {useState,useEffect} from 'react';
import {sceneKey,type Scene,type SearchResponse,type PixelReport} from '@/lib/types';
import {defaultPair,selectionWarnings,type CompareMode} from '@/lib/selection';
import {post} from '@/lib/api';
import AnalysisConditions from './AnalysisConditions';
import ProviderPreview from './ProviderPreview';
import {useWorkSession} from '@/lib/workSession';

function Preview({scene}:{scene:Scene}) {
  const [failed,setFailed]=useState(false);
  if(scene.provider_id)return <ProviderPreview scene={scene} large/>;
  return scene.thumbnail&&!failed?<img src={scene.thumbnail} alt={scene.id+' 실제 제공처 미리보기'} onError={()=>setFailed(true)}/>:<div className="compare-no-image">{failed?'제공처 이미지에 접근하지 못했습니다':'공개 미리보기 미제공'}<small>임의의 영상으로 대체하지 않습니다.</small></div>;
}
const pct=(v:number|null)=>v===null?'미제공':v.toLocaleString('ko-KR',{maximumFractionDigits:2})+'%';

export default function SceneComparison({data,onQuality,onPairChange,pair,mode,onModeChange,metadataOnly=false}:{metadataOnly?:boolean;data:SearchResponse;onQuality?:(r:PixelReport)=>void;onPairChange:(pair:[string,string])=>void;pair:[string,string];mode:CompareMode;onModeChange:(mode:CompareMode)=>void}) {
  const session=useWorkSession();
  const items=data.items;
  const ids=pair;
  const setIds=(next:string[])=>onPairChange([next[0]||'',next[1]||'']);
  const [a,b]=ids.map(id=>items.find(s=>sceneKey(s)===id));
  const scenes=[a,b].filter((s):s is Scene=>!!s);
  const warnings=selectionWarnings(a,b,mode);
  const [geometry,setGeometry]=useState<{common_geometry:boolean|null;message:string}|null>(null);
  useEffect(()=>{
    setGeometry(null);
    if(mode!=='temporal'||!a||!b)return;
    let active=true;const controller=new AbortController();
    post<{common_geometry:boolean|null;message:string}>('selection-overlap',{bbox:data.query.bbox,geometry_a:a.geometry,geometry_b:b.geometry},controller.signal)
      .then(result=>{if(active)setGeometry(result);})
      .catch(()=>{if(active)setGeometry({common_geometry:null,message:'공통 촬영 영역 확인 요청에 실패했습니다. 다시 선택해 주세요.'});});
    return ()=>{active=false;controller.abort();};
  },[mode,a,b,data.query.bbox]);
  if(!items.length)return null;
  const dateGap=a?.datetime&&b?.datetime?Math.abs(Date.parse(a.datetime)-Date.parse(b.datetime))/86400000:null;
  const validGap=dateGap!==null&&Number.isFinite(dateGap)?dateGap:null;
  const cloudKnown=a?.scene_cloud_cover!=null&&b?.scene_cloud_cover!=null;
  return <section className="comparison" aria-label="여러 영상 비교와 해석">
    <div><div className="eyebrow">COMPARE & UNDERSTAND</div><h2>여러 영상 비교와 해석</h2>
    <label htmlFor={metadataOnly?"collection-comparison-mode":"comparison-mode"}>{metadataOnly?"수집 비교 목적":"비교 목적"}</label><select id={metadataOnly?"collection-comparison-mode":"comparison-mode"} value={mode} onChange={e=>{const next=e.target.value as CompareMode;onModeChange(next);setIds(defaultPair(items,next));}}><option value="sensor">센서 후보 비교</option><option value="temporal">전후 변화용 영상 선택</option></select>
    <p className="compare-intro">{mode==='sensor'?'센서별 후보의 메타데이터를 비교합니다.':'동일 컬렉션·센서·제품의 다른 촬영 시점을 우선 선택합니다. 영상 1은 이전, 영상 2는 이후입니다.'} 비교 목적을 바꾸면 기본 비교 쌍을 선택란에 제안합니다. 실행 전 현재 두 영상을 확인하세요. 아래 이미지는 제공처 원본 미리보기이며 AOI 합성·정합 결과가 아닙니다. 두 영상 촬영 범위는 위의 동일한 AOI 지도에서 보라·분홍 선으로 비교할 수 있습니다.</p>
    <div className="comparison-grid">{ids.map((id,i)=>{const scene=items.find(s=>sceneKey(s)===id);return <div className="compare-scene" key={i}>
      <label htmlFor={(metadataOnly?'collection-compare-':'compare-')+i}>{metadataOnly?'수집 비교 영상':'비교 영상'} {i+1}</label><select id={(metadataOnly?'collection-compare-':'compare-')+i} value={id} onChange={e=>setIds(ids.map((v,j)=>i===j?e.target.value:v))}><option value="">영상 선택</option>{items.map(s=><option key={sceneKey(s)} value={sceneKey(s)}>{s.platform||s.collection} · {s.datetime?.slice(0,10)||'날짜 미제공'} · {s.id}</option>)}</select>
      {scene?<><div className="comparison-image"><Preview key={sceneKey(scene)} scene={scene}/></div><strong>{scene.platform||'위성 미제공'}</strong><p className="asset-help">픽셀 QA: {scene.pixel_quality?.message||'미검사'}</p><dl><div><dt>장면 구름량</dt><dd>{pct(scene.scene_cloud_cover)}</dd></div><div><dt>AOI 기하 중첩</dt><dd>{pct(scene.overlap_percent)}</dd></div><div><dt>해상도 메타데이터</dt><dd>{scene.resolution_m.join(' / ')||'미제공'} {scene.resolution_m.length?'m':''}</dd></div></dl><p className="comparison-plan">추천 시각화: {scene.purpose_plan?.visual_title||'미제공'}<br/>{scene.purpose_plan?.visual_keys.join(' · ')}{scene.purpose_plan?.visual_missing.length? <><br/>필요 밴드 미제공: {scene.purpose_plan.visual_missing.join(', ')}</>:null}</p></>:<div className="compare-no-image">비교할 영상을 선택하세요.</div>}
    </div>;})}</div>
    <div className="comparison-analysis">{warnings.map(w=><p className="warning" role="status" key={w}>{w}</p>)}{mode==='temporal'&&a&&b&&<p role="status" data-testid="common-geometry">{geometry?.message||'공통 촬영 영역 확인 중…'}</p>}<h3>선택 영상에서 확인한 내용</h3>
      {!a||!b?<p>비교할 두 번째 영상을 선택하세요. 조회 결과가 1건이면 기간·범위를 넓혀 다시 검색하세요.</p>:<>
        <p><strong>촬영 시점:</strong> {validGap===null?'촬영 날짜 정보가 부족합니다.':validGap<1?'촬영 시각 차이가 24시간 미만입니다. 같은 관측 조건을 의미하지는 않습니다.':'촬영 시각 차이는 약 '+validGap.toFixed(1)+'일입니다. 같은 시점의 상태로 간주할 수 없습니다.'}</p>
        <p><strong>구름:</strong> {cloudKnown?(a.scene_cloud_cover===b.scene_cloud_cover?'두 영상의 장면 구름량 수치가 같습니다.':(a.scene_cloud_cover!<b.scene_cloud_cover!?'영상 1':'영상 2')+'의 전체 장면 구름량이 더 낮습니다.'):'구름량 정보가 누락되어 수치 비교를 보류합니다.'} 장면 구름량만으로 AOI 내부의 맑은 픽셀 비율은 알 수 없습니다.</p>
        <p><strong>공간 범위:</strong> 영상 1 {pct(a.overlap_percent)}, 영상 2 {pct(b.overlap_percent)}의 기하 중첩입니다. 빈 픽셀이나 구름 없는 관측을 보장하지 않습니다.</p>
        <p><strong>필요 밴드:</strong> {scenes.map((s,i)=>'영상 '+(i+1)+' '+(s.purpose_plan?.metadata_only?'제품 메타데이터만 확인 · 밴드/픽셀 미검사':s.purpose_plan?.missing_bands.length?'미확인 '+s.purpose_plan.missing_bands.join(', '):s.purpose_plan?'필수 밴드 메타데이터 확인':'미검사')).join(' / ')}.</p>
      </>}
      <p><strong>현재 결론: 판정 보류.</strong> {data.recommendation?.purpose_type==='flood'?'지금 자료로 침수 면적이나 침수 전후 변화를 확정할 수 없습니다. 사건 전후 시점·SAR 자료와 구름 마스크를 추가 검토하세요.':'밴드의 scale·offset과 품질 마스크를 확인하고 날짜·좌표계·픽셀 격자를 맞춘 뒤 분석해야 합니다.'}</p>
      <p className="asset-help">{metadataOnly?'메타데이터·제공처 미리보기만 비교합니다. 원본 수신·픽셀 QA·분석 완료가 아닙니다.':'위 비교는 STAC 메타데이터와 촬영 범위 기반입니다. A3 픽셀 품질과 A4 식생 NDVI 변화는 아래에서 각각 실제 검사할 수 있습니다.'}</p>
    </div>
    </div>{!metadataOnly&&mode==='temporal'&&a&&b&&<AnalysisConditions key={JSON.stringify([sceneKey(a),sceneKey(b),data.query,data.recommendation.purpose_type])} a={a} b={b} data={data} onQuality={onQuality}/>}
  </section>;
}
