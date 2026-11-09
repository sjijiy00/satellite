// Explicit public PC search/canonical Range/processing artifact, no paid AI/browse/original delivery.
import {mkdir,writeFile} from 'node:fs/promises';
import {spawnSync} from 'node:child_process';
import path from 'node:path';
import {test,expect,searchProduct} from './runtime';
test('LIVE PC Landsat ST search → user selection → actual QA/temperature → browser ZIP reopen',async({page},info)=>{
 test.skip(process.env.LIVE_STAC!=='1'||process.env.LIVE_PROCESSING!=='1','Explicit public LIVE flags');test.setTimeout(180000);
 await page.route('**/api/media/**',r=>r.abort());
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
 for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String([-115.15,36.16,-115.14,36.17][i]));
 const pending=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/search'&&r.request().method()==='POST');await searchProduct(page,'pc_landsat_tirs');
 const response=await pending,data=await response.json(),id='LC08_L2SP_039035_20250719_02_T1';expect(response.status()).toBe(200);
 expect(data.items.some((s:{id:string;collection:string})=>s.id===id&&s.collection==='pc-landsat-c2-l2')).toBe(true);
 await page.getByRole('group',{name:'촬영 날짜',exact:true}).getByRole('button',{name:/2025-07-19/}).click();
 const card=page.getByTestId('scene-card').filter({hasText:id});await expect(card).toHaveCount(1);await expect(card.getByTestId('card-processing')).toContainText('제품별 실행 후보');await card.getByRole('button',{name:'지도에서 선택',exact:true}).click();
 await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();const selection=page.getByTestId('analysis-selection');await selection.locator('input[value="surface_temperature"]').check();await selection.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 const panel=page.getByTestId('processing-foundation'),details=panel.locator('details').filter({hasText:'이 장면의 제품·필수 밴드/QA 확인'});await details.locator('summary').click();
 for(const key of ['qa','cdist'])await details.getByLabel(key,{exact:true}).check();
 await panel.getByRole('button',{name:'공통 처리 계획 검사',exact:true}).click();await expect(panel).toContainText('pixels_pending');
 await panel.getByLabel('현재 장면·AOI·기간·QA 정책과 산출물을 확인했습니다',{exact:true}).check();await panel.getByRole('button',{name:'확인한 계획 실행',exact:true}).click();
 await expect.poll(async()=>await panel.getByTestId('processing-job').innerText(),{timeout:100000}).toContain('succeeded');
 await expect(page.locator('.map-legend')).toContainText('실제 지표면 온도');
 const downloadEvent=page.waitForEvent('download');await panel.getByRole('button',{name:'검증된 처리 ZIP 다운로드',exact:true}).click();const file=await downloadEvent,saved=info.outputPath('actual-pc-temperature.zip');await file.saveAs(saved);expect(await file.failure()).toBeNull();await expect(panel).toContainText('SHA-256 확인');
 const check=spawnSync(path.resolve('../.venv/Scripts/python.exe'),['-c',`import sys,zipfile,json,hashlib,numpy as np;from rasterio.io import MemoryFile
with zipfile.ZipFile(sys.argv[1]) as z:
 m=json.loads(z.read('manifest.json'));assert m['input']['method_id']=='surface_temperature' and m['verified_after_disk_write']
 assert m['execution_record']['source_mode']=='canonical_server_range'
 assert any(s['id']=='files' and s['status']=='completed' for s in m['execution_record']['steps'])
 assert m['sources'][0]['id']=='LC08_L2SP_039035_20250719_02_T1'
 for name,entry in m['files'].items():
  assert hashlib.sha256(z.read(name)).hexdigest()==entry['sha256']
  if name.endswith('.tif'):
   with MemoryFile(z.read(name)) as mem:
    with mem.open() as ds:
     assert ds.crs and ds.nodata is not None and ds.read().size
     if name=='temperature.tif':
      a=ds.read(masked=True);assert ds.tags(1)['unit']=='K' and ds.tags(2)['unit']=='degC';assert np.allclose((a[0]-a[1]).compressed(),273.15,atol=.0001)
`,saved],{encoding:'utf8',windowsHide:true});expect(check.status,'Actual PC temperature ZIP and TIFF content reopen').toBe(0);
 await expect(panel).toContainText('실행된 전처리·계산·파일 검증 기록');await expect(panel).toContainText('서버 파일: available');
 const out=path.join(process.env.E2E_EVIDENCE_DIR||'../test-results/product-engines-20261103-210850','live-browser');await mkdir(out,{recursive:true});await writeFile(path.join(out,'result.json'),JSON.stringify({checked_at:new Date().toISOString(),item:id,search_http:response.status(),search_returned:data.returned,product:'PC Landsat 8 L2SP Collection 2',bbox:[-115.15,36.16,-115.14,36.17],actual_job:'succeeded',complete_browser_zip_saved_and_reopened:true,excluded:'provider browse/full original files/GIS GUI/AI'},null,2));await panel.screenshot({path:path.join(out,'panel.png')});
});
