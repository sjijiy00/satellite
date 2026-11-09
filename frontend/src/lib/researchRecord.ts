import type {ProcessingJob} from './types';
export const landsatResearchSources=[
 {title:'USGS Landsat 8–9 Level-2 Collection 2 데이터셋 DOI',url:'https://doi.org/10.5066/P9OGBGM6'},
 {title:'USGS 지표면 온도 제품·보정식·알려진 한계',url:'https://www.usgs.gov/landsat-missions/landsat-collection-2-surface-temperature'},
 {title:'USGS QA 밴드 정의',url:'https://www.usgs.gov/landsat-missions/landsat-collection-2-quality-assessment-bands'},
];
export const asObject=(value:unknown):Record<string,unknown>=>value!==null&&typeof value==='object'&&!Array.isArray(value)?value as Record<string,unknown>:{};
const fields=(value:unknown,keys:string[])=>{const obj=asObject(value);return Object.fromEntries(keys.filter(k=>k in obj).map(k=>[k,obj[k]]));};
const scene=(value:unknown)=>fields(value,['provider_id','collection','id','asset_keys','datetime','valid_area_m2']);
const roi=(value:unknown)=>{
 const obj=asObject(value);
 return {...fields(obj,['mode','bbox','source','boundary_id','geometry','confirmed']),...('boundary_metadata' in obj?{boundary_metadata:obj.boundary_metadata==null?null:fields(obj.boundary_metadata,['name','code','year','source','source_url','terms','crs','original_crs','geojson_sha256'])}:{})};
};
const qa=(value:unknown)=>fields(value,['maximum_uncertainty_k','minimum_cloud_distance_km']);
const list=(value:unknown)=>Array.isArray(value)?value:[];
const exclusions=['band_nodata_or_unobserved','base_qa_or_required_data','cloud_cirrus','cloud_dilated_cirrus','cloud_shadow','snow','saturated','dark_or_unclassified','fill','st_uncertainty','cloud_distance','uncertainty_or_cloud_proximity','qa_nodata_numeric'];
const statKeys=['estimated_celsius','target_celsius','other_date_fill_celsius','valid_area_m2','mean','minimum','maximum','kelvin','celsius','before','after','difference','hot_area_m2','candidate_gain_area_m2','candidate_loss_area_m2','regions','label','confirmed_area_m2','valid_percent','mean_celsius','mean_difference_celsius_first_minus_second','threshold','candidate_area_m2_by_date'];
function statistics(value:unknown):unknown{
 if(value===null||typeof value==='number'||typeof value==='string')return value;
 if(Array.isArray(value))return value.map(statistics);
 return Object.fromEntries(Object.entries(fields(value,statKeys)).map(([k,v])=>[k,statistics(v)]));
}
const mlKeys=['version','policy','validation_scope','status','folds','cloud_truth_accuracy_verified','paired_cells','sampled_pairs','sampling_step_cells','model','copy','bias_corrected_copy','fold','train_count','holdout_count','rmse_k','mae_k','p95_k','count','fitted_model','center','scale','coef','intercept','features','training_donor_range_k','estimated_cells','model_sha256','alpha','spatial_folds','buffer_m','sampling_spacing_m','minimum_train','minimum_holdout','minimum_pairs','maximum_rmse_k','maximum_mae_k','maximum_p95_k','minimum_copy_improvement','minimum_bias_improvement','maximum_training_distance_m'];
function mlValidation(value:unknown):unknown{
 if(value===null||['number','string','boolean'].includes(typeof value))return value;
 if(Array.isArray(value))return value.map(mlValidation);
 return Object.fromEntries(Object.entries(fields(value,mlKeys)).map(([k,v])=>[k,mlValidation(v)]));
}
export function researchRecord(job:ProcessingJob,note:string,exportedAt:string){
 const input=asObject(job.input),result=asObject(job.result),failure=asObject(job.failure),checked=asObject(failure.qa),summary=asObject(result.output_summary);
 return {
  schema:'satellite-insight-research-record/1',exported_at:exportedAt,
  notice:'조회한 작업의 연구 기록입니다. 현재 폼이나 원본 픽셀 파일이 아닙니다. 미기록은 미확인이며, 동일 입력만으로 향후 동일 바이트/결과 재현을 보장하지 않습니다. 성공 ZIP·manifest·원본 및 실행 환경을 함께 보관하세요.',
  researcher_note:note||null,
  product_references:list(input.scenes).some(v=>asObject(v).collection==='pc-landsat-c2-l2')?landsatResearchSources:[],
  job:fields(job,['job_id','status','stage','error','created_at','updated_at']),
  execution_steps:list(job.artifact?.execution_record?.steps).map(v=>fields(v,['id','label','status','detail','at'])),
  input:{...fields(input,['purpose_type','analysis_id','method_id','start_date','end_date','reference_date','threshold','threshold_basis','qa_policy_version','comparison_labels']),roi:roi(input.roi),comparison_regions:list(input.comparison_regions).map(roi),qa_options:qa(input.qa_options),scenes:list(input.scenes).map(scene)},
  result:job.status!=='succeeded'?null:{...fields(result,['status','analysis_completed','analysis_label','version','checked_at','aoi_area_m2','common_observed_area_m2','common_valid_area_m2','common_valid_percent_aoi','common_valid_percent_observed','ndvi_before_mean','ndvi_after_mean','ndvi_difference_mean']),statistics:result.statistics?statistics(result.statistics):null,threshold_sensitivity:result.threshold_sensitivity?statistics(result.threshold_sensitivity):null,
   output_summary:{...fields(summary,['crs','resolution_m','width','height','units','formula','qa_policy_version','statistics_scope']),sources:list(summary.sources).map(scene)},
   ml_validation:result.ml_validation?mlValidation(result.ml_validation):null,
   cloud_fill:result.cloud_fill?fields(result.cloud_fill,['mode','target_date','donor_date','original_valid_area_m2','filled_area_m2','composite_valid_area_m2','composite_valid_percent_aoi','remaining_gap_area_m2','cloud_gap_area_m2','target_date_restored']):null,
   grid:fields(result.grid,['crs','transform','width','height','resolution_m','extent','pixel_count','area_method']),
   preview_scale:fields(asObject(asObject(result.map_layers).analysis).legend,['minimum','maximum','unit','percentiles','scope']),
  },
  failure:job.failure?{ml_validation:failure.ml_validation?mlValidation(failure.ml_validation):null,...fields(failure,['code','retry_at']),qa:failure.qa?{...fields(checked,['status','aoi_area_m2','observed_area_m2','valid_area_m2','qa_policy_version']),qa_options:qa(checked.qa_options),scenes:list(checked.scenes).map(v=>({...scene(v),exclusions_m2:fields(asObject(v).exclusions_m2,exclusions)}))}:null}:null,
  artifact:job.artifact?fields(job.artifact,['filename','bytes','sha256','files','created_at','expires_at']):null,
  retention:job.retention?fields(job.retention,['state','expires_at']):null,
  limitations:['결측을 포함한 전체 지역의 참값·원인·통계적 유의성을 검증한 기록이 아닙니다.','과거 작업에 없던 QA 사유·격자·계산식을 소급 생성하지 않습니다.','별도 연구 노트에 장면 선택 이유·기준 채택 근거·독립 검증과 소프트웨어 환경을 남기세요.'],
 };
}
