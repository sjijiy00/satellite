import {test,expect,searchProduct,type Page} from './runtime';
import {fixture,status} from './fixtures';
import {readFile} from 'node:fs/promises';
import {Buffer} from 'node:buffer';

const products=[
 {profile:'pc_landsat_tirs',collection:'pc-landsat-c2-l2',purpose:'thermal',key:'qa_pixel',provider:'planetary-computer'},
 {profile:'pc_s2_msi',collection:'pc-sentinel-2-l2a',purpose:'vegetation',key:'SCL',provider:'planetary-computer'},
 {profile:'noaa_viirs_ndvi',collection:'noaa-viirs-ndvi-cdr',purpose:'vegetation',key:'ndvi',provider:'noaa-nodd'},
] as const;
async function conditions(page:Page,purpose:string){
 await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption(purpose);
 for(const [label,value] of [['시작일','2025-07-20'],['종료일','2025-07-20'],['서쪽 경도','126.7'],['남쪽 위도','36.4'],['동쪽 경도','126.71'],['북쪽 위도','36.41']])await page.getByLabel(label,{exact:true}).fill(value);
}

for(const product of products)test(`TEST ONLY 공개 경로 선택·상태·명시 수신 ${product.collection}`,async({page})=>{
 const data=fixture(product.purpose,1),scene=data.items[0];data.items=[scene];data.returned=1;data.collections=[product.collection];data.collection_statuses=[{...status(product.collection,'success',1),provider_id:product.provider}];
 Object.assign(scene,{id:'TEST_ONLY_PUBLIC',provider_id:product.provider,provider:'TEST ONLY '+product.provider,collection:product.collection,datetime:'2025-07-20T00:00:00Z',
  support:{search:true,processing:'앱 내 픽셀 처리 미지원',file_access:'asset_dependent',access_verified:false},geometry_role:product.provider==='noaa-nodd'?'product_grid_extent':'scene_footprint',temporal_role:product.provider==='noaa-nodd'?'daily_product':undefined,
  preview_diagnostic:{status:'missing_asset',has_candidate:false,message:'미리보기 Asset 없음'},
  download_assets:[{key:product.key,title:'TEST ONLY ORIGINAL',href:'https://example.test/TEST_ONLY.nc',direct_url:null,signing_required:product.provider==='planetary-computer',filename:'TEST_ONLY.nc',size_bytes:32,provider:'TEST ONLY',media_type:product.key==='ndvi'?'application/x-netcdf':'image/tiff',common_names:[],roles:['data'],requester_pays:false,access_note:'TEST ONLY'}]});
 scene.purpose_plan!.default_keys=[product.key];scene.purpose_plan!.analysis_keys=[];
 let downloads=0;
 await page.route('**/api/search',r=>r.fulfill({json:data}));await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY_PUBLIC'}}));
 await page.route('**/api/media/inspect',r=>r.fulfill({json:{reference:{id:scene.id,collection:scene.collection,provider_id:scene.provider_id},preview:null,assets:[{key:product.key,status:'available',message:'TEST ONLY 범위 확인 · 전체 수신 전',download_url:'/api/media/downloads/TEST_ONLY_PUBLIC'}]}}));
 const bytes=Buffer.concat([Buffer.from(product.key==='ndvi'?[67,68,70,2]:[73,73,42,0]),Buffer.from('TEST_ONLY_CONTENT')]);
 await page.route('**/api/media/downloads/TEST_ONLY_PUBLIC',r=>{downloads++;return r.fulfill({body:bytes,headers:{'content-type':'application/octet-stream','content-disposition':'attachment; filename="TEST_ONLY.bin"'}});});
 await conditions(page,product.purpose);await searchProduct(page,product.profile);
 await expect(page.getByTestId('applied-search-selection')).toContainText(product.collection);
 const card=page.getByTestId('scene-card').first();await expect(card).toContainText('픽셀 처리 미지원');expect(downloads).toBe(0);
 if(product.key==='ndvi'){await expect(card).toContainText('NetCDF를 이미지로 표시하지 않습니다');await expect(card).toContainText('전 지구 격자 포함');}
 const details=card.locator('details.asset-downloads');if(!await details.evaluate(e=>(e as HTMLDetailsElement).open))await details.locator('summary').first().click();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();await expect(card.getByRole('button',{name:'원본 다운로드',exact:true})).toBeEnabled();expect(downloads).toBe(0);
 const pending=page.waitForEvent('download');await card.getByRole('button',{name:'원본 다운로드',exact:true}).click();const file=await pending;await file.saveAs(`test-results/public-test-${product.key}.bin`);expect(await readFile(`test-results/public-test-${product.key}.bin`)).toEqual(bytes);expect(downloads).toBe(1);
 await page.setViewportSize({width:390,height:844});await expect(card.getByRole('button',{name:'원본 다운로드',exact:true})).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1)).toBe(true);
 expect((await card.locator('.scene-body>dl').boundingBox())!.width).toBeGreaterThan(200);
});

test('TEST ONLY 공개 검색 부분 실패·범위 밖은 0건과 구분',async({page})=>{
 let outside=false;await page.route('**/api/search',r=>{const data=fixture('vegetation',0);data.collections=['pc-sentinel-2-l2a','noaa-viirs-ndvi-cdr'];data.outcome=outside?'outside_scope':'partial';data.collection_statuses=outside?[{...status('noaa-viirs-ndvi-cdr','outside_scope'),reason:'outside_supported_period',requests:0,complete:true}]:[status('pc-sentinel-2-l2a','failed'),status('noaa-viirs-ndvi-cdr','empty')];return r.fulfill({json:data});});
 await conditions(page,'vegetation');await searchProduct(page,'pc_s2_msi');await expect(page.getByTestId('search-status')).toContainText('부분 검색 완료');
 outside=true;await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();await expect(page.getByTestId('search-status')).toContainText('지원 범위 밖');await expect(page.getByRole('heading',{name:'연결 제품의 지원 범위 밖입니다',exact:true})).toBeVisible();
});

for(const product of products)test(`LIVE 익명 검색→선택→미리보기 상태→원본 파일 ${product.collection}`,async({page,context},testInfo)=>{
 test.skip(process.env.LIVE_STAC!=='1','공개 실연결은 별도 실행');test.setTimeout(240000);
 let inspections=0;
 page.on('request',r=>{if(r.url().endsWith('/api/media/inspect'))inspections++;});
 page.on('response',r=>{if(r.url().endsWith('/api/media/inspect'))inspections=Math.max(0,inspections-1);});
 page.on('requestfailed',r=>{if(r.url().endsWith('/api/media/inspect'))inspections=Math.max(0,inspections-1);});
 await conditions(page,product.purpose);
 if(product.key!=='ndvi')await page.getByLabel('종료일',{exact:true}).fill('2025-07-26');
 const pendingSearch=page.waitForResponse(r=>r.url().endsWith('/api/search'));
 await searchProduct(page,product.profile);const response=await pendingSearch,data=await response.json();
 console.log(JSON.stringify({scope:'LIVE anonymous public',collection:product.collection,status:response.status(),outcome:data.outcome,returned:data.returned,statuses:data.collection_statuses?.map((s:{status:string;reason:string})=>({status:s.status,reason:s.reason}))}));
 expect(response.status()).toBe(200);expect(data.returned).toBeGreaterThan(0);expect(data.items.every((s:{collection:string})=>s.collection===product.collection)).toBe(true);
 const card=page.getByTestId('scene-card').first();await card.scrollIntoViewIfNeeded();
 if(product.key==='ndvi'){await expect(card).toContainText('미리보기 미제공');await expect(card).toContainText('NetCDF를 이미지로 표시하지 않습니다');}
 else {await expect(card.locator('img')).toBeVisible({timeout:90000});}
 const details=card.locator('details.asset-downloads');if(!await details.evaluate(e=>(e as HTMLDetailsElement).open))await details.locator('summary').first().click();
 await card.getByRole('button',{name:'선택 해제',exact:true}).click();await card.getByTestId('band-'+product.key).check();
 await expect.poll(()=>inspections,{timeout:90000}).toBe(0);
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();const button=card.getByRole('button',{name:'원본 다운로드',exact:true});await expect(button).toBeEnabled({timeout:90000});
 expect((await context.cookies()).some(c=>/earthdata|edl|microsoft/i.test(c.name))).toBe(false);
 const pending=page.waitForEvent('download');await button.click();const file=await pending;expect(await file.failure()).toBeNull();
 const path=`test-results/public-live-${product.key}.${product.key==='ndvi'?'nc':'tif'}`;await file.saveAs(path);const bytes=await readFile(path);
 expect(bytes.length).toBeGreaterThan(1024);expect(product.key==='ndvi'?['89484446','43444601','43444602']:['49492a00','4d4d002a','49492b00','4d4d002b']).toContain(bytes.subarray(0,4).toString('hex'));
 const evidence={collection:product.collection,provider:product.provider,item_id:data.items[0].id,datetime:data.items[0].datetime,preview:product.key==='ndvi'?'missing_asset':'provider_image_visible',bytes:bytes.length,magic:bytes.subarray(0,8).toString('hex'),filename:file.suggestedFilename(),scope:'Full file received; decoded variable/pixels verified separately. Not AOI QA.'};
 console.log(JSON.stringify(evidence));await testInfo.attach('anonymous-public-file',{body:JSON.stringify(evidence),contentType:'application/json'});
 await card.screenshot({path:`test-results/public-live-${product.key}-desktop.png`});
 await page.setViewportSize({width:390,height:844});await card.screenshot({path:`test-results/public-live-${product.key}-mobile.png`});
});
