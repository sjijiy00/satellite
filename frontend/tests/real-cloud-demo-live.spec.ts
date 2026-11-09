// Explicit live UI verification. No search, raster, job, or image fixtures.
import {test,expect,searchProduct} from './runtime';
import {readFile,mkdir,writeFile} from 'node:fs/promises';
test('LIVE real cloud ML search to verified download',async({page})=>{
 test.skip(process.env.LIVE_CLOUD_DEMO!=='1','Explicit public raster execution only');test.setTimeout(300000);
 const evidence=JSON.parse(await readFile('../test-results/real-cloud-demo/chosen.json','utf8')),q=evidence.input;
 const out='../test-results/real-cloud-demo/browser';await mkdir(out,{recursive:true});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');
 await page.getByLabel('시작일',{exact:true}).fill(q.start_date);await page.getByLabel('종료일',{exact:true}).fill(q.end_date);
 for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String(q.roi.bbox[i]));
 await searchProduct(page,'pc_landsat_tirs');
 console.log('LIVE_SEARCH_SUBMITTED');
 const card=page.getByTestId('scene-card').filter({hasText:q.scenes[0].id});await expect(card).toHaveCount(1,{timeout:60000});
 await card.getByRole('button',{name:'지도에서 선택',exact:true}).click();
 console.log('LIVE_TARGET_SELECTED');
 await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();
 const selection=page.getByTestId('analysis-selection');await selection.locator('input[value="surface_temperature"]').check();await selection.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 const panel=page.getByTestId('processing-foundation');await panel.getByLabel('구름 전처리 방식',{exact:true}).selectOption('thermal_ml');
 for(const [i,s] of q.scenes.entries())await page.locator('#processing-scene-'+i).selectOption(JSON.stringify([s.provider_id,s.collection,s.id]));
 await panel.getByLabel('허용 ST 불확실성 상한 (K)',{exact:true}).fill(String(q.qa_options.maximum_uncertainty_k));
 await panel.getByLabel('구름으로부터 최소 거리 (km)',{exact:true}).fill(String(q.qa_options.minimum_cloud_distance_km));
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();
 console.log('LIVE_PLAN_SUBMITTED');
 const check=panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true});await expect(check).toBeVisible({timeout:60000});await check.check();
 const started=page.waitForResponse(r=>r.url().endsWith('/api/processing/jobs')&&r.request().method()==='POST');
 await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();const initial=await(await started).json();
 const button=panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true});await expect(button).toBeEnabled({timeout:150000});
 const job=await(await page.request.get('/api/processing/jobs/'+initial.job_id)).json();
 expect(job.status).toBe('succeeded');expect(job.result.ml_validation.status).toBe('passed');expect(job.result.ml_validation.estimated_cells).toBeGreaterThan(0);
 const receiving=page.waitForEvent('download');await button.click();await(await receiving).saveAs(out+'/real-cloud-ml.zip');
 await writeFile(out+'/job.json',JSON.stringify(job,null,2));await panel.screenshot({path:out+'/result.png'});
 const record=page.getByRole('button',{name:/연구 기록.*JSON|연구 기록.*저장/}).first();
 if(await record.isVisible()){const saved=page.waitForEvent('download');await record.click();await(await saved).saveAs(out+'/research-record.json');}
});
