// TEST ONLY UI transport. ZIP contains real local fixture TIFFs, never provider data.
import {readFile,mkdir} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {test,expect,searchProduct,type Page} from './runtime';
import {fixture} from './fixtures';
const output=path.resolve('../test-results/foundation-20261103-200942/ui-fixture');
let sample:any,zip:Buffer;
test.beforeAll(async()=>{
 const p=spawnSync(path.resolve('../.venv/Scripts/python.exe'),['tests/create_processing_ui_fixture.py',output],{cwd:path.resolve('../backend'),encoding:'utf8',windowsHide:true});
 expect(p.status,'TEST ONLY local TIFF fixture generator').toBe(0);
 sample=JSON.parse(await readFile(path.join(output,'TEST_ONLY_result.json'),'utf8'));zip=await readFile(path.join(output,'TEST_ONLY_result.zip'));
});
async function setup(page:Page,holdPlan?:(r:any)=>Promise<void>){
 const data=fixture('vegetation',2);data.items=data.items.filter(s=>s.collection==='sentinel-2-l2a').map((s,i)=>({...s,id:'TEST_ONLY_'+i,provider_id:'earth-search',datetime:`2025-07-${10+i*10}T00:00:00Z`}));data.returned=data.items.length;
 let plans=0,starts=0,downloads=0,originals=0;let latest:any;
 const job={job_id:sample.job_id,status:'succeeded',stage:'TEST ONLY disk reopen complete',created_at:'2025-07-01T00:00:00Z',updated_at:'2025-07-01T00:00:00Z',error:null,result:sample.result,artifact:sample.artifact,input:sample.input};
 await page.route('**/api/search',r=>{const q=r.request().postDataJSON();data.query={bbox:q.bbox,start_date:q.start_date,end_date:q.end_date};return r.fulfill({json:data});});
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY_FOUNDATION'}}));
 await page.route('**/api/media/inspect',r=>r.fulfill({json:{reference:r.request().postDataJSON(),assets:[],preview:null}}));
 await page.route('**/api/media/downloads/**',r=>{originals++;return r.abort();});
 await page.route('**/api/processing/plans',async r=>{plans++;latest=r.request().postDataJSON();if(holdPlan)return holdPlan(r);
  return r.fulfill({json:{plan_id:'a'.repeat(32),confirmation_digest:'b'.repeat(64),status:'awaiting_confirmation',source_access:'canonical_metadata_checked_pixels_pending',pixel_quality:null,grid:{tile_count:1,width:50,height:50,resolution_m:20,aoi_area_m2:100,maximum_aoi_km2:50},input:latest,expected_artifacts:['ndvi_change.tif','valid_mask.tif','exclusion_mask.tif','manifest.json'],notice:'TEST ONLY actual pixels remain pending until explicit execution'}});});
 await page.route('**/api/processing/jobs',r=>{starts++;return r.fulfill({status:202,json:job});});
 await page.route('**/api/processing/jobs/'+sample.job_id,r=>r.fulfill({json:job}));
 await page.route('**/api/processing/jobs/'+sample.job_id+'/download',r=>{downloads++;return r.fulfill({body:zip,contentType:'application/zip',headers:{'content-length':String(zip.length),'content-disposition':'attachment; filename="TEST_ONLY_processing.zip"'}});});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
 for(const [i,l] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(l,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));
 await searchProduct(page,'s2_msi');await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();
 const selection=page.getByTestId('analysis-selection');await selection.locator('input[value="vegetation_change"]').check();await selection.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 return {panel:page.getByTestId('processing-foundation'),counts:()=>({plans,starts,downloads,originals}),input:()=>latest};
}

for(const width of [1440,390])test(`TEST ONLY ${width}px canonical server input → confirmation → verified ZIP full receive/reopen`,async({page},info)=>{
 await page.setViewportSize({width,height:844});const state=await setup(page),panel=state.panel;
 const summary=page.getByRole('region',{name:'현재 작업 요약'});
 await expect(summary.locator(':scope > details')).not.toHaveAttribute('open');
 await expect(summary.getByText('아래 실행 설정을 확인하고 처리 계획을 만드세요.',{exact:true})).toBeVisible();
 await mkdir('../test-results/processing-cleanup',{recursive:true});await summary.screenshot({path:`../test-results/processing-cleanup/summary-${width}.png`});await panel.screenshot({path:`../test-results/processing-cleanup/settings-${width}.png`});
 await expect(page.getByRole('region',{name:'현재 작업 요약'})).toContainText('원본 전체 수신 0/3개');
 await expect(panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true})).toBeEnabled();
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await expect(panel).toContainText('pixels_pending');
 expect(state.counts().starts).toBe(0);await expect(panel.getByRole('button',{name:'확인한 계획 실행',exact:true})).toBeDisabled();
 expect(state.input()).toMatchObject({purpose_type:'vegetation',analysis_id:'vegetation_change',method_id:'ndvi_change',roi:{confirmed:true,mode:'bbox',bbox:[126.7,36.4,126.71,36.41],source:'manual_bbox'},start_date:'2025-07-01',end_date:'2025-07-31'});
 expect(state.input().scenes.every((s:any)=>s.provider_id==='earth-search'&&s.asset_keys.includes('scl'))).toBe(true);
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();await expect(panel.getByTestId('processing-job')).toContainText('succeeded');
 const pending=page.waitForEvent('download');await panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true}).click();const received=await pending,filename=info.outputPath('TEST_ONLY_downloaded.zip');await received.saveAs(filename);
 await expect(panel).toContainText('SHA-256 확인');expect(await readFile(filename)).toEqual(zip);
 const verification=spawnSync(path.resolve('../.venv/Scripts/python.exe'),['-c',`import sys,zipfile,json,hashlib;from rasterio.io import MemoryFile
with zipfile.ZipFile(sys.argv[1]) as z:
 m=json.loads(z.read('manifest.json'));assert m['verified_after_disk_write']
 for n,e in m['files'].items():
  assert hashlib.sha256(z.read(n)).hexdigest()==e['sha256']
  if n.endswith('.tif'):
   with MemoryFile(z.read(n)) as mem:
    with mem.open() as ds:assert ds.crs and ds.nodata is not None and ds.read().size>0
`,filename],{encoding:'utf8',windowsHide:true});expect(verification.status,'TEST ONLY received ZIP/TIFF reopens').toBe(0);
 await page.reload();await expect(page.getByTestId('processing-job')).toContainText('succeeded');expect(state.counts()).toEqual({plans:1,starts:1,downloads:1,originals:0});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 // A shared `dl div {display:flex}` once squeezed metric values into a
 // letter-wide column even on desktop. Labels and values must stack.
 for(const cell of await panel.locator('.processing-metrics > div:visible').all()){
  const label=await cell.locator('dt').boundingBox(),value=await cell.locator('dd').boundingBox();
  expect(label).not.toBeNull();expect(value).not.toBeNull();expect(value!.y).toBeGreaterThanOrEqual(label!.y+label!.height);
 }
 await mkdir('../test-results/foundation-20261103-200942/screenshots',{recursive:true});await page.getByTestId('processing-foundation').screenshot({path:`../test-results/foundation-20261103-200942/screenshots/foundation-${width}.png`});
});

test('TEST ONLY changed scene discards a delayed plan without execution',async({page})=>{
 let release!:()=>void,started!:()=>void;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 const state=await setup(page,async r=>{started();await gate;await r.fulfill({json:{plan_id:'a'.repeat(32),status:'awaiting_confirmation'}}).catch(()=>{});});
 await state.panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await ready;
 const select=state.panel.getByLabel('공통 처리 영상 2',{exact:true});await select.selectOption('');release();
 await expect(state.panel.getByRole('button',{name:'확인한 계획 실행',exact:true})).toHaveCount(0);expect(state.counts().starts).toBe(0);
});

test('TEST ONLY server plan failure remains unknown and does not execute',async({page})=>{
 const state=await setup(page,async r=>r.fulfill({status:422,json:{detail:'TEST ONLY QA file unavailable · valid ratio unknown'}}));
 await state.panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await expect(state.panel.getByRole('alert')).toContainText('valid ratio unknown');
 expect(state.counts()).toEqual({plans:1,starts:0,downloads:0,originals:0});
});

test('TEST ONLY confirmed polygon mode survives page navigation/reload without a duplicate job',async({page})=>{
 const s=await setup(page);
 // TEST ONLY metadata/control restoration. This is not a real boundary lookup
 // or a server-approved polygon calculation; plan/job responses are fixtures.
 await page.evaluate(()=>{const saved=JSON.parse(sessionStorage.getItem('satellite-workflow-v1')!);saved.form.boundary={status:'proposed',id:'TEST_ONLY_BOUNDARY',name:'TEST ONLY 경계',year:'TEST ONLY',bbox:[126.7,36.4,126.71,36.41]};sessionStorage.setItem('satellite-workflow-v1',JSON.stringify(saved));});
 await page.reload();const panel=s.panel,polygon=panel.getByLabel('등록 행정경계를 실제 통계·클리핑 범위로 확정:',{exact:false});await polygon.check();
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await expect.poll(()=>s.input()?.roi).toMatchObject({mode:'polygon',boundary_id:'TEST_ONLY_BOUNDARY'});
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();await expect(panel.getByTestId('processing-job')).toContainText('succeeded');
 await page.reload();await expect(polygon).toBeChecked();await expect(panel.getByTestId('processing-job')).not.toContainText('이전 조건의 작업');expect(s.counts().starts).toBe(1);
});
