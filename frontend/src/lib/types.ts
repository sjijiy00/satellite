import type { Geometry } from 'geojson';
export type Bbox = [number, number, number, number];
export type Purpose = '' | 'vegetation' | 'flood' | 'urban' | 'thermal';
export interface RequestIntent {summary:string;detail:string|null;evidence:string|null;basis:'explicit'|'inferred'|'unspecified';domains:Purpose[]}
export interface ProcessingMethod {id:string;label:string;engine:string;domains:Purpose[];providers:string[];collections:string[];levels:string[];minimum_scenes:number;maximum_scenes:number;required_variables:string[]|Record<string,string[]>;required_qa:string[];qa_policy_version:string;temporal:{utc:boolean;maximum_days:number;distinct_dates:boolean;same_platform:boolean;same_baseline:boolean};spatial:{maximum_aoi_km2:number;resolution_m:number;resolution_by_collection?:Record<string,number>;maximum_grid_pixels:number;polygon:boolean;tile_edge:number|null;maximum_tiles:number};artifacts:string[];unsupported_reason:string;source_mode:string;browser_download_required:boolean;products?:{provider_id:string;collection:string;levels:string[];platforms:string[];required_keys:string[];resolution_m:number;native_resolution:string;product:string;checked_on:string;policy_version:string}[];inputs?:{threshold:boolean;threshold_unit:string;comparison_regions:number;thermal_qa:boolean};caveats?:string[]}
export interface AnalysisTask {id:string;domain:Purpose;label:string;question:string;minimum_scenes:number;required_variables:string[];additional_requirements:string[];output:string;engine:string|null;engine_note:string;comparison:boolean;execution?:{analysis_engine:string|null;analysis_supported:boolean;method_ids:string[];methods:ProcessingMethod[];required_variables:string[];required_qa:string[];minimum_scenes:number;providers:string[];collections:string[];unsupported_reason:string|null;legacy_spatial:{maximum_aoi_km2:number;resolution_m:number}};preprocessing:{id:string;label:string;requirement:'required'|'optional'|'unnecessary';reason:string;engine:string|null}[]}
export interface AnalysisCatalog {version:string;domains:{id:Purpose;label:string}[];analyses:AnalysisTask[];processing_methods?:ProcessingMethod[];notice:string}
export interface ProcessingPlan {plan_id:string;confirmation_digest:string;status:string;source_access:string;pixel_quality:unknown;grid:{tile_count:number;width:number;height:number;resolution_m:number;aoi_area_m2:number;maximum_aoi_km2:number;maximum_transfer_bytes?:number;maximum_seconds?:number;maximum_output_bytes?:number};input:unknown;expected_artifacts:string[];notice:string}
export interface ExecutionStep {id:string;label:string;status:string;detail?:string;at?:string}
export interface ProcessingJob {job_id:string;status:'queued'|'running'|'succeeded'|'failed'|'cancelled';stage:string;created_at:string;updated_at:string;error:string|null;result:PixelReport|EstimatePlan|null;artifact:{filename:string;bytes:number;sha256:string;files:string[];expires_in_seconds:number;created_at?:string;expires_at?:string;execution_record?:{source_mode:string;inputs:unknown[];outputs:string[];grid:unknown;steps:ExecutionStep[]}}|null;input:unknown;events?:ExecutionStep[];retention?:{state:'available'|'expired'|'missing'|'changed'|'not_created';remaining_seconds:number;expires_at:string|null};job_expires_at?:string;ownership?:string}
export interface ProcessingFailure {
 code:string;retry_at?:string|null;
 qa?:{status:'checked_no_valid';aoi_area_m2:number;observed_area_m2:number;valid_area_m2:number;qa_policy_version:string;
 qa_options:Record<string,number>;scenes:{id:string;datetime:string;valid_area_m2:number;exclusions_m2:Record<string,number>}[]};
}
export interface ProcessingJob {failure?:ProcessingFailure|null}
export interface ProcessingJobRef {job_id:string;context:string;method_id:string;uses_pair:boolean}
export interface PixelQuality {status:'not_checked'|'checked'|'failed';message:string}
export interface SensorCard {
 analysis_options?:{id:string;label:string;minimum_scenes:number;data_candidate:boolean;engine_supported:boolean;note:string}[];
 provider_id?:string;
 id:string;observation:string;payload:string;platform_label:string;product:string;collection:string|null;
 native_resolution:string;output_grid:string;fit:{status:'met'|'conditional'|'not_met';reason:string};
 required_bands:{name:string;description:string}[];quality_materials:string[];constraints:string[];
 app_support:{search:boolean;processing:string;download:string};
 availability:{status:'unsearched'|'searched'|'none'|'failed'|'outside_scope';message:string;count:number|null};
 pixel_quality:PixelQuality;sources:{title:string;url:string;checked_on:string}[];rule_version:string;
 search_enabled:boolean;search_conditions:{collections:string[];platforms:string[];product_levels:string[];required_bands:string[]}|null;
}
export interface Recommendation { detail_intent?:string|null;detail_label?:string|null;purpose_type: Purpose | null; label: string; matched: string[]; collections: string[]; reasons: string[]; future: string[]; cards?:SensorCard[];assumptions?:string[];rule_version?:string;checked_on?:string;observation_requirement?:string|null }
export interface PurposePlan {
  metadata_only?:boolean;
  purpose: Purpose; label: string; analysis: string; analysis_keys: string[]; default_keys: string[];
  visual_keys: string[]; visual_title: string; visual_note: string; visual_mapping: Record<string,string|null>;
  missing_bands: string[]; visual_missing: string[]; group: 'primary'|'other'; group_reason: string; preprocessing: string;
  product_status?:'met'|'not_met'|'unknown';profile_id?:string|null;rule_version?:string;
}
export interface Scene {
  hls?:{short_name:string;version:string;original_id:string;doi:string;source:string;scale_note:string;temporal_note:string;not_surface_temperature:boolean}|null;
  geometry_role?:string;temporal_role?:string|null;
  source_product?:{original_id:string;version:string;family:string}|null;
  access_group?:string;access_paths?:{provider_id:string;provider:string;collection:string;id:string;source_url:string|null}[];
  preview_diagnostic?:{status:string;message:string;has_candidate:boolean};
  provider_id?:string; product_id?:string|null;remote_collection?:string|null;product_type?:string|null;end_datetime?:string|null;
  native_resolution?:string|null;output_grid?:string|null;
  sar?:Record<string,string|number|string[]|null>|null;
  support?:{analysis_methods?:string[];search:boolean;processing:string;file_access:string;access_verified:boolean};
  pixel_quality?:PixelQuality;
  purpose_plan?: PurposePlan;
  download_assets?: {key: string; title: string; href: string; media_type: string; direct_url: string | null; requester_pays: boolean;authentication_required?:boolean;access_verified?:boolean;signing_required?:boolean;filename?:string;size_bytes?:number|null;provider?:string; access_note: string; common_names: string[]; roles: string[];raster_metadata?:{scale?:number;offset?:number;unit?:string}[]}[];
  id: string; collection: string; geometry: Geometry | null; datetime: string | null;
  platform: string | null; instruments: string[]; resolution_m: number[]; scene_cloud_cover: number | null;
  processing_level: string | null; provider: string; source_url: string | null; thumbnail: string | null;
  overlap_percent: number | null; band_details: {asset: string; bands: string[]; resolution_m: number[]}[];
  evaluation: {status: string; label: string; days_from_start: number | null; sensor_match: boolean | null; sensor_reason: string; limitations: string[]};
}
export const sceneKey=(scene:Pick<Scene,'collection'|'id'|'provider_id'>)=>scene.provider_id?JSON.stringify([scene.provider_id,scene.collection,scene.id]):JSON.stringify([scene.collection,scene.id]);
export interface CollectionStatus {
  provider_id?:string;
  collection:string; status:'success'|'empty'|'partial'|'failed'|'limited'|'not_started'|'outside_scope';
  reason:string; complete:boolean; requests:number; returned:number; fetched:number;
  duplicates:number; invalid:number; error:string|null; last_datetime:string|null;
  filtered?:number;
  has_more:boolean|null; buffered_not_returned:number;
}
export interface SearchResponse {access_guidance?:{provider:string;products:string;authentication:string;url:string;conditions:string;scene_confirmed:boolean;scope:string;checked_on:string}[];source: string; items: Scene[]; returned: number; truncated: boolean; limit: number; recommendation: Recommendation; ranking: string; notice: string; collections?:string[];applied_recommendation?:string|null;outcome?:'success'|'partial'|'empty'|'failed'|'outside_scope'; collection_statuses?:CollectionStatus[]; query: {bbox: Bbox; start_date: string; end_date: string;requested_reference_date?:string|null}}
export interface ConditionsReport {
 version:string;checked_at:string;status:'conditional'|'unknown'|'blocked';conclusion:string;
 checks:{id:string;label:string;status:'pass'|'conditional'|'unknown'|'blocked';reason:string;next_action:string;evidence:unknown}[];
 coverage:{scene_a_percent:number|null;scene_b_percent:number|null;common_area_m2:number|null;common_percent:number|null;method?:string};
 request_count:number;limits:{max_requests:number};pixel_quality:'not_checked';file_headers_read:false;
}
export interface PixelReport {
 analysis_label?:string;statistics?:Record<string,unknown>;threshold_sensitivity?:unknown;qa_policy?:unknown;
 status:'checked'|'partial'|'failed'|'limited'|'busy';error?:string;conclusion?:string;version?:string;checked_at?:string;
 aoi_area_m2?:number;common_observed_area_m2?:number;common_valid_area_m2:number|null;common_valid_percent_aoi:number|null;common_valid_percent_observed:number|null;common_excluded_area_m2?:number|null;
 operational_threshold?:{minimum_percent:number;met:boolean|null};
 scenes?:{id:string;collection?:string;provider_id?:string;datetime:string;status:'checked'|'no_pixels'|'failed';error:string|null;valid_area_m2:number|null;valid_in_common_area_m2:number|null;valid_percent_aoi?:number|null;valid_percent_common?:number|null;exclusions_m2:Record<string,number>|null;headers:unknown[];radiometry:{status:string;[key:string]:unknown}[]}[];
 policy?:unknown;grid?:unknown;transfer?:unknown;provenance?:unknown;
 map_layers?:{quality:MapPreview[];analysis:MapPreview|null};
}
export interface MapPreview {
 legend?:{minimum:number;maximum:number;unit:string;percentiles:number[];scope:string;low_color:string;high_color:string}|null;
 png_base64:string;coordinates:[[number,number],[number,number],[number,number],[number,number]];
 label:string;scene_ids:string[];source:string;
}
export type ChangeReport = Omit<PixelReport,'status'> & {
 status:'computed'|'blocked'|'failed'|'limited'|'busy';analysis_completed:boolean;
 analysis_area_m2?:number|null;excluded_common_area_m2?:number|null;excluded_aoi_area_m2?:number|null;
 qa_excluded_area_m2?:number|null;numeric_excluded_area_m2?:number|null;
 ndvi_before_mean?:number|null;ndvi_after_mean?:number|null;ndvi_difference_mean?:number|null;
 artifact_base64?:string|null;artifact_name?:string;artifact_size_bytes?:number;
};

export interface WorkflowInterpretation {
 followup_supported?:boolean;
 condition_proposals?:ConditionProposals;
 version:string;intent:'search'|'cloud_help'|'clarify'|'compare'|'move_aoi';purpose_type:Purpose|null;purpose_label:string;
 purpose_evidence:string[];aoi:Bbox|null;period:{start:string|null;end:string|null;timezone:'UTC'};
 reference_date:string|null;target_size_m:number|null;temporal_mode:string;effective_temporal_mode:'single'|'change';
 observation_need:string;allow_date_change:boolean;selected_scene:{collection:string;id:string}|null;
 selected_datetime:string|null;text_date_mentions:string[];questions:string[];notes:string[];
 available_actions:string[];parser_scope:string;
}
export interface InterpretationUsage {
 requests:number;succeeded:number;failed:number;cancelled:number;cache_hits:number;input_tokens:number;output_tokens:number;
 unknown_usage_calls:number;last_status:string;estimated_usd_reported_tokens?:number|null;billing_note?:string;
}
export interface InterpretationConfig {
 ready:boolean;provider:string|null;model:string|null;message:string;usage:InterpretationUsage;
 limits:{timeout_seconds:number;max_input_chars:number;max_output_tokens:number;requests_per_minute:number;requests_per_process:number;concurrency:number;cache_seconds:number};
}
export interface CameraLocation {
 id:string;name:string;view_bbox?:Bbox;center?:[number,number];token:number;
}
export interface PlaceCandidate {
 id:string;name:string;view_bbox?:Bbox;center?:[number,number];role?:'camera_only';
 source?:string;source_url?:string;terms_url?:string;note?:string;usage?:string;history_url?:string;
 official_name?:string;admin_level?:string;parent?:string;checked_at?:string;region_code?:string|null;
 boundary?:BoundaryProposal;
 query?:string;
 extent?:{bbox:Bbox;radius_m:number;method:string;scope:string;polygon_clipping:boolean};
}
export interface BoundaryProposal {
 status:'proposed'|'unsupported'|'mismatch'|'failed';message:string;id?:string;name?:string;code?:string;code_system?:string;
 geometry?:Geometry;bbox?:Bbox;year?:string;source?:string;source_url?:string;terms?:string;crs?:string;original_crs?:string;note?:string;
 polygon_clipping?:boolean;search_scope?:string;boundary_area_km2?:number;bbox_area_km2?:number;pixel_area_limit_km2?:number;pixel_area_exceeded?:boolean;
 display_simplification?:string|null;
}
export interface PlaceProposal extends Partial<PlaceCandidate> {
 extent_requires_confirmation?:boolean;
 status:'resolved'|'absent'|'ambiguous'|'unsupported'|'failed'|'lookup_required'|'loading'|'not_configured'|'needs_confirmation'|'no_results'|'limited'|'timeout'|'authentication_failed'|'invalid_response';
 mentioned_text?:string|null;label?:string;message?:string;source_year?:string;truncated?:boolean;
 candidates?:PlaceCandidate[];
}
export interface PlaceConfig {ready:boolean;provider:string;message:string;missing_settings:string[]}
export interface ConditionProposals {
 request_summary?:string|null;domain_candidates?:Purpose[];
 status:'success'|'partial'|'failed';messages:string[];event_reference_required:boolean;scope:string;
 engine?:{mode:'rules'|'ai';status:string;provider:string|null;model:string|null;usage?:InterpretationUsage};
 fields?:Record<string,{value:string|number|null;basis:'explicit'|'inferred'|'unspecified';evidence:string|null}>;
 comparison_periods?:{role:'before'|'after';status:string;start?:string;end?:string}[];
 extraction?:{purpose_type:Purpose|null;purpose_evidence?:string|null;analysis_target?:string|null;temporal_mode:'single'|'change'|'unspecified';temporal_evidence?:string|null;places?:{text:string;ambiguous:boolean;basis?:'explicit'|'inferred'|'unspecified';kind?:'administrative'|'place';spatial_scope?:'boundary'|'radius'|'unspecified';radius_m?:number|null}[];uncertainties?:string[]};
 period:{status:'resolved'|'absent'|'needs_confirmation';start?:string;end?:string;timezone?:string;message?:string};
 region:PlaceProposal;
}
export interface CloudSceneResult {
 id:string;collection:string;datetime:string;status:'checked'|'no_pixels'|'failed';error:string|null;
 valid_area_m2:number|null;valid_percent_aoi:number|null;date_offset_days:number;
 exclusions_m2:Record<string,number>|null;
}
export interface CloudPlan {
 status:'planned'|'succeeded'|'blocked'|'failed'|'busy'|'limited';error?:string;version?:string;
 plan_id?:string;confirmation_digest?:string;expires_in_seconds?:number;
 interpretation?:string;target_id?:string;target_date?:string;
 period?:{start:string;end:string;timezone:string};
 aoi_area_m2?:number;observed_area_m2?:number;unobserved_area_m2?:number;
 original_valid_area_m2?:number;composite_valid_area_m2?:number;composite_valid_percent_aoi?:number;
 remaining_gap_area_m2?:number;quality_or_nodata_excluded_area_m2?:number;
 scenes?:CloudSceneResult[];priority?:{index:number;id:string;datetime:string;date_offset_days:number}[];
 used_scene_count?:number;oldest_observation_date?:string|null;oldest_observation_age_days?:number|null;
 can_execute?:boolean;grid?:{resolution_m:number;width:number;height:number;crs:string;extent:number[]};
 limits?:Record<string,number>;estimate?:{output_uncompressed_bytes:number;note:string};policy?:{version:string;[key:string]:unknown};
}
export interface CloudJob {
 job_id:string;plan_id:string;status:'queued'|'running'|'succeeded'|'failed'|'cancelled';stage:string;
 created_at:string;updated_at:string;error:string|null;result:CloudPlan|null;
}

/** A supervised estimate is never an observed pixel or an observed-date composite. */
export interface EstimatePlan {
 status:'planned'|'blocked'|'failed'|'busy'|'succeeded';error?:string|null;version?:string;
 plan_id?:string;confirmation_digest?:string;can_execute?:boolean;expires_in_seconds?:number;
 target_id?:string;target_date?:string;period?:{start:string;end:string;timezone:string};
 method?:{name:string;version:string;description:string;training:string;validation:string;limitations:string[]};
 validation?:{status:string;train_pixels:number|null;holdout_pixels:number|null;
   rmse_by_band:Record<string,number>|null;baseline_rmse_by_band:Record<string,number>|null;note:string;
   mae_by_band?:Record<string,number>|null;error_q90_by_band?:Record<string,number>|null;baseline_mae_by_band?:Record<string,number>|null};
 areas?:{aoi_m2:number|null;observed_m2:number|null;estimated_m2:number|null;remaining_gap_m2:number|null};
 source_dates?:string[];grid?:CloudPlan['grid'];artifact_name?:string;artifact_size_bytes?:number;
 map_layers?:{observed:MapPreview|null;estimated:MapPreview|null};
}
export interface EstimateJob extends Omit<CloudJob,'result'> {result:EstimatePlan|null}
