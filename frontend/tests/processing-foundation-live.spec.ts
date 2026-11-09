// Explicit real public search/range processing. No paid AI, provider login or full originals.
import {mkdir,writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {test,expect,searchProduct} from './runtime';
import {sceneKey,type Scene} from '../src/lib/types';
test('LIVE public search → canonical processing → actual map → complete ZIP reopen',async({page},info)=>{
 test.skip(process.env.LIVE_STAC!=='1'||process.env.LIVE_PROCESSING!=='1','Explicit LIVE_STAC + LIVE_PROCESSING');test.setTimeout(180000);
 // This test intentionally excludes provider browse/original delivery. Abort
 // automatic preview transport instead of spending additional provider bytes.
 await page.route('**/api/media/**',r=>r.abort());
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 await page.getByLabel('시작일',{exact:true}).fill('2021-07-01');await page.getByLabel('종료일',{exact:true}).fill('2021-07-31');
 for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));
 const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/search'&&r.request().method()==='POST');await searchProduct(page,'s2_msi');
 const response=await pending,data=await response.json();expect(response.status()).toBe(200);expect(data.outcome).toBe('success');
 const ids=['S2B_52SBF_20210716_0_L2A','S2B_52SBF_20210726_0_L2A'];
 const scenes=ids.map(id=>data.items.find((s:Scene)=>s.id===id&&s.provider_id==='earth-search'&&s.collection==='sentinel-2-l2a'));
 expect(scenes.every(Boolean),'Exact canonical sample Items must exist in actual search; no replacement scenes').toBe(true);
 await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();const selection=page.getByTestId('analysis-selection');
 await selection.locator('input[value="vegetation_change"]').check();await selection.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 const panel=page.getByTestId('processing-foundation');await panel.getByLabel('공통 처리 영상 1',{exact:true}).selectOption(sceneKey(scenes[0]));await panel.getByLabel('공통 처리 영상 2',{exact:true}).selectOption(sceneKey(scenes[1]));
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await expect(panel).toContainText('canonical_metadata_checked_pixels_pending');
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();
 const started=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/processing/jobs'&&r.request().method()==='POST');await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 const jobStart=await(await started).json();expect(/^[a-f0-9]{32}$/.test(jobStart.job_id)).toBe(true);
 await expect(panel.getByTestId('processing-job')).toContainText('succeeded',{timeout:100000});await expect(page.locator('.map-legend')).toContainText('실제 NDVI');
 const event=page.waitForEvent('download');await panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true}).click();const download=await event;
 const saved=info.outputPath('actual-public-processing.zip');await download.saveAs(saved);expect(await download.failure()).toBeNull();await expect(panel).toContainText('SHA-256 확인');
 const verified=spawnSync(path.resolve('../.venv/Scripts/python.exe'),['-c',`import sys,zipfile,json,hashlib;from rasterio.io import MemoryFile
with zipfile.ZipFile(sys.argv[1]) as z:
 m=json.loads(z.read('manifest.json'));assert m['verified_after_disk_write']
 assert m['input']['start_date']=='2021-07-01'
 for n,e in m['files'].items():
  assert hashlib.sha256(z.read(n)).hexdigest()==e['sha256']
  if n.endswith('.tif'):
   with MemoryFile(z.read(n)) as mem:
    with mem.open() as ds:assert ds.crs and ds.nodata is not None and ds.read().size>0
`,saved],{encoding:'utf8',windowsHide:true});expect(verified.status,'Actual browser-downloaded TIFF/manifest reopens').toBe(0);
 await mkdir('../test-results/foundation-20261103-200942/live-browser',{recursive:true});
 await writeFile('../test-results/foundation-20261103-200942/live-browser/result.json',JSON.stringify({checked_at:new Date().toISOString(),scope:'real public search, canonical range processing, map, browser full ZIP save and reopen; browse/original transfer excluded',search_http:response.status(),search_returned:data.returned,items:ids,job_status:'succeeded',browser_complete_download_and_reopen:true},null,2));
 await panel.screenshot({path:'../test-results/foundation-20261103-200942/live-browser/panel.png'});
});
