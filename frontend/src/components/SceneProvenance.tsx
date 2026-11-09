import type {Scene} from '@/lib/types';

export function originalAccessLabel(scene:Scene){
 const assets=scene.download_assets||[];
 return assets.some(a=>a.authentication_required)?'인증 필요 파일 포함 · 다운로드 미검증':assets.some(a=>a.signing_required)?'계정 불필요 · 서버 단기 SAS · 접근 확인 필요':assets.some(a=>a.requester_pays)?'요청자 비용 자료 포함':assets.some(a=>a.direct_url)?'공개 파일 링크 있음 · 접근 미검증':'직접 링크 미제공';
}

/** Access states are independent of recommendations and actual pixel QA. */
export default function SceneProvenance({scene}:{scene:Scene}) {
  if(!scene.support)return null;
  return <div className="scene-provenance" data-testid="scene-provenance">
    <p><b>실제 검색됨</b> · {scene.provider} · {scene.product_type||scene.product_id||scene.collection}</p>
    <p>추천: {scene.purpose_plan?.profile_id&&scene.purpose_plan.product_status==='met'?'추천됨 · 등록된 목적 후보':'참고 자료 · 목적 일치 미확인'} · 픽셀 품질: {scene.pixel_quality?.message||'미검사'}</p>
    <p>원본 접근: {originalAccessLabel(scene)}</p>
    <p>미리보기: {scene.preview_diagnostic?.has_candidate?'실제 제공처 후보 있음 · 접근 확인 후 표시':'미리보기 미제공'}{scene.collection==='noaa-viirs-ndvi-cdr'?' · NetCDF를 이미지로 표시하지 않습니다. 대용량 전체 파일의 자동 미리보기 생성은 미지원입니다.':''}</p>
    <p>처리 지원: {scene.support.processing}</p>
    {scene.hls&&<details><summary>HLS 제품·품질 자료·이용 출처</summary><p>{scene.hls.short_name} v{scene.hls.version} · 30 m 광학 시계열. 지표면온도·구름 복원 결과가 아닙니다.</p><p>{scene.hls.scale_note}</p><p>{scene.hls.temporal_note}</p><p>Fmask 파일 제공 여부와 실제 픽셀 QA 실행은 별개입니다. 타일 범위는 유효 관측률이 아닙니다.</p><a href={'https://doi.org/'+scene.hls.doi} target="_blank" rel="noreferrer">NASA/LP DAAC 제품 DOI · 출처 표시</a></details>}
    <dl className="imagery-facts">
      <div><dt>원래 관측 해상도</dt><dd>{scene.native_resolution||'미제공'}</dd></div>
      <div><dt>출력 격자</dt><dd>{scene.output_grid||'미제공'}</dd></div>
    </dl>
    {scene.geometry_role==='product_grid_extent'&&<p>AOI 수치는 제품의 전 지구 격자 포함입니다. 실제 촬영 범위·픽셀 유효률이 아닙니다.</p>}
    {scene.end_datetime&&<p>제품 관측 기간 (UTC): {scene.datetime} — {scene.end_datetime} · {scene.collection==='viirs-vnp09ga-002'||scene.temporal_role==='daily_product'?'일별 집계는 한 순간의 촬영이 아닙니다.':'관측 시작·종료 시각입니다.'}</p>}
    {scene.source_product&&<details><summary>원천 제품 식별자·버전</summary><code>{scene.source_product.original_id}</code><p>{scene.source_product.version}</p></details>}
    {(scene.access_paths?.length||0)>1&&<details><summary>동일 원천 제품의 접근 경로 {scene.access_paths!.length}곳</summary><p>원천 제품·버전이 일치한 경로입니다. 파일 형식/바이트나 픽셀 처리가 같다는 보장은 아닙니다. 아래 Item은 실제 현재 결과에서 검색됐습니다.</p>{scene.access_paths!.map(p=><p key={`${p.provider_id}/${p.collection}/${p.id}`}>{p.provider} · {p.collection} · {p.id}{p.source_url&&<> · <a href={p.source_url} target="_blank" rel="noreferrer">원본 Item</a></>}</p>)}</details>}
    {scene.sar&&<details><summary>SAR 관측모드·편파·궤도·격자 메타데이터</summary><dl className="imagery-facts">{Object.entries(scene.sar).map(([k,v])=><div key={k}><dt>{k}</dt><dd>{v==null?'미제공':Array.isArray(v)?v.join(' / '):String(v)}</dd></div>)}</dl><p>GRD 디지털 값은 보정된 후방산란·침수 면적이 아닙니다. 격자 간격과 유효 해상도를 구분하세요.</p></details>}
  </div>;
}
