// TEST ONLY metadata/image/transfer fixtures. LIVE is explicit, read-only and preview-only.
import {mkdir,writeFile} from 'node:fs/promises';
import {test,expect,searchProduct,openBandPanel,openCollectionComparison,type Page,type Route} from './runtime';
import {sceneKey} from '../src/lib/types';
import {fixture,status} from './fixtures';
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==','base64');
function pcData(){
 const data=fixture('vegetation',2);data.items=data.items.filter(s=>s.collection==='sentinel-2-l2a').map((s,i)=>({...s,
  id:'TEST_ONLY_PC_S2_'+i,provider_id:'planetary-computer',provider:'Planetary Computer TEST ONLY',collection:'pc-sentinel-2-l2a',platform:'sentinel-2b',product_type:'S2MSI2A',processing_level:'L2A',datetime:`2025-07-${i?'25':'20'}T02:00:00Z`,thumbnail:null,
  pixel_quality:{status:'not_checked',message:'실제 AOI 픽셀 QA 미검사'},support:{search:true,processing:'앱 내 픽셀 처리 미지원',file_access:'anonymous_sas',access_verified:false},
  preview_diagnostic:{status:'unchecked',has_candidate:true,message:'TEST ONLY'},
  purpose_plan:{...s.purpose_plan!,profile_id:'pc_s2_msi',analysis:'반사도 식생 분석 자료 후보',group_reason:'TEST ONLY 적색·근적외선 반사도 제품 조건 확인',default_keys:['B04','B08','SCL'],analysis_keys:['B04','B08'],visual_keys:['B04','B03','B08']},
  download_assets:['B04','B08','B03','SCL'].map(k=>({key:k,title:'TEST ONLY '+k,href:'https://example.test/TEST_ONLY/'+k+'.tif',media_type:'image/tiff',direct_url:null,requester_pays:false,signing_required:true,access_note:'계정 불필요 · 서버 SAS',common_names:[k],roles:['data']}))}));
 data.returned=2;data.collections=['pc-sentinel-2-l2a'];data.collection_statuses=[{...status('pc-sentinel-2-l2a','success',2),provider_id:'planetary-computer'}];return data;
}
async function conditions(page:Page){
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-20');await page.getByLabel('종료일',{exact:true}).fill('2025-07-26');
 for(const [i,l] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(l,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));
}
async function setup(page:Page,opts:{missing?:boolean;partial?:boolean;hold?:(r:Route)=>Promise<void>}={}){
 const data=pcData();if(opts.missing)for(const s of data.items)s.preview_diagnostic!.has_candidate=false;
 if(opts.partial){data.outcome='partial';data.collection_statuses!.push({...status('sentinel-2-l2a','failed'),provider_id:'earth-search',error:'TEST ONLY provider timeout'});}
 let originals=0,probes=0;const queries:any[]=[];
 await page.route('**/api/search',r=>{const q=r.request().postDataJSON();queries.push(q);data.query={bbox:q.bbox,start_date:q.start_date,end_date:q.end_date};return r.fulfill({json:data});});
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY_CARDS'}}));
 await page.route('**/api/media/previews/**',r=>r.fulfill({body:png,contentType:'image/png'}));
 await page.route('**/api/media/inspect',async r=>{
  const q=r.request().postDataJSON();if(q.include_preview&&opts.hold)return opts.hold(r);
  if(q.asset_keys.length)probes++;
  await r.fulfill({json:{reference:q,preview:q.include_preview&&!opts.missing?{status:'available',access_verified:true,url:'/api/media/previews/'+q.id,source_asset:'rendered_preview',message:'TEST ONLY provided PNG'}:null,
   assets:q.asset_keys.map((key:string)=>({key,status:'available',access_verified:true,message:'TEST ONLY 접근 확인 · 전체 수신 전',download_url:'/api/media/downloads/TEST_ONLY_'+key}))}});
 });
 await page.route('**/api/media/downloads/**',r=>{originals++;return r.fulfill({body:Buffer.from('II*\0TEST_ONLY_ORIGINAL'),contentType:'application/octet-stream',headers:{'Content-Disposition':'attachment; filename="TEST_ONLY_original.tif"'}});});
 await conditions(page);await searchProduct(page,'pc_s2_msi');await expect(page.getByTestId('scene-card')).toHaveCount(2);
 return {data,queries,counts:()=>({originals,probes})};
}

for(const width of [1440,390])test(`TEST ONLY ${width}px PC 카드 첫 정보·독립 품질 상태·큰 미리보기·접힌 밴드`,async({page})=>{
 await page.setViewportSize({width,height:844});const state=await setup(page),card=page.getByTestId('scene-card').first();
 await expect(card.locator('.scene-top')).toContainText('2025-07-20');await expect(card.locator('.scene-top')).toContainText('sentinel-2b · S2MSI2A');await expect(card.locator('.scene-top')).toContainText('Planetary Computer');
 const processing=card.getByTestId('card-processing');await expect(processing).toBeVisible();await expect(processing).toContainText('픽셀 처리 미지원');
 await expect(card.getByTestId('card-recommendation')).toContainText('적색·근적외선');
 await expect(card.locator('.scene-metadata')).not.toHaveAttribute('open');await expect(card.locator('.asset-downloads')).not.toHaveAttribute('open');
 const work=page.getByRole('region',{name:'현재 작업 요약',exact:true}),help=work.locator('.collection-help');
 await expect(help).not.toHaveAttribute('open');await expect(work.getByRole('link',{name:'세부 분석 선택으로'})).toBeVisible();
 await expect(help.getByText(/수신 수는/)).toBeHidden();await help.locator('summary').focus();await page.keyboard.press('Enter');
 await expect(help.getByText(/수신 수는/)).toBeVisible();await page.keyboard.press('Enter');await expect(help.getByText(/수신 수는/)).toBeHidden();
 await mkdir('../test-results/collection-disclosure',{recursive:true});await work.screenshot({path:`../test-results/collection-disclosure/summary-${width}.png`});
 const image=card.locator('.scene-preview img');await card.locator('.scene-preview').scrollIntoViewIfNeeded();await expect(image).toBeVisible();expect((await image.boundingBox())!.width).toBeGreaterThan(250);expect((await image.boundingBox())!.height).toBeGreaterThan(200);
 await expect(card.locator('.card-quality')).toContainText('전체 장면 구름량');await expect(card.locator('.card-quality')).toContainText('AOI 기하학적 중첩');await expect(card.locator('.card-pixel-qa')).toContainText('미검사');
 await expect(card.locator('figcaption')).toContainText('원본 밴드/분석 결과/픽셀 QA가 아닙니다');expect(state.counts()).toEqual({originals:0,probes:0});
 await card.getByRole('button',{name:'지도에서 선택',exact:true}).focus();await page.keyboard.press('Enter');await expect(page.getByTestId('map-selected-scene')).toHaveText(sceneKey(state.data.items[0]));
 await openBandPanel(card);await expect(card.getByTestId('band-B04')).toBeChecked();await expect(card.getByTestId('band-SCL')).toBeChecked();await card.getByRole('button',{name:'전체 선택',exact:true}).click();await expect(card.locator('input:checked')).toHaveCount(4);
 await card.getByRole('button',{name:'선택 해제',exact:true}).click();await expect(card.locator('input:checked')).toHaveCount(0);await card.getByRole('button',{name:'목적 추천으로 복원',exact:true}).click();await expect(card.locator('input:checked')).toHaveCount(3);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await card.locator('.asset-downloads > summary').click();await mkdir('../test-results/scene-cards',{recursive:true});await card.screenshot({path:`../test-results/scene-cards/card-${width}.png`});
});

test('TEST ONLY PC 날짜·목록·지도·두 장면 메타데이터 비교는 처리 실행과 분리',async({page})=>{
 const state=await setup(page);const explorer=page.getByRole('region',{name:'날짜별 영상 탐색과 레이어'});
 await page.getByTestId('scene-card').nth(1).getByRole('button',{name:'지도에서 선택',exact:true}).click();await expect(page.getByTestId('map-selected-scene')).toHaveText(sceneKey(state.data.items[1]));await expect(page.getByTestId('active-day-results')).toContainText('2025-07-25');
 await explorer.getByRole('button',{name:/2025-07-20/}).click();await expect(page.getByTestId('map-selected-scene')).toHaveText(sceneKey(state.data.items[0]));await explorer.getByRole('button',{name:/전체/}).click();await expect(page.getByTestId('scene-card')).toHaveCount(2);
 const comparison=await openCollectionComparison(page);await comparison.getByLabel('수집 비교 목적',{exact:true}).selectOption('temporal');await expect(comparison.getByLabel('수집 비교 영상 2',{exact:true})).toHaveValue(sceneKey(state.data.items[1]));
 await expect(comparison.getByRole('button',{name:/픽셀 진단|NDVI 계산|조건 검사/})).toHaveCount(0);await expect(comparison).toContainText('메타데이터·제공처 미리보기만 비교');
 await comparison.getByLabel('수집 비교 영상 2',{exact:true}).selectOption(sceneKey(state.data.items[0]));await expect(comparison).toContainText('동일 Item을 두 번 선택');expect(state.queries).toHaveLength(1);
});

test('TEST ONLY PC 원본 접근 확인과 전체 수신·링크 목록은 별개',async({page})=>{
 const state=await setup(page),card=page.getByTestId('scene-card').first();await openBandPanel(card);await expect(card.getByRole('button',{name:'선택 링크 목록 저장 (.txt)',exact:true})).toBeDisabled();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();await expect(card.getByRole('button',{name:'원본 다운로드',exact:true}).first()).toBeEnabled();expect(state.counts().originals).toBe(0);
 const receiving=page.waitForEvent('download');await card.getByRole('button',{name:'원본 다운로드',exact:true}).first().click();expect(await(await receiving).failure()).toBeNull();
 await expect(page.getByRole('region',{name:'현재 작업 요약'})).toContainText('원본 전체 수신 1/3개');await expect(card.locator('.card-pixel-qa')).toContainText('미검사');expect(state.counts()).toEqual({originals:1,probes:1});
});

test('TEST ONLY 미리보기 없음·제공처 부분 장애는 가짜 이미지로 대체하지 않음',async({page})=>{
 await setup(page,{missing:true,partial:true});await expect(page.getByTestId('search-status')).toContainText('부분 검색 완료');await expect(page.getByTestId('search-status')).toContainText('TEST ONLY provider timeout');
 await expect(page.getByTestId('search-status').locator('details')).toHaveAttribute('open');
 const card=page.getByTestId('scene-card').first();await card.scrollIntoViewIfNeeded();await expect(card.locator('.scene-preview img')).toHaveCount(0);await expect(card.locator('.scene-preview')).toContainText('미리보기 후보가 없습니다');await expect(card.locator('.card-pixel-qa')).toContainText('미검사');
});

test('TEST ONLY 선택 변경 중 늦은 미리보기는 새 카드·지도에 붙지 않음',async({page})=>{
 let release!:()=>void,started!:()=>void;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
 const state=await setup(page,{hold:async r=>{const q=r.request().postDataJSON();if(q.id.endsWith('_0')){started();await gate;}await r.fulfill({json:{reference:q,preview:{status:'available',url:'/api/media/previews/'+q.id,source_asset:'rendered_preview',message:'TEST ONLY'},assets:[]}}).catch(()=>{});}});
 await ready;await page.getByTestId('scene-card').nth(1).getByRole('button',{name:'지도에서 선택',exact:true}).click();const selected=page.getByTestId('scene-card').first();await selected.locator('.scene-preview').scrollIntoViewIfNeeded();await expect(selected.locator('img')).toHaveAttribute('src','/api/media/previews/TEST_ONLY_PC_S2_1');release();await expect(page.getByTestId('map-selected-scene')).toHaveText(sceneKey(state.data.items[1]));await expect(selected.locator('img')).not.toHaveAttribute('src','/api/media/previews/TEST_ONLY_PC_S2_0');
});

test('TEST ONLY 수신한 미리보기는 스크롤 후에도 유지 · 명시 숨기기/보기',async({page})=>{
 await page.setViewportSize({width:390,height:844});const state=await setup(page),card=page.getByTestId('scene-card').first(),preview=card.locator('.provider-preview'),image=preview.locator('img');
 await card.locator('.scene-preview').scrollIntoViewIfNeeded();await expect(image).toBeVisible();
 await page.getByLabel('시작일',{exact:true}).scrollIntoViewIfNeeded();await expect(preview).toHaveAttribute('data-preview-visible','false');await expect(image).toHaveCount(1);
 await card.locator('.scene-preview').scrollIntoViewIfNeeded();await expect(image).toBeInViewport();await preview.getByRole('button',{name:'미리보기 숨기기',exact:true}).click();await expect(image).toHaveCount(0);await expect(preview).toContainText('미리보기를 숨겼습니다');
 await preview.getByRole('button',{name:'미리보기 보기',exact:true}).click();await expect(image).toBeVisible();expect(state.counts()).toEqual({originals:0,probes:0});
});

test('LIVE PC Sentinel-2 공개 검색→카드→전체 제공처 PNG · 원본 다운로드 없음',async({page})=>{
 test.skip(process.env.LIVE_SCENE_CARDS!=='1','공개 제공처 실연결은 별도 opt-in');test.setTimeout(120000);let originalDownloads=0;
 page.on('request',r=>{if(new URL(r.url()).pathname.includes('/api/media/downloads/'))originalDownloads++;});
 await page.setViewportSize({width:1440,height:1000});await conditions(page);await page.getByLabel('위성 선택',{exact:true}).selectOption('manual');
 await page.getByLabel('Sentinel-2 Level-2A',{exact:true}).uncheck();await page.getByLabel('Landsat Collection 2 Level-2',{exact:true}).uncheck();await page.getByLabel('Sentinel-2 L2A · Planetary Computer',{exact:true}).check();await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
 const result=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/search'&&r.request().method()==='POST');await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();const response=await result,data=await response.json();
 expect(response.status()).toBe(200);expect(data.outcome).toBe('success');expect(data.returned).toBeGreaterThan(0);expect(data.items.every((s:any)=>s.provider_id==='planetary-computer'&&s.collection==='pc-sentinel-2-l2a')).toBe(true);
 await mkdir('../test-results/scene-cards',{recursive:true});await writeFile('../test-results/scene-cards/live-search.json',JSON.stringify({time_utc:new Date().toISOString(),http:response.status(),outcome:data.outcome,returned:data.returned,items:data.items.map((s:any)=>({id:s.id,provider_id:s.provider_id,collection:s.collection,datetime:s.datetime,product_type:s.product_type,scene_cloud_cover:s.scene_cloud_cover,overlap_percent:s.overlap_percent,pixel_quality:s.pixel_quality?.status}))},null,2));
 const card=page.getByTestId('scene-card').first();await card.locator('.scene-preview').scrollIntoViewIfNeeded();const image=card.locator('.scene-preview img');await expect(image).toBeVisible({timeout:60000});await expect.poll(()=>image.evaluate((i:HTMLImageElement)=>i.complete&&i.naturalWidth>0)).toBe(true);
 const src=await image.getAttribute('src');expect(typeof src==='string'&&/^\/api\/media\/previews\/[A-Za-z0-9_-]+$/.test(src)).toBe(true);const file=await page.request.get(src!);expect(file.status()).toBe(200);const body=await file.body();expect(body.subarray(0,8)).toEqual(Buffer.from([137,80,78,71,13,10,26,10]));expect(body.length).toBeLessThanOrEqual(8*1024**2);
 const dimensions=await image.evaluate((i:HTMLImageElement)=>({width:i.naturalWidth,height:i.naturalHeight}));await expect(card.getByTestId('card-processing')).toContainText('픽셀 처리 미지원');expect(originalDownloads).toBe(0);
 await mkdir('../test-results/scene-cards',{recursive:true});await writeFile('../test-results/scene-cards/live-preview.png',body);await writeFile('../test-results/scene-cards/live.json',JSON.stringify({time_utc:new Date().toISOString(),http:response.status(),outcome:data.outcome,returned:data.returned,items:data.items.map((s:any)=>({id:s.id,provider_id:s.provider_id,collection:s.collection,datetime:s.datetime,product_type:s.product_type,scene_cloud_cover:s.scene_cloud_cover,overlap_percent:s.overlap_percent,pixel_quality:s.pixel_quality?.status})),preview:{bytes:body.length,...dimensions},original_downloads:originalDownloads},null,2));
 await card.screenshot({path:'../test-results/scene-cards/live-desktop.png'});await card.locator('.scene-preview').scrollIntoViewIfNeeded();await expect(image).toBeVisible();await card.locator('.scene-preview').screenshot({path:'../test-results/scene-cards/live-desktop-preview.png'});await page.setViewportSize({width:390,height:844});await card.locator('.scene-preview').scrollIntoViewIfNeeded();await expect(image).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await card.screenshot({path:'../test-results/scene-cards/live-mobile.png'});
});
