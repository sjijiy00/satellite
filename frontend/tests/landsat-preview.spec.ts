// TEST ONLY media responses. No provider credentials or signed URLs.
import {test,expect,searchProduct,type Page,type Route} from './runtime';
import {fixture} from './fixtures';
import {writeFile,mkdir} from 'node:fs/promises';
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNoclu1BQAE5wIngLnp3wAAAABJRU5ErkJggg==','base64');
const original={status:'usgs_login_required',message:'USGS 원본은 별도 로그인이 필요합니다.',access_verified:false,http_status:302,redirect_host:'ers.cr.usgs.gov',original_status:'requester_pays'};
function result(id:string,pc=false,count=1){
 const d=fixture('thermal',count);d.items=d.items.filter(s=>s.collection==='landsat-c2-l2').map((s,i)=>({...s,id:i?id+'_B':id,provider_id:pc?'planetary-computer':'earth-search',collection:pc?'pc-landsat-c2-l2':'landsat-c2-l2',provider:pc?'Planetary Computer TEST ONLY':'Earth Search TEST ONLY',thumbnail:null,preview_diagnostic:{status:'missing_asset',message:'TEST ONLY original missing thumbnail',has_candidate:false},
  download_assets:s.download_assets?.filter(a=>a.key==='lwir11').map(a=>({...a,requester_pays:!pc,direct_url:null,signing_required:pc})),purpose_plan:{...s.purpose_plan!,default_keys:['lwir11'],analysis_keys:['lwir11'],visual_keys:['lwir11']}}));d.returned=d.items.length;return d;
}
function available(id:string){return {status:'available',message:'TEST ONLY actual bytes fixture',access_verified:true,url:'/api/media/previews/'+id,source_asset:'rendered_preview',source_provider_id:'planetary-computer',source_label:'Planetary Computer 제공 미리보기',source_reference:{provider_id:'planetary-computer',collection:'pc-landsat-c2-l2',id},product_match:{status:'exact',product_id:'TEST_ONLY_FULL_PRODUCT',platform:'landsat-9',datetime:'2025-07-01T02:00:00Z',processing_level:'L2SP',collection_version:'02'},original_access:original};}
async function setup(page:Page,preview:unknown|((r:Route)=>Promise<void>),count=1){
 const searches:any[]=[];let probes=0,downloads=0;
 await page.route('**/api/search',r=>{const q=r.request().postDataJSON();searches.push(q);const pc=q.collections?.includes('pc-landsat-c2-l2');const data=result('TEST_ONLY_LANDSAT',pc,count);data.query={bbox:q.bbox,start_date:q.start_date,end_date:q.end_date};return r.fulfill({json:data});});
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY_LANDSAT',expires_at:Date.now()/1000+3600}}));
 await page.route('**/api/media/inspect',r=>{
  if(typeof preview==='function')return preview(r);
  const q=r.request().postDataJSON();if(q.asset_keys?.length)probes++;
  return r.fulfill({json:{reference:q,preview:q.include_preview?preview:null,assets:q.asset_keys.map((key:string)=>({key,...original})),notice:'TEST ONLY'}});
 });
 await page.route('**/api/media/previews/**',r=>r.fulfill({body:png,contentType:'image/png'}));
 await page.route('**/api/media/downloads/**',r=>{downloads++;return r.abort();});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
 for(const [i,l] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(l,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));
 await searchProduct(page,'landsat_tirs');await page.locator('.imagery-preview').scrollIntoViewIfNeeded();
 return {searches,counts:()=>({probes,downloads})};
}
const preview=(page:Page)=>page.locator('.imagery-preview .provider-preview');

test('TEST ONLY 원본 미리보기 없어도 정확한 PC preview 표시 · 선택/밴드/원본 권한 유지',async({page})=>{
 const state=await setup(page,available('TEST_ONLY_LANDSAT'));await expect(preview(page).locator('img')).toBeVisible();
 await expect(preview(page)).toContainText('Planetary Computer 제공 미리보기');
 expect(state.counts()).toEqual({probes:0,downloads:0});expect(state.searches).toHaveLength(1);
 const card=page.getByTestId('scene-card').first();const details=card.locator('.asset-downloads');if(!await details.evaluate(e=>(e as HTMLDetailsElement).open))await details.locator(':scope > summary').click();
 await expect(card.getByTestId('band-lwir11')).toBeChecked();await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await expect(card.locator('.managed-asset-access').getByRole('button',{name:'원본 다운로드',exact:true})).toBeDisabled();
 await expect(card.locator('.managed-asset-access')).toContainText('USGS 원본은 별도 로그인이 필요합니다.');
 await expect(page.getByRole('region',{name:'현재 작업 요약'})).toContainText('Earth Search');
 await expect(page.getByRole('region',{name:'현재 작업 요약'})).toContainText('원본 전체 수신 0/');
 await expect(card.locator('.managed-asset-access').getByText('제공처 HTTP 302',{exact:false})).toBeHidden();
 expect(state.counts().downloads).toBe(0);
});

for(const status of ['product_mismatch','missing_asset','provider_error'])test(`TEST ONLY PC ${status}는 기존 실패 유지 · 상세/동일 조건 명시 PC 검색`,async({page})=>{
 const state=await setup(page,{...original,alternate_preview:{provider_id:'planetary-computer',status,message:'TEST ONLY PC 확인 실패',access_verified:false,http_status:status==='provider_error'?503:null}});
 await expect(preview(page)).toContainText(original.message);await expect(preview(page).locator('img')).toHaveCount(0);
 await expect(preview(page).getByText('제공처 HTTP 302',{exact:false})).toBeHidden();
 await preview(page).getByText('미리보기 출처·접근 상세',{exact:true}).click();await expect(preview(page)).toContainText(status);await expect(preview(page)).toContainText('ers.cr.usgs.gov');
 expect(state.searches).toHaveLength(1);await preview(page).getByRole('button',{name:'PC Landsat에서 검색',exact:true}).click();
 await expect.poll(()=>state.searches.length).toBe(2);
 expect(state.searches[1]).toMatchObject({purpose_type:'thermal',bbox:[126.7,36.4,126.71,36.41],start_date:'2025-07-01',end_date:'2025-07-31',collections:['pc-landsat-c2-l2'],recommendation_id:null});
 await expect(page.getByTestId('effective-search-selection')).toContainText('pc-landsat-c2-l2');expect(state.counts().downloads).toBe(0);
});

test('TEST ONLY 장면 변경 중 늦은 PC 미리보기가 현재 장면을 덮지 않음 · 모바일',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 let release!:()=>void,started!:()=>void;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 await setup(page,async (r:Route)=>{const q=r.request().postDataJSON();if(q.id==='TEST_ONLY_LANDSAT'){started();await gate;}await r.fulfill({json:{reference:q,preview:available(q.id),assets:[],notice:'TEST ONLY'}}).catch(()=>{});},2);
 await ready;
 await page.getByTestId('scene-card').nth(1).getByRole('button',{name:'지도에서 선택',exact:true}).click();
 await page.locator('.imagery-preview').scrollIntoViewIfNeeded();await expect(preview(page).locator('img')).toHaveAttribute('src','/api/media/previews/TEST_ONLY_LANDSAT_B');
 release?.();await expect(preview(page).locator('img')).not.toHaveAttribute('src','/api/media/previews/TEST_ONLY_LANDSAT');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('TEST ONLY 공개 PC 재검색 장애를 성공 이미지로 대체하지 않음',async({page})=>{
 await setup(page,{...original,alternate_preview:{provider_id:'planetary-computer',status:'timeout',message:'TEST ONLY timeout',access_verified:false}});
 await expect(preview(page)).toContainText('제공처 미리보기 응답을 제한 시간 안에 받지 못했습니다.');
 await page.route('**/api/search',r=>r.fulfill({status:503,json:{error:{message:'TEST ONLY PC search unavailable'}}}));
 await preview(page).getByRole('button',{name:'PC Landsat에서 검색',exact:true}).click();await expect(page.getByRole('alert').first()).toContainText('TEST ONLY PC search unavailable');
 await expect(page.getByTestId('scene-card')).toHaveCount(0);
});

test('TEST ONLY 미리보기 504는 제공처 시간 초과로 표시하고 선택을 보존',async({page})=>{
 const state=await setup(page,{status:'provider_error',http_status:504,message:'제공처 요청에 실패했습니다.',access_verified:false});
 await expect(preview(page)).toContainText('제공처 미리보기 서버가 시간 초과(HTTP 504)를 반환했습니다.');
 await expect(preview(page)).toContainText('원본 접근·분석 가능 여부는 별도로 확인');
 await expect(preview(page).locator('img')).toHaveCount(0);
 await expect(preview(page).getByRole('button',{name:'미리보기 재시도'})).toBeEnabled();
 expect(state.searches).toHaveLength(1);expect(state.counts().downloads).toBe(0);
});

test('LIVE Earth Search Landsat 정확한 PC 미리보기 전체 PNG · 원본 선택 보존',async({page})=>{
 test.skip(process.env.LIVE_LANDSAT_PREVIEW!=='1','공개 제공처 실연결은 명시 opt-in');test.setTimeout(120000);
 const id='LC09_L2SP_116035_20250723_02_T1';let originalDownloads=0;
 page.on('request',r=>{if(new URL(r.url()).pathname.includes('/api/media/downloads/'))originalDownloads++;});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-20');await page.getByLabel('종료일',{exact:true}).fill('2025-07-26');
 for(const [i,l] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(l,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));
 const searching=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/search'&&r.request().method()==='POST');
 const inspecting=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/media/inspect'&&r.request().postDataJSON()?.id===id&&r.request().postDataJSON()?.include_preview);
 const receiving=page.waitForResponse(r=>new URL(r.url()).pathname.startsWith('/api/media/previews/')&&r.status()===200);
 await searchProduct(page,'landsat_tirs');const data=await(await searching).json();
 expect(data.items.some((s:any)=>s.id===id&&s.provider_id==='earth-search'&&s.collection==='landsat-c2-l2')).toBe(true);
 await page.locator('.imagery-preview').scrollIntoViewIfNeeded();const report=await(await inspecting).json(),p=report.preview;
 expect(p.status).toBe('available');expect(p.source_provider_id).toBe('planetary-computer');expect(report.reference).toMatchObject({provider_id:'earth-search',collection:'landsat-c2-l2',id});
 await expect(preview(page).locator('img')).toBeVisible();await expect.poll(()=>preview(page).locator('img').evaluate((i:HTMLImageElement)=>i.complete&&i.naturalWidth>0)).toBe(true);
 const response=await receiving,body=await response.body();expect(body.subarray(0,8)).toEqual(Buffer.from([137,80,78,71,13,10,26,10]));expect(body.length).toBeLessThan(8*1024**2);
 const dimensions=await preview(page).locator('img').evaluate((i:HTMLImageElement)=>({width:i.naturalWidth,height:i.naturalHeight}));
 const card=page.getByTestId('scene-card').first();if(!await card.locator('.asset-downloads').evaluate(e=>(e as HTMLDetailsElement).open))await card.locator('.asset-downloads > summary').click();
 await expect(card.getByTestId('band-lwir11')).toBeChecked();await expect(page.getByRole('region',{name:'현재 작업 요약'})).toContainText(id);
 expect(originalDownloads).toBe(0);await mkdir('../test-results/landsat-preview',{recursive:true});
 await writeFile('../test-results/landsat-preview/browser-preview.png',body);
 await writeFile('../test-results/landsat-preview/browser.json',JSON.stringify({time_utc:new Date().toISOString(),reference:report.reference,product_match:p.product_match,source_provider:p.source_provider_id,original_status:p.original_access?.status,original_http:p.original_access?.http_status,original_redirect_host:p.original_access?.redirect_host,bytes:body.length,dimensions,original_download_requests:originalDownloads},null,2));
 await preview(page).evaluate(e=>e.scrollIntoView({block:'center'}));await expect(preview(page).locator('img')).toBeVisible();await preview(page).screenshot({path:'../test-results/landsat-preview/browser-desktop.png'});
 await page.setViewportSize({width:390,height:844});await preview(page).evaluate(e=>e.scrollIntoView({block:'center'}));await expect(preview(page).locator('img')).toBeVisible();await expect.poll(()=>preview(page).locator('img').evaluate((i:HTMLImageElement)=>i.complete&&i.naturalWidth>0)).toBe(true);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);await preview(page).screenshot({path:'../test-results/landsat-preview/browser-mobile.png'});
});
