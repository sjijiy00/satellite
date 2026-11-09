'use client';
import type {Scene} from '@/lib/types';
import {portalForCollection} from '@/lib/externalAccess';
import ManagedAssetAccess from './ManagedAssetAccess';
import {useWorkSession} from '@/lib/workSession';

export default function AssetDownloads({scene,initiallyOpen=false,selectedKeys,onKeys}:{scene:Scene;initiallyOpen?:boolean;selectedKeys?:string[];onKeys:(keys:string[])=>void}) {
  const session=useWorkSession();
  const assets=scene.download_assets || [], plan=scene.purpose_plan;
  const defaults=plan?.default_keys || [];
  const keys=selectedKeys??defaults, setKeys=onKeys;
  const selected=assets.filter(a=>keys.includes(a.key));
  const direct=selected.filter(a=>a.direct_url);
  const ordered=[...assets].sort((a,b)=>Number(defaults.includes(b.key))-Number(defaults.includes(a.key)));
  const portal=portalForCollection(scene.collection);
  function alternateFor(asset:typeof assets[number]) {
    if (asset.direct_url || asset.common_names.length!==1 || asset.roles.includes('visual')) return null;
    return assets.find(other=>other.key!==asset.key && other.direct_url && !other.roles.includes('visual') &&
      other.common_names.length===1 && other.common_names[0]===asset.common_names[0]) || null;
  }
  function saveLinks() {
    const text=['# '+(scene.provider_id?scene.provider_id+' / ':'')+scene.collection+' / '+scene.id,'# '+(plan?.label || '선택한 파일')+' — 원본 전체 장면 · 링크 접근 미검증',...direct.map(a=>a.direct_url)].join('\r\n');
    const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download=scene.id+'-links.txt';link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    session?.recordLinks(scene);
  }
  return <details className="asset-downloads" open={initiallyOpen}>
    <summary>밴드 선택·다운로드 · 선택 {selected.length} / {assets.length}개</summary>
    {!assets.length?<p>제공된 래스터 파일 링크가 없습니다. 다시 검색하거나 원본 STAC을 확인하세요.</p>:<div className="asset-content">
      <div className="band-actions"><button type="button" onClick={()=>setKeys(defaults)}>목적 추천으로 복원</button><button type="button" onClick={()=>setKeys(plan?.visual_keys || [])}>추천 시각화 밴드</button><button type="button" onClick={()=>setKeys(assets.map(a=>a.key))}>전체 선택</button><button type="button" onClick={()=>setKeys([])}>선택 해제</button></div>
      <p>분석·추천 시각화에 필요한 실제 파일과 제공된 품질 밴드를 기본 선택합니다. 전체 선택에는 같은 밴드의 다른 형식도 포함됩니다.</p>
      <div className="band-checklist">{ordered.map(a=><label className="band-choice" key={a.key}>
        <input type="checkbox" data-testid={'band-'+a.key} checked={keys.includes(a.key)} onChange={e=>setKeys(e.target.checked?[...keys,a.key]:keys.filter(k=>k!==a.key))}/>
        <span><strong>{a.key}</strong>{defaults.includes(a.key)&&<em>목적 추천</em>}<small>{a.title}{a.authentication_required?' · 인증 필요 · 다운로드 미검증':a.signing_required?' · 계정 불필요 · 서버 단기 SAS · 접근 확인 필요':a.direct_url?' · 직접 링크 · 접근 미검증':' · 브라우저 직접 다운로드 불가'}{!a.direct_url&&alternateFor(a)?' · 같은 밴드의 다른 형식 링크 있음':''}{(a.roles||[]).includes('visual')?' · 자연색 참고용, 분석 밴드 아님':''}</small><small>{a.filename||a.href.split('/').pop()} · {a.media_type} · {a.size_bytes==null?'크기 미확인':`${a.size_bytes.toLocaleString()} bytes`} · {a.provider||scene.provider}</small></span>
      </label>)}</div>
      <div className="download-selection"><strong>선택한 파일 {selected.length}개 · 직접 링크 {direct.length}개</strong><button type="button" disabled={!direct.length} onClick={saveLinks}>선택 링크 목록 저장 (.txt)</button></div>
      {scene.provider_id&&<p className="asset-help">필요한 밴드를 선택한 뒤 <strong>바로 다운로드</strong>를 누르세요. 접근 확인 후 파일을 저장합니다. 링크 목록(.txt)은 영상 파일이 아닙니다.</p>}
      {scene.provider_id==='planetary-computer'&&<p className="asset-help">Planetary Computer는 로그인 없이 사용할 수 있습니다. 직접 링크가 0개여도 위 순서로 다운로드할 수 있으며, 임시 접근 주소는 서버가 준비합니다.</p>}
      {scene.collection==='landsat-c2-l2'&&<p className="asset-help">Landsat는 서버의 USGS 연결로 같은 제품·밴드 원본을 받습니다. EarthExplorer로 이동할 필요가 없습니다. 계정 권한과 파일 제공 여부는 클릭 시 확인합니다.</p>}
      {scene.provider_id&&<ManagedAssetAccess scene={scene} keys={keys}/>}
      <details className="collection-help"><summary>제공처 링크·밴드 추천 기준</summary>
        <p className="asset-help">아래 외부 링크의 접근 여부는 별도 확인이 필요합니다. 앱의 다운로드 완료 기록과는 다릅니다.</p>
        {plan?.rule_version&&<small>밴드 추천 기준: {plan.rule_version}</small>}
      </details>
      <div className="selected-links">{selected.map(a=><div key={a.key}>{a.direct_url?<a className="download-link" href={a.direct_url} target="_blank" rel="noreferrer" download>{a.key} 다운로드 ↗</a>:<details><summary>{a.key} · {a.access_note}</summary><code className="asset-url">{a.href}</code>{alternateFor(a)&&<p>같은 Item·밴드의 다른 형식: <a href={alternateFor(a)!.direct_url!} target="_blank" rel="noreferrer">{alternateFor(a)!.key} 직접 링크 열기 ↗</a> (접근 상태 미검사)</p>}{portal&&<p>대체 경로: <a href={portal.url} target="_blank" rel="noreferrer">{portal.name}에서 직접 찾기 ↗</a><br/>Item ID: <code>{scene.id}</code>. 포털에서 제품과 촬영일을 다시 확인하세요. {portal.access}</p>}</details>}</div>)}</div>
      <p className="asset-help">제공처 원본 전체 장면이며 AOI 추출본이 아닙니다. 파일당 수십~수백 MB 이상일 수 있고 개별 접근 상태는 미검사입니다. 인증·요청자 비용 동의는 자동 수행하지 않습니다.</p>
    </div>}
  </details>;
}
