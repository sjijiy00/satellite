// TEST ONLY response transport. Files are real local TIFF calculations, not provider imagery.
import {mkdir,readFile,writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {test,expect,searchProduct,type Page} from './runtime';
import {fixture} from './fixtures';
import type {Purpose} from '../src/lib/types';
const root=path.resolve(process.env.E2E_EVIDENCE_DIR||'../test-results/product-engines-20261103-210850'),folder=path.join(root,'ui-fixture-'+process.pid);
test.beforeAll(async()=>{
 await mkdir(folder,{recursive:true});
 const result=spawnSync(path.resolve('../.venv/Scripts/python.exe'),['tests/create_product_ui_fixture.py',folder],{cwd:path.resolve('../backend'),encoding:'utf8',windowsHide:true});
 await writeFile(path.join(folder,'fixture-generation.log'),result.stderr||result.error?.name||'');
 expect(result.status,'TEST ONLY actual TIFF fixture generation').toBe(0);
});
async function setup(page:Page,method:string,failDownload=false,extraScene=false){
 const sample=JSON.parse(await readFile(path.join(folder,method+'.json'),'utf8')),query=sample.input;
 const domain=query.purpose_type as Purpose,thermal=domain==='thermal';
 const data=fixture(domain,1),baseScene=data.items.find(s=>s.collection===(thermal?'landsat-c2-l2':'sentinel-2-l2a'))!;data.items=query.scenes.map((ref:any,i:number)=>{
  const s=baseScene,keys=ref.asset_keys as string[];return {...s,id:ref.id,provider_id:thermal?'planetary-computer':'earth-search',collection:thermal?'pc-landsat-c2-l2':'sentinel-2-l2a',platform:thermal?'landsat-9':'sentinel-2b',datetime:`2025-07-${10+i*10}T00:00:00Z`,processing_level:thermal?'L2SP':'S2MSI2A',
   purpose_plan:{...s.purpose_plan!,analysis_keys:keys,default_keys:thermal?['lwir11','qa_pixel','qa_radsat']:keys},
   download_assets:keys.map(key=>({key,title:key,href:'https://example.test/TEST_ONLY/'+key+'.tif',direct_url:null,media_type:'image/tiff',requester_pays:false,access_note:'TEST ONLY',common_names:[key==='lwir11'?'thermal':key==='nir08'?'nir':key],roles:[]}))};});data.returned=data.items.length;
 if(extraScene){data.items.push({...data.items[0],id:'TEST_ONLY_ALTERNATIVE',datetime:'2025-07-20T00:00:00Z'});data.returned=data.items.length;}
 let plans=0,starts=0,latest:any;
 await page.route('**/api/search',r=>{data.query=r.request().postDataJSON();return r.fulfill({json:data});});
 await page.route('**/api/media/**',r=>r.fulfill({json:{assets:[],preview:null}}));
 await page.route('**/api/processing/plans',r=>{plans++;latest=r.request().postDataJSON();return r.fulfill({json:{plan_id:'c'.repeat(32),confirmation_digest:'d'.repeat(64),source_access:'canonical_metadata_checked_pixels_pending',grid:{width:40,height:40,tile_count:1},input:latest,expected_artifacts:sample.artifact.files,notice:'TEST ONLY plan awaits explicit confirmation'}});});
 const job={...sample,status:'succeeded',stage:'TEST ONLY actual local file reopen',created_at:'2025-07-01T00:00:00Z',updated_at:'2025-07-01T00:00:00Z',error:null,retention:{state:'available',expires_at:new Date(Date.now()+900000).toISOString(),remaining_seconds:900}};
 await page.route('**/api/processing/jobs',r=>{starts++;return r.fulfill({status:202,json:job});});
 await page.route('**/api/processing/jobs/'+sample.job_id,r=>r.fulfill({json:job}));
 const zip=await readFile(path.join(folder,method+'.zip'));
 let downloads=0;await page.route('**/api/processing/jobs/'+sample.job_id+'/download',r=>{downloads++;return failDownload&&downloads===1?r.fulfill({status:503,json:{detail:'TEST ONLY provider unavailable'}}):r.fulfill({body:zip,contentType:'application/zip',headers:{'content-length':String(zip.length)}});});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption(domain);
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
 for(const [i,label]of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String(query.roi.bbox[i]));
 await searchProduct(page,thermal?'pc_landsat_tirs':'s2_msi');await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();
 const selection=page.getByTestId('analysis-selection');await selection.locator(`input[value="${query.analysis_id}"]`).check();await selection.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 return {panel:page.getByTestId('processing-foundation'),query,zip,job,downloads:()=>downloads,counts:()=>({plans,starts}),input:()=>latest};
}
for(const method of ['ndvi','mndwi','mndwi_change','ndbi','surface_temperature','hotspots','temperature_comparison'])test(`TEST ONLY ${method} required user inputs → plan → actual fixture file save/reopen`,async({page},info)=>{
 await page.setViewportSize({width:390,height:844});const state=await setup(page,method),panel=state.panel;
 if(method==='mndwi'||method==='mndwi_change'||method==='hotspots'){
  await expect(panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true})).toBeDisabled();
  await panel.getByLabel(method==='hotspots'?'고온 기준 (섭씨)':'수역 후보 MNDWI 임계값 (-1~1)',{exact:true}).fill(method==='hotspots'?'20':'.1');
  await panel.getByLabel('임계값 근거·확인 내용',{exact:true}).fill('TEST ONLY explicit criterion');
 }
 if(method==='surface_temperature'||method==='hotspots'||method==='temperature_comparison'){
  const details=panel.locator('details').filter({hasText:'이 장면의 제품·필수 밴드/QA 확인'});await details.locator('summary').click();
  for(const key of ['qa','cdist'])await details.getByLabel(key,{exact:true}).check();
 }
 if(method==='temperature_comparison'){
  await expect(panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true})).toBeDisabled();
  for(const [i,row] of [[126.7,36.4,126.704,36.41],[126.706,36.4,126.71,36.41]].entries())for(const [j,v]of row.entries())await panel.getByLabel(`영역 ${i+1} ${['서','남','동','북'][j]}`,{exact:true}).fill(String(v));
  await panel.getByLabel('두 비교 영역과 이름을 직접 확인했습니다',{exact:true}).check();
 }
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await expect(panel).toContainText('pixels_pending');expect(state.counts().starts).toBe(0);
 expect(state.input()).toMatchObject({method_id:method,roi:{bbox:[126.7,36.4,126.71,36.41],confirmed:true}});
 if(method==='temperature_comparison')expect(state.input().comparison_regions).toHaveLength(2);
 if(method==='hotspots')expect(state.input()).toMatchObject({threshold:20,qa_options:{maximum_uncertainty_k:2,minimum_cloud_distance_km:1}});
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();await expect(panel.getByTestId('processing-job')).toContainText('succeeded');
 await expect(page.locator('.map-legend')).toContainText(['surface_temperature','hotspots','temperature_comparison'].includes(method)?'실제 지표면 온도':method==='mndwi_change'?'MNDWI':'실제 '+method.toUpperCase());
 const pending=page.waitForEvent('download');await panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true}).click();const received=await pending,target=info.outputPath('TEST_ONLY_product.zip');await received.saveAs(target);expect(await readFile(target)).toEqual(state.zip);
 const verification=spawnSync(path.resolve('../.venv/Scripts/python.exe'),['-c',`import sys,zipfile,json,hashlib;from rasterio.io import MemoryFile
with zipfile.ZipFile(sys.argv[1]) as z:
 m=json.loads(z.read('manifest.json'));assert m['verified_after_disk_write'];assert m['execution_record']['source_mode']=='canonical_server_range'
 for n,e in m['files'].items():
  assert hashlib.sha256(z.read(n)).hexdigest()==e['sha256']
  if n.endswith('.tif'):
   with MemoryFile(z.read(n)) as mem:
    with mem.open() as ds:assert ds.crs and ds.nodata is not None and ds.read().size>0
`,target],{encoding:'utf8',windowsHide:true});expect(verification.status,'TEST ONLY browser-saved ZIP/TIFF reopen').toBe(0);
 await expect(panel).toContainText('실행된 전처리·계산·파일 검증 기록');await expect(panel).toContainText('SHA-256 확인');await page.reload();expect(state.counts()).toEqual({plans:1,starts:1});await expect(panel.getByTestId('processing-job')).toContainText('succeeded');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await mkdir(path.join(root,'screenshots'),{recursive:true});await panel.screenshot({path:path.join(root,'screenshots',method+'-390.png')});
});
for(const width of [390,1440])test(`TEST ONLY ${width}px thermal ML explicit choice validation and export`,async({page},info)=>{
 await page.setViewportSize({width,height:844});const s=await setup(page,'thermal_ml'),panel=s.panel;
 await panel.getByLabel('구름 전처리 방식',{exact:true}).selectOption('thermal_ml');
 for(const [i,ref] of s.query.scenes.entries())await panel.getByLabel('공통 처리 영상 '+(i+1),{exact:false}).selectOption(JSON.stringify([ref.provider_id,ref.collection,ref.id]));
 for(const detail of await panel.locator('details').filter({has:page.locator('summary').filter({hasText:'이 장면의 제품·필수 밴드/QA 확인'})}).all()){
  await detail.locator(':scope > summary').click();await detail.getByRole('button',{name:'카탈로그 필수 밴드 선택'}).click();
 }
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();
 expect(s.counts().starts).toBe(0);
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();
 await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 await expect(panel.getByRole('region',{name:'ML 공간 검증 결과'})).toContainText('통과');
 await expect(panel.getByRole('region',{name:'구름 제거 전처리 결과'})).toContainText('ML 추정');
 await expect(panel.getByRole('region',{name:'ML 공간 검증 결과'}).locator(':scope > details')).not.toHaveAttribute('open');
 await expect(panel.locator('.processing-outcome').getByText('실행된 전처리·계산·파일 검증 기록',{exact:true}).locator('..')).not.toHaveAttribute('open');
 await mkdir('../test-results/outcome-readability',{recursive:true});await panel.locator('.processing-outcome').screenshot({path:`../test-results/outcome-readability/ml-${width}.png`});
 expect(s.input()).toMatchObject({method_id:'thermal_ml',roi:{bbox:s.query.roi.bbox}});
 const receive=page.waitForEvent('download');await panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true}).click();
 const zip=info.outputPath('thermal_ml.zip');await (await receive).saveAs(zip);expect(await readFile(zip)).toEqual(s.zip);
 const record=page.waitForEvent('download');await panel.getByRole('button',{name:'연구 기록 JSON 저장',exact:true}).click();
 const file=info.outputPath('record.json');await (await record).saveAs(file);const data=JSON.parse(await readFile(file,'utf8'));
 expect(data.result.ml_validation.status).toBe('passed');expect(data.result.cloud_fill.mode).toBe('ml_estimate');expect(data.result.statistics.estimated_celsius).toBeTruthy();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});
for(const width of [390,1440])test(`TEST ONLY ${width}px researcher reads temperatures, color scale and saves reproducible record`,async({page},info)=>{
 await page.setViewportSize({width,height:844});const s=await setup(page,'surface_temperature'),panel=s.panel;
 const guide=panel.getByRole('region',{name:'연구 해석과 방법 기록'});await guide.getByText('연구 해석·방법 기록 안내',{exact:true}).click();await guide.getByText('2K·1km는 논문에 그대로 써도 되는 기준인가요?',{exact:true}).click();await expect(guide).toContainText('지역 평균의 ±2℃ 신뢰구간');
 await guide.getByText('논문 자료 출처와 방법은 어떻게 남기나요?',{exact:true}).click();await expect(guide.getByRole('link',{name:/데이터셋 DOI/})).toHaveAttribute('href','https://doi.org/10.5066/P9OGBGM6');
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 await panel.getByText('상세 통계·계산식·출처',{exact:true}).click();const stats=panel.getByRole('region',{name:'연구 결과 수치 요약'});await expect(stats).toContainText('29.661 ℃');await expect(stats).toContainText('전체 AOI나 도시 전체 평균으로 일반화하지 마세요');
 await expect(panel.getByRole('group',{name:'미리보기 색상 범위'})).toHaveCount(1);
 await expect(page.locator('.analysis-map-scale')).toContainText('같은 색이 같은 값은 아닙니다');
 await panel.getByText('연구 메모 추가·저장 내용',{exact:true}).click();await panel.getByLabel('연구 메모 · 장면 선택 이유와 기준 채택 근거 (선택)',{exact:true}).fill('TEST ONLY 연구 질문·QA 선택 근거');
 const download=page.waitForEvent('download');await panel.getByRole('button',{name:'연구 기록 JSON 저장',exact:true}).click();const file=await download,target=info.outputPath('TEST_ONLY_research.json');await file.saveAs(target);const record=JSON.parse(await readFile(target,'utf8'));
 expect(record.job.job_id).toBe(s.job.job_id);expect(record.input.roi).toEqual(s.query.roi);expect(record.result.statistics.celsius.mean).toBeCloseTo(45000*.00341802+149-273.15,5);
 expect(record.artifact.sha256).toBe(s.job.artifact!.sha256);expect(record.researcher_note).toBe('TEST ONLY 연구 질문·QA 선택 근거');expect(record.result.preview_scale.unit).toBe('degC');expect(record.product_references[0].url).toContain('10.5066/P9OGBGM6');expect(s.counts()).toEqual({plans:1,starts:1});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await stats.screenshot({path:info.outputPath('research-statistics.png')});await panel.getByRole('group',{name:'미리보기 색상 범위'}).screenshot({path:info.outputPath('research-legend.png')});
});

test('TEST ONLY failed research record uses historical job input and never exports invented results or access fields',async({page},info)=>{
 const s=await setup(page,'surface_temperature',false,true),panel=s.panel;
 Object.assign(s.job,{status:'failed',artifact:null,result:null,failure:{code:'no_valid_pixels',qa:{status:'checked_no_valid',aoi_area_m2:1e6,observed_area_m2:1e6,valid_area_m2:0,qa_policy_version:'TEST_ONLY',qa_options:{maximum_uncertainty_k:2,minimum_cloud_distance_km:1},scenes:[{id:'TEST_ONLY_0',datetime:'2025-07-10T00:00:00Z',valid_area_m2:0,exclusions_m2:{st_uncertainty:1e6}}]}}});
 (s.job as any).ownership='TEST_ONLY_DO_NOT_EXPORT';(s.job.input as any).secret='TEST_ONLY_DO_NOT_EXPORT';
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 await panel.getByLabel('같은 검색에서 다른 촬영일 선택',{exact:true}).selectOption({label:'2025-07-20 · landsat-9 · TEST_ONLY_ALTERNATIVE'});
 await expect(panel.getByRole('region',{name:'연구 기록 저장'})).toContainText('현재 바꾼 조건이 아닌');
 const pending=page.waitForEvent('download');await panel.getByRole('button',{name:'연구 기록 JSON 저장',exact:true}).click();const file=await pending,target=info.outputPath('TEST_ONLY_failed_record.json');await file.saveAs(target);const raw=await readFile(target,'utf8'),record=JSON.parse(raw);
 expect(record.result).toBeNull();expect(record.artifact).toBeNull();expect(record.failure.qa.valid_area_m2).toBe(0);expect(record.input.scenes[0].id).toBe(s.query.scenes[0].id);expect(record.input.scenes[0].id).not.toBe('TEST_ONLY_ALTERNATIVE');expect(raw).not.toContain('TEST_ONLY_DO_NOT_EXPORT');expect(s.counts()).toEqual({plans:1,starts:1});
});

for(const width of [390,1440])test(`TEST ONLY ${width}px completed QA exclusion evidence and explicit alternative date`,async({page},info)=>{
 await page.setViewportSize({width,height:844});const s=await setup(page,'surface_temperature',false,true),panel=s.panel;
 Object.assign(s.job,{status:'failed',stage:'TEST ONLY completed QA',artifact:null,result:{common_valid_area_m2:null,common_valid_percent_aoi:null},error:'TEST ONLY no valid pixels',failure:{code:'no_valid_pixels',qa:{status:'checked_no_valid',aoi_area_m2:1e6,observed_area_m2:1e6,valid_area_m2:0,qa_policy_version:'TEST_ONLY',qa_options:{maximum_uncertainty_k:2,minimum_cloud_distance_km:1},scenes:[{id:'TEST_ONLY_0',datetime:'2025-07-10T00:00:00Z',valid_area_m2:0,exclusions_m2:{base_qa_or_required_data:0,st_uncertainty:1e6,cloud_distance:0,qa_nodata_numeric:1e6}}]}}});
 await expect(panel).toContainText('월평균이나 기간 평균을 계산하지 않습니다');
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 const reason=panel.getByRole('region',{name:'분석 보류 이유와 다음 행동'});
 await expect(reason).toContainText('온도 불확실성 상한 초과·결측: 1 km²');
 await expect(reason).toContainText('온도·지수 평균이 0이라는 뜻은 아닙니다');
 await expect(panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true})).toHaveCount(0);
 await expect(panel.getByRole('heading',{name:/실제 처리 결과/})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await reason.screenshot({path:info.outputPath('qa-reasons.png')});
 await panel.getByLabel('같은 검색에서 다른 촬영일 선택',{exact:true}).selectOption({label:'2025-07-20 · landsat-9 · TEST_ONLY_ALTERNATIVE'});
 await expect(panel).toContainText('2025-07-20 (UTC) 한 촬영 시점');
 await expect(panel).toContainText('이전 조건의 분석 보류');expect(s.counts()).toEqual({plans:1,starts:1});
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await expect.poll(()=>s.counts().plans).toBe(2);
 expect(s.input()).toMatchObject({roi:{bbox:[126.7,36.4,126.71,36.41]},start_date:'2025-07-01',end_date:'2025-07-31',qa_options:{maximum_uncertainty_k:2,minimum_cloud_distance_km:1}});
 expect(s.input().scenes[0].id).toBe('TEST_ONLY_ALTERNATIVE');expect(s.counts().starts).toBe(1);
});

test('TEST ONLY quota deadline blocks premature replanning and never automatically retries',async({page})=>{
 await page.clock.install({time:new Date('2026-11-05T05:00:00Z')});
 const s=await setup(page,'surface_temperature'),panel=s.panel;
 Object.assign(s.job,{status:'failed',artifact:null,result:null,error:'TEST ONLY quota',failure:{code:'transfer_quota',retry_at:'2026-11-05T05:02:00Z'}});
 const button=panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true});await button.click();
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 await expect(panel).toContainText('원본 픽셀 읽기를 시작하지 않았습니다');await expect(button).toBeDisabled();
 await expect(panel.getByLabel('같은 검색에서 다른 촬영일 선택',{exact:true})).toHaveCount(0);
 await page.clock.fastForward(130000);await expect(button).toBeEnabled();await expect(panel).toContainText('기록된 대기시간이 지났습니다');expect(s.counts()).toEqual({plans:1,starts:1});
});

test('TEST ONLY historical failure does not invent QA exclusion numbers',async({page})=>{
 const s=await setup(page,'surface_temperature'),panel=s.panel;
 Object.assign(s.job,{status:'failed',artifact:null,result:null,error:'TEST ONLY historical failure'});
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 await expect(panel).toContainText('상세 제외 통계가 기록되지 않았습니다');await expect(panel.getByText('검사된 공통 유효 면적',{exact:true})).toHaveCount(0);
});
test('TEST ONLY keyboard retry after failed result download; expired file remains unavailable after reload',async({page})=>{
 await page.setViewportSize({width:390,height:844});const s=await setup(page,'ndvi',true),panel=s.panel;
 const plan=panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true});await plan.focus();await page.keyboard.press('Enter');
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 await panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true}).click();await expect(panel.getByRole('alert')).toContainText('HTTP 503');
 const retry=panel.getByRole('button',{name:'처리 결과 다운로드 다시 시도',exact:true});await retry.focus();const pending=page.waitForEvent('download');await page.keyboard.press('Enter');await pending;expect(s.downloads()).toBe(2);
 s.job.retention={state:'expired',expires_at:new Date(Date.now()-1000).toISOString(),remaining_seconds:0};await page.reload();await expect(panel).toContainText('서버 파일: expired');await expect(panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true})).toBeDisabled();expect(s.counts().starts).toBe(1);
});
test('TEST ONLY long processing error preserves unknown quality and wraps on mobile',async({page})=>{
 await page.setViewportSize({width:390,height:844});const s=await setup(page,'ndvi');
 await page.route('**/api/processing/plans',r=>r.fulfill({status:422,json:{detail:'TEST ONLY 실제 원본 접근 실패 · '+('매우긴오류원인'.repeat(70))+' · QA 미계산'}}));
 await s.panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await expect(s.panel.getByRole('alert')).toContainText('QA 미계산');await expect(s.panel.getByRole('button',{name:'확인한 계획 실행',exact:true})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);expect(s.counts().starts).toBe(0);
});
test('TEST ONLY threshold edit drops the old confirmed plan and never auto-runs',async({page})=>{
 const s=await setup(page,'mndwi');await s.panel.getByLabel('수역 후보 MNDWI 임계값 (-1~1)',{exact:true}).fill('.1');await s.panel.getByLabel('임계값 근거·확인 내용',{exact:true}).fill('TEST ONLY');await s.panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await expect(s.panel).toContainText('pixels_pending');
 await s.panel.getByLabel('수역 후보 MNDWI 임계값 (-1~1)',{exact:true}).fill('.2');await expect(s.panel.getByRole('button',{name:'확인한 계획 실행',exact:true})).toHaveCount(0);expect(s.counts().starts).toBe(0);
});
