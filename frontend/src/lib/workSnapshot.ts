// Browser-tab metadata only. Never persist access receipts, tokens, signed URLs,
// raster bytes, execution confirmations or plan digests.
export const SNAPSHOT_KEY='satellite-workflow-v1';
const forbidden=/token|password|secret|authorization|cookie|receipt|download_url|artifact_base64|png_base64|confirmation_digest|plan_id|__proto__|constructor|prototype/i;
function safeGeometry(value:unknown):unknown{
 if(!value||typeof value!=='object')return null;
 const g=value as {type?:string;coordinates?:unknown};
 if(!['Point','MultiPoint','LineString','MultiLineString','Polygon','MultiPolygon'].includes(g.type||''))return null;
 const valid=(v:unknown,depth=0):boolean=>depth<9&&(typeof v==='number'?Number.isFinite(v)&&Math.abs(v)<=180:Array.isArray(v)&&v.length<=10000&&v.every(n=>valid(n,depth+1)));
 // Preserve complete rings; truncating to the generic array cap could turn a
 // valid administrative boundary into an open/incorrect polygon on refresh.
 if(!valid(g.coordinates)||JSON.stringify(g.coordinates).length>300000)return null;
 return {type:g.type,coordinates:g.coordinates};
}
export function safeMetadata(value:unknown,depth=0):unknown{
 if(depth>20)return null;
 if(value==null||typeof value==='boolean')return value;
 if(typeof value==='number')return Number.isFinite(value)?value:null;
 if(typeof value==='string'){
  if(value.length>8000||/Bearer\s|https?:\/\/\S+\?|[?&](?:sig|token|X-Amz-|X-Goog-|se=|sv=)|^data:/i.test(value))return '';
  if(/^(?:https?|s3):/i.test(value)){
   try{const u=new URL(value);if(u.search||u.hash||u.username||u.password)return '';}catch{return '';}
  }
  return value;
 }
 if(Array.isArray(value))return value.slice(0,200).map(v=>safeMetadata(v,depth+1));
 if(typeof value==='object')return Object.fromEntries(Object.entries(value).filter(([key])=>!forbidden.test(key)).slice(0,160).map(([key,v])=>[key,key==='geometry'?safeGeometry(v):safeMetadata(v,depth+1)]));
 return null;
}
export function readSnapshot():Record<string,unknown>|null{
 try{
  const raw=sessionStorage.getItem(SNAPSHOT_KEY);if(!raw||raw.length>2_000_000)return null;
  const value=JSON.parse(raw);if(value?.version!==1||typeof value.purpose!=='string'||!value.form||!Array.isArray(value.form.coordinates)||value.form.coordinates.length!==4||!value.form.origins)return null;
  const form=value.form;
  if(!['start','end','purposeType','temporalMode','observationNeed','targetSize','resolution','cloud','referenceDate','analysisTarget'].every(k=>typeof form[k]==='string'&&['default','auto','manual'].includes(form.origins[k])))return null;
  if(!form.coordinates.every((v:unknown)=>typeof v==='string')||!Array.isArray(form.origins.coordinates)||form.origins.coordinates.length!==4||!form.origins.coordinates.every((v:unknown)=>['default','auto','manual'].includes(v as string)))return null;
  if(value.data&&(!Array.isArray(value.data.items)||value.data.items.length>100||!value.data.query||!Array.isArray(value.data.query.bbox)))return null;
  if(value.data&&!value.data.items.every((s:Record<string,unknown>)=>typeof s.id==='string'&&typeof s.collection==='string'&&Array.isArray(s.instruments)&&Array.isArray(s.resolution_m)&&Array.isArray(s.band_details)&&s.evaluation))return null;
  for(const scene of Object.values(value.acquisitions||{}))for(const record of Object.values(scene as Record<string,{status:string}>))if(record.status==='receiving')record.status='failed';
  return safeMetadata(value) as Record<string,unknown>;
 }catch{return null;}
}
export function writeSnapshot(value:unknown){
 const raw=JSON.stringify(safeMetadata(value));if(raw.length>2_000_000)throw new Error('작업 메타데이터 보관 상한입니다.');
 sessionStorage.setItem(SNAPSHOT_KEY,raw);
}
