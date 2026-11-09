// Real public metadata/Range pixels only. No scene/band/processing fixtures,
// paid AI, provider credentials, automatic browse or full original downloads.
import {mkdir,writeFile,readFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {test,expect,searchProduct} from './runtime';
import {sceneKey,type Scene} from '../src/lib/types';

const cases=[
 ['vegetation_index','ndvi','vegetation'],['vegetation_change','ndvi_change','vegetation'],
 ['water_extent','mndwi','flood'],['water_change','mndwi_change','flood'],['urban_index','ndbi','urban'],
 ['surface_temperature','surface_temperature','thermal'],['hotspots','hotspots','thermal'],['temperature_comparison','temperature_comparison','thermal'],
 ['surface_temperature','thermal_gapfill','thermal'],
] as const;
const root=path.resolve(process.env.E2E_EVIDENCE_DIR||'../test-results/analysis-delivery-live');
test.describe.configure({mode:'default'});
test('LIVE city AOI actual search remains intact; pixel processing rejects the oversized bbox',async({page})=>{
 test.skip(process.env.LIVE_STAC!=='1'||process.env.LIVE_PROCESSING!=='1','Explicit LIVE flags');test.setTimeout(120000);
 await page.route('**/api/media/**',r=>r.abort());const bbox=[126.76,37.42,127.18,37.70];let starts=0;
 page.on('request',r=>{if(r.method()==='POST'&&new URL(r.url()).pathname==='/api/processing/jobs')starts++;});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');await page.getByLabel('시작일',{exact:true}).fill('2025-08-15');await page.getByLabel('종료일',{exact:true}).fill('2025-08-30');
 for(const [i,label]of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String(bbox[i]));
 const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/search'&&r.request().method()==='POST');await searchProduct(page,'pc_landsat_tirs');const response=await pending,data=await response.json();expect(response.status()).toBe(200);
 const scene=data.items.find((s:Scene)=>s.collection==='pc-landsat-c2-l2'&&s.processing_level==='L2SP') as Scene|undefined;expect(scene,'Current actual L2SP search must supply an Item').toBeTruthy();
 await page.getByRole('group',{name:'촬영 날짜',exact:true}).getByRole('button',{name:new RegExp(scene!.datetime!.slice(0,10))}).click();await page.getByTestId('scene-card').filter({hasText:scene!.id}).getByRole('button',{name:'지도에서 선택',exact:true}).click();await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();
 const selection=page.getByTestId('analysis-selection');await selection.locator('input[value="surface_temperature"]').check();await selection.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();const panel=page.getByTestId('processing-foundation');
 const details=panel.locator('details').filter({hasText:'이 장면의 제품·필수 밴드/QA 확인'});await details.locator(':scope > summary').click();for(const key of ['qa','cdist'])await details.getByLabel(key,{exact:true}).check();
 const request=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/processing/plans'&&r.request().method()==='POST');await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();const rejected=await request,body=await rejected.json();expect(rejected.status()).toBe(422);expect(JSON.stringify(body)).toMatch(/50|상한|km/);expect(starts).toBe(0);
 const payload=rejected.request().postDataJSON();expect(payload.roi.bbox).toEqual(bbox);await expect(panel.getByRole('alert')).toBeVisible();
 await mkdir(path.join(root,'live-city'),{recursive:true});await writeFile(path.join(root,'live-city','result.json'),JSON.stringify({at:new Date().toISOString(),bbox,item:scene!.id,period:['2025-08-15','2025-08-30'],search_http:response.status(),search_returned:data.returned,plan_http:rejected.status(),limit_message:body.detail,processing_starts:starts,scope:'Seoul-containing search bbox, not confirmed Seoul polygon statistics'},null,2));
});
for(const [analysis,method,domain] of cases)test(`LIVE delivery ${analysis} ${method} actual search → pixels → browser ZIP/TIFF numeric reopen`,async({page},info)=>{
 test.skip(process.env.LIVE_STAC!=='1'||process.env.LIVE_PROCESSING!=='1','Explicit LIVE_STAC + LIVE_PROCESSING');test.setTimeout(420000);
 const thermal=domain==='thermal',many=method==='ndvi_change'||method==='mndwi_change'||method==='thermal_gapfill';
 const bbox=method==='thermal_gapfill'?[-115.17,36.14,-115.13,36.18]:thermal?[-115.15,36.16,-115.14,36.17]:[126.7,36.4,126.71,36.41];
 const ids=method==='thermal_gapfill'?['LC08_L2SP_039035_20250719_02_T1','LC08_L2SP_039035_20250703_02_T1']:thermal?['LC08_L2SP_039035_20250719_02_T1']:many?['S2B_52SBF_20210716_0_L2A','S2B_52SBF_20210726_0_L2A']:['S2B_52SBF_20210716_0_L2A'];
 const year=thermal?'2025':'2021';
 let jobId='',downloadPosts=0,searchCount=0,paid=0;
 page.on('request',r=>{if(new URL(r.url()).pathname==='/api/search')searchCount++;if(r.method()==='POST'&&new URL(r.url()).pathname==='/api/processing/jobs')downloadPosts++;});
 await page.route('**/api/media/**',r=>r.abort());
 await page.route('https://api.openai.com/**',r=>{paid++;return r.abort();});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption(domain);
 await page.getByLabel('시작일',{exact:true}).fill(year+'-07-01');await page.getByLabel('종료일',{exact:true}).fill(year+'-07-31');
 for(const [i,label]of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String(bbox[i]));
 const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/search'&&r.request().method()==='POST');await searchProduct(page,thermal?'pc_landsat_tirs':'s2_msi');
 const response=await pending,data=await response.json();expect(response.status()).toBe(200);
 const scenes=ids.map(id=>data.items.find((s:Scene)=>s.id===id&&s.collection===(thermal?'pc-landsat-c2-l2':'sentinel-2-l2a')) as Scene|undefined);
 expect(scenes.every(Boolean),'Exact sample Items must occur in current real search; no substituted results').toBe(true);
 const first=scenes[0]!;await page.getByRole('group',{name:'촬영 날짜',exact:true}).getByRole('button',{name:new RegExp(first.datetime!.slice(0,10))}).click();
 await page.getByTestId('scene-card').filter({hasText:first.id}).getByRole('button',{name:'지도에서 선택',exact:true}).click();
 await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();const selection=page.getByTestId('analysis-selection');
 await selection.locator(`input[value="${analysis}"]`).check();await selection.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 const panel=page.getByTestId('processing-foundation');
 if(method==='thermal_gapfill')await panel.getByLabel('구름 전처리 방식',{exact:true}).selectOption('thermal_gapfill');
 await expect(panel.getByLabel('서버 지원 처리 방법',{exact:true})).toHaveValue(method);
 if(many)for(const [i,scene]of scenes.entries())await panel.getByLabel('공통 처리 영상 '+(i+1),{exact:method!=='thermal_gapfill'}).selectOption(sceneKey(scene!));
 // Display the canonical product requirements already returned by the server.
 // NDVI change's existing catalog/UI uses its selected required band defaults.
 for(const details of await panel.locator('details').filter({has:page.locator('summary').filter({hasText:'이 장면의 제품·필수 밴드/QA 확인'})}).all()){
  await details.locator(':scope > summary').click();for(const checkbox of await details.getByRole('checkbox').all())if(!await checkbox.isChecked())await checkbox.check();
 }
 if(method==='mndwi'||method==='mndwi_change'||method==='hotspots'){
  await panel.getByLabel(method==='hotspots'?'고온 기준 (섭씨)':'수역 후보 MNDWI 임계값 (-1~1)',{exact:true}).fill(method==='hotspots'?'40':'0');
  await panel.getByLabel('임계값 근거·확인 내용',{exact:true}).fill('LIVE validation explicit illustrative criterion; not a universal physical threshold');
 }
 if(method==='temperature_comparison'){
  for(const [i,row]of [[-115.15,36.16,-115.146,36.17],[-115.144,36.16,-115.14,36.17]].entries())for(const [j,value]of row.entries())await panel.getByLabel(`영역 ${i+1} ${['서','남','동','북'][j]}`,{exact:true}).fill(String(value));
  await panel.getByLabel('두 비교 영역과 이름을 직접 확인했습니다',{exact:true}).check();
 }
 const planResponse=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/processing/plans'&&r.request().method()==='POST');await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();
 const plan=await planResponse;expect(plan.status(),'real canonical plan').toBe(200);
 const planData=await plan.json();expect(planData.input).toMatchObject({analysis_id:analysis,method_id:method,roi:{bbox,confirmed:true},start_date:year+'-07-01',end_date:year+'-07-31'});
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();
 const started=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/processing/jobs'&&r.request().method()==='POST');await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 const jobResponse=await started;expect(jobResponse.status()).toBe(202);jobId=(await jobResponse.json()).job_id;
 // The server's bounded tile worker can legitimately take up to 255 seconds.
 // Allow its declared budget plus polling/transport margin, not an earlier test cutoff.
 const processingWait=Math.min(300000,(Number(planData.grid.maximum_seconds)||75)*1000+30000);
 await expect.poll(async()=>{const text=await panel.getByTestId('processing-job').innerText();if(text.includes('failed'))throw new Error(text.slice(0,700));return text;},{timeout:processingWait}).toContain('succeeded');
 const event=page.waitForEvent('download');await panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true}).click();const received=await event;
 const saved=info.outputPath(analysis+'.zip');await received.saveAs(saved);expect(await received.failure()).toBeNull();await expect(panel).toContainText('SHA-256 확인');
 const evidence=path.join(root,'live-delivery',method);await mkdir(evidence,{recursive:true});
 await writeFile(path.join(evidence,'result.zip'),await readFile(saved));
 const verification=spawnSync(path.resolve('../.venv/Scripts/python.exe'),['tests/verify_analysis_delivery.py',saved,path.join(evidence,'rasterio.json')],{cwd:path.resolve('../backend'),encoding:'utf8',windowsHide:true});
 await writeFile(path.join(evidence,'verification.log'),verification.stderr||'');expect(verification.status,'real browser file CRS/NoData/grid/unit/checksum/numeric verification').toBe(0);
 await writeFile(path.join(evidence,'run.json'),JSON.stringify({at:new Date().toISOString(),analysis,method,items:ids,bbox,start:year+'-07-01',end:year+'-07-31',job_id:jobId,search_status:response.status(),search_returned:data.returned,searchCount,processing_posts:downloadPosts,openai_requests:paid,scope:'actual public search/Range/QA/computation/map/browser file; no full originals or provider browse'},null,2));
 expect(paid).toBe(0);expect(downloadPosts).toBe(1);await panel.screenshot({path:path.join(evidence,'panel.png')});
 if(method==='thermal_gapfill'){
  await expect(panel.getByRole('region',{name:'구름 제거 전처리 결과'})).toContainText('보충 후 AOI 유효율');
  const event=page.waitForEvent('download');await panel.getByRole('button',{name:'연구 기록 JSON 저장',exact:true}).click();
  const recordFile=path.join(evidence,'research-record.json');await (await event).saveAs(recordFile);
  const record=JSON.parse(await readFile(recordFile,'utf8'));
  expect(record.result.cloud_fill.target_date_restored).toBe(false);
  expect(record.result.statistics).toHaveProperty('target_celsius');
  // Actual data may contain uncertainty-only gaps, which must NOT be filled.
  expect(record.result.cloud_fill.filled_area_m2).toBeGreaterThanOrEqual(0);
  if(record.result.cloud_fill.filled_area_m2===0)await expect(panel.getByRole('region',{name:'구름 제거 전처리 결과'})).toContainText('채워진 구름 영역은 없습니다');
 }
 if(analysis==='vegetation_index'){
  await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();await page.reload();
  await page.getByText('내 결과 보관함 · 재시작 후 찾기',{exact:true}).click();
  const archive=page.locator('.result-archive');await archive.getByRole('button',{name:'보관 결과 조회',exact:true}).click();
  const archived=page.waitForEvent('download');await archive.getByRole('button',{name:'이전 결과 ZIP 저장',exact:true}).click();
  const again=await archived,archiveFile=info.outputPath('retained-ndvi.zip');await again.saveAs(archiveFile);
  expect(await readFile(archiveFile)).toEqual(await readFile(saved));await expect(archive).toContainText('SHA-256 확인');
  expect(downloadPosts).toBe(1);expect(searchCount).toBe(1);
  const statusUrl=process.env.E2E_API_BASE_URL?`${new URL(process.env.E2E_API_BASE_URL).origin}/processing/jobs/${jobId}`:new URL(`/api/processing/jobs/${jobId}`,page.url()).href;
  expect((await page.request.get(statusUrl)).status()).toBe(200);
  const stranger=await page.context().browser()!.newContext();
  try{expect((await stranger.request.get(statusUrl+'/download')).status()).toBe(404);}finally{await stranger.close();}
  await archive.screenshot({path:path.join(evidence,'retained-archive.png')});
  await writeFile(path.join(evidence,'archive.json'),JSON.stringify({reload_restored:true,identical_zip_bytes:true,sha256_checked:true,other_browser_http:404,processing_posts:downloadPosts,searches:searchCount},null,2));
 }
});
