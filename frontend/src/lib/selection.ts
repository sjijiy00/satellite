import {sceneKey, type Scene} from './types';
export type CompareMode='sensor'|'temporal';
export function sameProduct(a:Scene,b:Scene) {
  return a.provider_id===b.provider_id && a.collection===b.collection && !!a.processing_level && a.processing_level===b.processing_level &&
    a.instruments.length>0 && [...a.instruments].sort().join('|')===[...b.instruments].sort().join('|');
}
export function defaultPair(items:Scene[],mode:CompareMode):string[] {
  const a=items.find(s=>s.purpose_plan?.group==='primary')||items[0];
  if(!a)return ['',''];
  const candidates=items.filter(b=>sceneKey(a)!==sceneKey(b));
  if(mode==='sensor')return [sceneKey(a),candidates.find(b=>b.collection!==a.collection)?sceneKey(candidates.find(b=>b.collection!==a.collection)!):candidates[0]?sceneKey(candidates[0]):''];
  const aTime=Date.parse(a.datetime||'');
  const b=candidates.filter(b=>sameProduct(a,b)&&Number.isFinite(aTime)&&Number.isFinite(Date.parse(b.datetime||''))&&Date.parse(b.datetime!)!==aTime)
    .sort((b,c)=>Math.abs(Date.parse(b.datetime!)-aTime)-Math.abs(Date.parse(c.datetime!)-aTime))[0];
  if(!b)return [sceneKey(a),''];
  return [a,b].sort((x,y)=>Date.parse(x.datetime!)-Date.parse(y.datetime!)).map(sceneKey);
}
export function selectionWarnings(a:Scene|undefined,b:Scene|undefined,mode:CompareMode):string[] {
  if(!a||!b)return ['두 영상을 모두 선택하세요.'];
  const warnings=[];
  if(sceneKey(a)===sceneKey(b))warnings.push('동일 Item을 두 번 선택했습니다. 서로 다른 영상을 선택하세요.');
  if(mode==='temporal') {
    if(!sameProduct(a,b))warnings.push('동일 센서·제품 조건이 확인되지 않습니다. 같은 컬렉션·센서·제품을 우선 선택하세요.');
    const before=Date.parse(a.datetime||''),after=Date.parse(b.datetime||'');
    if(!Number.isFinite(before)||!Number.isFinite(after))warnings.push('촬영 시각 미확인: 전후 순서를 판단할 수 없습니다.');
    else if(before>after)warnings.push('전후 순서가 역전되었습니다. 영상 1을 이전 시점으로 선택하세요.');
    else if(before===after)warnings.push('촬영 시각이 같아 전후 변화용 영상 쌍이 아닙니다.');
  }
  return warnings;
}
