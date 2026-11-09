import {test,expect,searchProduct} from './runtime';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
test('LIVE graduate review: Gumi search, scene selection and research questions without AI or processing',async({page})=>{
 test.skip(process.env.LIVE_STAC!=='1','Explicit public source search only');
 const out=path.resolve('../test-results/graduate-review-20261105');await mkdir(out,{recursive:true});
 let starts=0;await page.route('**/api/processing/jobs',r=>{starts++;return r.abort();});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');
 await page.getByLabel('시작일',{exact:true}).fill('2026-07-01');await page.getByLabel('종료일',{exact:true}).fill('2026-07-31');
 for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String([128.28865,36.07461,128.39985,36.16453][i]));
 const response=page.waitForResponse(r=>r.url().endsWith('/api/search')&&r.request().method()==='POST');
 await searchProduct(page,'pc_landsat_tirs');const search=await response;expect(search.ok()).toBe(true);const data=await search.json();expect(data.items.length).toBeGreaterThan(0);
 await writeFile(path.join(out,'live-search-summary.json'),JSON.stringify({query:data.query,returned:data.returned,outcome:data.outcome,collections:data.collections,items:data.items.map((s:any)=>({id:s.id,datetime:s.datetime,platform:s.platform,scene_cloud_cover:s.scene_cloud_cover}))},null,2));
 await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();const panel=page.getByTestId('analysis-selection');await panel.locator('input[value="surface_temperature"]').check();await panel.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 const processing=page.getByTestId('processing-foundation');await expect(processing).toContainText('2K/1km');
 await writeFile(path.join(out,process.env.GRADUATE_AFTER?'live-after.txt':'live-before.txt'),await processing.innerText());
 await processing.screenshot({path:path.join(out,process.env.GRADUATE_AFTER?'live-after.png':'live-before.png')});
 if(process.env.GRADUATE_AFTER){await expect(processing.getByRole('region',{name:'연구 해석과 방법 기록'})).toBeVisible();}
 expect(starts).toBe(0);
});
