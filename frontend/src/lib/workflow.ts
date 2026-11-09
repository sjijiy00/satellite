import type {CloudPlan,PixelReport,Purpose,Scene} from './types';

// UI routing only. Canonical Item, calibration, grids and pixel gates remain in FastAPI.
export function s2QualitySupported(scene:Scene|undefined|null,purpose:Purpose|null):boolean {
  return !!scene&&(!scene.provider_id||scene.provider_id==='earth-search')&&['vegetation','flood','urban'].includes(purpose||'')&&scene.collection==='sentinel-2-l2a'&&
    ['S2MSI2A','L2A'].includes(scene.processing_level||'')&&!!scene.platform&&scene.instruments.includes('msi')&&
    !!scene.purpose_plan&&!scene.purpose_plan.missing_bands.length&&scene.purpose_plan.product_status!=='not_met'&&
    !!scene.download_assets?.some(asset=>asset.key==='scl');
}
export function ndviPairSupported(a:Scene,b:Scene,purpose:Purpose|null){
  return purpose==='vegetation'&&s2QualitySupported(a,'vegetation')&&s2QualitySupported(b,'vegetation')&&a.platform===b.platform;
}
export function qualityState(report:PixelReport|null):'unchecked'|'good'|'degraded'|'failed' {
  if(!report)return 'unchecked';
  if(report.status!=='checked'||report.scenes?.some(s=>s.status!=='checked')||report.common_valid_area_m2==null)return 'failed';
  const exclusions=report.scenes?.reduce((sum,s)=>sum+Object.entries(s.exclusions_m2||{}).reduce((n,[key,v])=>
    n+(['nodata','cloud_shadow','dark_or_topographic_shadow','cloud_cirrus','band_nodata_or_mixed_invalid'].includes(key)?v:0),0),0)||0;
  return exclusions>0&&(report.operational_threshold?.met===false||report.common_valid_area_m2===0)?'degraded':'good';
}
export function observedGap(plan:CloudPlan|null):boolean {
  return !!plan&&['planned','blocked','succeeded'].includes(plan.status)&&!!plan.scenes?.length&&
    plan.scenes.every(s=>s.status==='checked')&&Number.isFinite(plan.composite_valid_area_m2)&&
    Number.isFinite(plan.remaining_gap_area_m2)&&(plan.remaining_gap_area_m2??0)>0;
}
