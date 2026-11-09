// TEST ONLY: deterministic UI fixtures, never imported by application code.
import type {Purpose,Scene,SearchResponse,CollectionStatus} from '../src/lib/types';
export const collections=['sentinel-2-l2a','landsat-c2-l2'];
export const key=(collection:string,id:string)=>JSON.stringify(['earth-search',collection,id]);
export const rect=(w=126.5,e=127)=>({type:'Polygon' as const,coordinates:[[[w,36.3],[e,36.3],[e,36.8],[w,36.8],[w,36.3]]]});
export function fixture(purpose:Purpose='flood',count=12):SearchResponse {
  const items:Scene[]=[];
  for(const collection of collections)for(let n=0;n<count;n++) {
    const primary=purpose==='thermal'?collection===collections[1]:collection===collections[0];
    const required=purpose==='vegetation'?['red','nir']:purpose==='thermal'?['lwir11']:['green','swir16'];
    const defaults=[...required,'scl'];
    const names=['red','nir','green','swir16','lwir11','scl','visual','restricted'];
    const id='TEST_ONLY_'+n;
    items.push({id,collection,provider_id:'earth-search',platform:collection===collections[0]?'sentinel-2b':'landsat-9',instruments:[collection===collections[0]?'msi':'oli'],processing_level:collection===collections[0]?'S2MSI2A':'L2SP',datetime:`2025-07-${String(n+1).padStart(2,'0')}T02:00:00Z`,geometry:n===2?rect(128,129):rect(),scene_cloud_cover:n,overlap_percent:n===2?0:100,resolution_m:[10,20],provider:'TEST ONLY',source_url:null,thumbnail:null,band_details:[],
      evaluation:{status:'판정 보류',label:'테스트',days_from_start:n,sensor_match:true,sensor_reason:'TEST ONLY',limitations:[]},
      purpose_plan:{product_status:'met',purpose,label:purpose==='vegetation'?'식생 분석':purpose==='thermal'?'열환경 분석':'침수·수역 분석',analysis:purpose==='vegetation'?'NDVI':'TEST ANALYSIS',analysis_keys:defaults,default_keys:defaults,visual_keys:defaults,visual_title:'TEST VISUAL',visual_note:'TEST ONLY',visual_mapping:Object.fromEntries(required.map(n=>[n,n])),missing_bands:[],visual_missing:[],group:primary?'primary':'other',group_reason:'TEST GROUP',preprocessing:'TEST ONLY'},
      download_assets:names.map(name=>({key:name,title:name,href:name==='restricted'?'s3://test/restricted.tif':`https://example.test/${collection}/${id}/${name}.tif`,media_type:'image/tiff',direct_url:name==='restricted'?null:`https://example.test/${collection}/${id}/${name}.tif`,requester_pays:name==='restricted',access_note:'TEST ONLY',common_names:[name],roles:name==='visual'?['visual']:[]}))});
  }
  return {source:'TEST_ONLY_SYNTHETIC',outcome:'success',items,returned:items.length,truncated:false,limit:50,recommendation:{purpose_type:purpose,label:'TEST ONLY',matched:[],collections,reasons:[],future:[]},ranking:'TEST ONLY',notice:'TEST ONLY',query:{bbox:[126.5,36.3,127,36.8],start_date:'2025-07-01',end_date:'2025-07-31'},collection_statuses:collections.map(collection=>status(collection,'success',count))};
}
export function status(collection:string,state:CollectionStatus['status'],returned=0):CollectionStatus {
  return {collection,status:state,returned,fetched:returned,reason:state==='failed'?'timeout':'exhausted',complete:state==='success'||state==='empty',requests:1,duplicates:0,invalid:0,error:state==='failed'?'제공처 응답 시간 초과':null,last_datetime:null,has_more:state==='failed'?null:false,buffered_not_returned:0};
}
