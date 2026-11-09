import {test,expect} from '@playwright/test';
import {researchRecord} from '../src/lib/researchRecord';
import type {ProcessingJob} from '../src/lib/types';
test('TEST ONLY research export preserves registered boundary provenance and unknown legacy metrics',()=>{
 const roi={confirmed:true,mode:'polygon',source:'registered_boundary',bbox:[1,2,3,4],geometry:{type:'Polygon',coordinates:[[[1,2],[3,2],[3,4],[1,2]]]},boundary_id:'TEST_ONLY',boundary_metadata:{name:'TEST ONLY',year:2025,geojson_sha256:'TEST_ONLY_HASH',source_url:'https://example.test/TEST_ONLY'}};
 const job={job_id:'TEST_ONLY',status:'failed',stage:'TEST ONLY',error:'TEST ONLY cancelled read',input:{roi,scenes:[]},result:null,artifact:null} as unknown as ProcessingJob;
 const record=researchRecord(job,'','2026-11-05T00:00:00Z');
 expect(record.input.roi).toEqual(roi);expect(record.result).toBeNull();expect(record.failure).toBeNull();expect(record.job.error).toBe(job.error);expect(record.execution_steps).toEqual([]);
 expect(JSON.stringify(record)).not.toContain('valid_area_m2');
});

test('TEST ONLY ML export preserves measured errors but strips unknown access data',()=>{
 const validation={status:'blocked',model:{rmse_k:3,mae_k:2,p95_k:5},cloud_truth_accuracy_verified:false,token:'TEST_ONLY_SECRET',fitted_model:{coef:[1],password:'TEST_ONLY_SECRET'}};
 const job={job_id:'TEST_ONLY',status:'failed',input:{scenes:[]},failure:{code:'ml_validation_failed',ml_validation:validation},result:null} as unknown as ProcessingJob;
 const r=researchRecord(job,'','2026-11-06T00:00:00Z');
 expect(r.failure?.ml_validation).toMatchObject({status:'blocked',model:{rmse_k:3},cloud_truth_accuracy_verified:false});
 expect(JSON.stringify(r)).not.toContain('TEST_ONLY_SECRET');
});
