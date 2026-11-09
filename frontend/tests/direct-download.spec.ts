import {test,expect,searchProduct,openBandPanel} from './runtime';
import {fixture} from './fixtures';
import {Buffer} from 'node:buffer';

for(const denied of [false,true])test(`TEST ONLY Landsat one-click download ${denied?'denied without navigation':'checks and saves exact file'}`,async({page},info)=>{
 await page.setViewportSize({width:390,height:844});
 const data=fixture('thermal',1);data.items=data.items.filter(s=>s.collection==='landsat-c2-l2');data.returned=1;
 const scene=data.items[0];scene.download_assets=scene.download_assets!.filter(a=>a.key==='lwir11');
 Object.assign(scene.download_assets[0],{direct_url:null,href:'s3://TEST_ONLY/ST_B10.TIF',requester_pays:true,access_note:'AWS 인증 및 요청자 비용 동의 필요'});
 scene.purpose_plan!.default_keys=['lwir11'];const reference={provider_id:scene.provider_id,collection:scene.collection,id:scene.id};
 let checks=0,downloads=0;
 await page.route('**/api/search',r=>r.fulfill({json:data}));
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY',expires_at:Date.now()/1000+3600}}));
 await page.route('**/api/media/inspect',async r=>{
  const b=r.request().postDataJSON();if(b.asset_keys.length)checks++;
  await r.fulfill({json:{reference,preview:null,assets:b.asset_keys.map((key:string)=>({key,status:denied?'operator_permission_denied':'available',message:denied?'TEST ONLY USGS 권한 거절':'TEST ONLY 범위 확인',access_verified:!denied,...(!denied?{download_url:'/api/media/downloads/TEST_ONLY'}:{})})),notice:'TEST ONLY'}});
 });
 await page.route('**/api/media/downloads/**',r=>{downloads++;return r.fulfill({body:Buffer.from('TEST_ONLY_TIFF_BYTES'),contentType:'application/octet-stream',headers:{'Content-Disposition':'attachment; filename="TEST_ONLY_ST_B10.TIF"'}});});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');await page.getByRole('button',{name:'충남 예시 영역'}).click();await searchProduct(page,'landsat_tirs');
 const card=page.getByTestId('primary-results').getByTestId('scene-card').first();await openBandPanel(card);
 expect(checks).toBe(0);expect(downloads).toBe(0);
 const button=card.getByRole('button',{name:'lwir11 바로 다운로드',exact:true});
 if(denied){await button.click();await expect(card).toContainText('TEST ONLY USGS 권한 거절');expect(downloads).toBe(0);}
 else{const download=page.waitForEvent('download');await button.click();expect((await download).suggestedFilename()).toBe('TEST_ONLY_ST_B10.TIF');await expect(card).toContainText('파일 전체 수신 완료');expect(downloads).toBe(1);}
 // Edge opens its own downloads UI; only external HTTP(S) navigation is forbidden.
 expect(checks).toBe(1);await expect(page).toHaveURL(/\/$/);expect(page.context().pages().map(p=>p.url()).filter(url=>/^https?:/.test(url)&&new URL(url).origin!==new URL(page.url()).origin)).toEqual([]);
 await card.locator('.managed-asset-access').screenshot({path:info.outputPath('direct-download.png')});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});

test('LIVE USGS exact QA band saved in browser without EarthExplorer',async({page},info)=>{
 test.skip(process.env.LIVE_STAC!=='1','Explicit live provider test only');
 await page.goto('/');await page.getByRole('button',{name:'직접 입력으로 계속',exact:true}).click();
 await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');
 await page.getByLabel('시작일',{exact:true}).fill('2026-07-01');await page.getByLabel('종료일',{exact:true}).fill('2026-07-31');
 for(const [label,value] of [['서쪽 경도','128.28865'],['남쪽 위도','36.07461'],['동쪽 경도','128.39985'],['북쪽 위도','36.16453']])await page.getByLabel(label,{exact:true}).fill(value);
 await searchProduct(page,'landsat_tirs');
 const card=page.getByTestId('primary-results').getByTestId('scene-card').filter({has:page.getByText('LC08_L2SP_115035_20260711_02_T1',{exact:true})}).first();
 await expect(card).toBeVisible({timeout:60000});await openBandPanel(card);await card.getByRole('button',{name:'선택 해제',exact:true}).click();await card.getByTestId('band-qa_pixel').check();
 const saved=page.waitForEvent('download',{timeout:120000});await card.getByRole('button',{name:'qa_pixel 바로 다운로드',exact:true}).click();
 const download=await saved;expect(download.suggestedFilename()).toBe('LC08_L2SP_115035_20260711_20260720_02_T1_QA_PIXEL.TIF');
 await download.saveAs(info.outputPath(download.suggestedFilename()));await expect(card).toContainText('파일 전체 수신 완료');
 await card.locator('.managed-asset-access').screenshot({path:info.outputPath('live-download.png')});await expect(page).toHaveURL(/\/$/);
});
