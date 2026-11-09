import {test,expect,searchProduct,openBandPanel,type Page} from './runtime';
import {fixture} from './fixtures';
import {Buffer} from 'node:buffer';

const image=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==','base64');
function nasa(){
 const data=fixture('vegetation',1),s=data.items[0];
 Object.assign(s,{provider_id:'nasa-cmr',collection:'viirs-vnp09ga-002',id:'G_TEST_ONLY-LPCLOUD',platform:'Suomi NPP TEST ONLY',instruments:['viirs'],processing_level:'L2G',thumbnail:'https://example.test/never-request-signed-redirect.jpg',
  preview_diagnostic:{status:'unchecked',has_candidate:true,message:'미리보기 링크 있음 · 실제 접근 미검사'},
  download_assets:[{key:'granule-0',title:'TEST ONLY HDF5',href:'https://example.test/TEST_ONLY.h5',media_type:'application/x-hdf5',direct_url:null,requester_pays:false,authentication_required:true,access_verified:false,access_note:'Earthdata 인증 필요',common_names:[],roles:['data']}]});
 Object.assign(s.purpose_plan!,{default_keys:['granule-0'],analysis_keys:[],visual_keys:[],metadata_only:true,profile_id:'viirs_sr'});
 return data;
}
const reference={provider_id:'nasa-cmr',collection:'viirs-vnp09ga-002',id:'G_TEST_ONLY-LPCLOUD'};
async function setup(page:Page){
 await page.route('**/api/search',r=>r.fulfill({json:nasa()}));
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY',expires_at:Date.now()/1000+3600}}));
 await page.route('**/api/auth/earthdata/status',r=>r.fulfill({json:{configured:false,connected:false}}));
 await page.route('**/api/auth/providers/status',r=>r.fulfill({json:{providers:[]}}));
 await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 await page.getByRole('button',{name:'충남 예시 영역'}).click();await searchProduct(page,'s2_msi');await openBandPanel(page.getByTestId('scene-card').first());
}

test('TEST ONLY 공개 browse 수신과 원본 파일 수신은 다른 버튼·상태',async({page})=>{
 const inspected:unknown[]=[];
 await page.route('**/api/media/inspect',async r=>{
  const body=r.request().postDataJSON();inspected.push(body);
  await r.fulfill({json:{reference,preview:body.include_preview?{status:'available',message:'TEST ONLY 이미지 수신 확인',access_verified:true,url:'/api/media/previews/TEST_ONLY',download_url:'/api/media/previews/TEST_ONLY?download=1',source_asset:'browse'}:null,
   assets:body.asset_keys.map((key:string)=>({key,status:'available',message:'GET 범위 접근 확인 · 전체 다운로드 미실행',access_verified:true,download_url:'/api/media/downloads/TEST_ONLY'})),notice:'TEST ONLY'}});
 });
 await page.route('**/api/media/previews/**',r=>r.fulfill({body:image,contentType:'image/png'}));
 await page.route('**/api/media/downloads/**',r=>r.fulfill({body:Buffer.from('TEST_ONLY_ORIGINAL_HDF5_BYTES'),contentType:'application/octet-stream',headers:{'Content-Disposition':'attachment; filename="TEST_ONLY.h5"'}}));
 await setup(page);
 const preview=page.locator('.imagery-preview');
 await preview.scrollIntoViewIfNeeded();
 await expect(preview.locator('img')).toHaveAttribute('src','/api/media/previews/TEST_ONLY');
 await expect(preview.getByRole('button',{name:'미리보기 이미지 저장'})).toBeVisible();
 expect(inspected).toContainEqual({...reference,asset_keys:[],include_preview:true});
 expect(inspected).not.toContainEqual({...reference,asset_keys:['granule-0'],include_preview:true});
 const card=page.getByTestId('primary-results').getByTestId('scene-card').first();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await expect(card.getByRole('button',{name:'원본 다운로드',exact:true})).toBeEnabled();
 await expect(card).toContainText('전체 다운로드 미실행');
 const download=page.waitForEvent('download');await card.getByRole('button',{name:'원본 다운로드',exact:true}).click();
 expect((await download).suggestedFilename()).toBe('TEST_ONLY.h5');
 await expect(card).toContainText('파일 전체 수신 완료 · 브라우저 저장 결과를 확인하세요.');
 expect(inspected).toContainEqual({...reference,asset_keys:['granule-0'],include_preview:false});
});

test('TEST ONLY Sentinel-1 대용량 저장은 범위 확인 후 디스크에 쓰고 완료를 표시',async({page})=>{
 const data=fixture('flood',1),scene=data.items[0];
 const sar={provider_id:'copernicus',collection:'sentinel-1-grd',id:'S1_TEST_ONLY'};
 Object.assign(scene,{...sar,datetime:'2025-08-17T09:32:17Z',thumbnail:null,
  download_assets:[{key:'Product',title:'TEST ONLY SAR ZIP',href:'https://example.test/TEST_ONLY.zip',media_type:'application/zip',direct_url:null,requester_pays:false,authentication_required:true,access_verified:false,access_note:'TEST ONLY',common_names:[],roles:['data']}]});
 Object.assign(scene.purpose_plan!,{default_keys:['Product'],analysis_keys:['Product'],visual_keys:[]});
 data.items=[scene];data.returned=1;data.query.start_date='2025-08-01';data.query.end_date='2025-08-31';
 data.collection_statuses=[{...data.collection_statuses![0],collection:'sentinel-1-grd',returned:1,fetched:1}];
 await page.addInitScript(()=>{
  const saved:{chunks:number[][];closed:boolean;aborted:boolean}={chunks:[],closed:false,aborted:false};
  (window as Window & {__testSarSave?:typeof saved}).__testSarSave=saved;
  Object.defineProperty(window,'showSaveFilePicker',{value:async()=>({createWritable:async()=>({
   write:async(bytes:Uint8Array)=>{saved.chunks.push(Array.from(bytes));},
   close:async()=>{saved.closed=true;},abort:async()=>{saved.aborted=true;}
  })})});
 });
 await page.route('**/api/search',r=>r.fulfill({json:data}));
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY'}}));
 await page.route('**/api/auth/earthdata/status',r=>r.fulfill({json:{configured:false,connected:false}}));
 await page.route('**/api/auth/providers/status',r=>r.fulfill({json:{providers:[]}}));
 await page.route('**/api/media/inspect',r=>r.fulfill({json:{reference:sar,preview:null,assets:[{key:'Product',status:'available',message:'TEST ONLY 범위 확인',size_bytes:1177053605,access_verified:true,download_url:'/api/media/downloads/TEST_ONLY'}],notice:'TEST ONLY'}}));
 const zip=Buffer.from('PK\x03\x04TEST_ONLY_SAR_ZIP');
 await page.route('**/api/media/downloads/**',r=>r.fulfill({body:zip,headers:{'content-type':'application/octet-stream','content-length':String(zip.length),'content-disposition':'attachment; filename="TEST_ONLY.zip"'}}));
 await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-08-01');await page.getByLabel('종료일',{exact:true}).fill('2025-08-31');
 await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('flood');await page.getByRole('button',{name:'충남 예시 영역'}).click();await searchProduct(page,'s1_csar');
 const card=page.getByTestId('scene-card').first();await openBandPanel(card);
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await expect(card.getByRole('button',{name:'원본 다운로드',exact:true})).toBeEnabled();
 await card.getByRole('button',{name:'원본 다운로드',exact:true}).click();
 await expect(card).toContainText('파일 전체 수신·디스크 저장 완료');
 const saved=await page.evaluate(()=>(window as Window & {__testSarSave?:{chunks:number[][];closed:boolean;aborted:boolean}}).__testSarSave);
 expect(saved?.closed).toBe(true);expect(saved?.aborted).toBe(false);
 expect(Buffer.from(saved?.chunks.flat()||[])).toEqual(zip);
});

for(const succeeds of [true,false])
test(`TEST ONLY 만료 원본 receipt는 명시 다운로드 후 같은 Asset 갱신 1회 · ${succeeds?'성공':'반복 만료 중단'}`,async({page})=>{
 const originalInspections:unknown[]=[],transfers:string[]=[];
 await page.route('**/api/media/inspect',r=>{
  const body=r.request().postDataJSON();
  if(!body.include_preview)originalInspections.push(body);
  return r.fulfill({json:{reference,preview:body.include_preview?{status:'not_provided',message:'TEST ONLY browse 없음',access_verified:false}:null,
   assets:body.asset_keys.map((key:string)=>({key,status:'available',access_verified:true,message:'TEST ONLY 범위 접근만 확인',download_url:originalInspections.length>1?'/api/media/downloads/FRESH':'/api/media/downloads/EXPIRED'})),notice:'TEST ONLY'}});
 });
 await page.route('**/api/media/downloads/**',r=>{
  const path=new URL(r.request().url()).pathname;transfers.push(path);
  return path.endsWith('FRESH')&&succeeds?r.fulfill({body:Buffer.from('TEST_ONLY_FILE'),contentType:'application/octet-stream',headers:{'Content-Disposition':'attachment; filename="FRESH_TEST_ONLY.h5"'}})
   :r.fulfill({status:404,json:path.endsWith('EXPIRED')?{detail:{code:'MEDIA_RECEIPT_INVALID',message:'TEST ONLY 만료'}}:{error:{code:'MEDIA_RECEIPT_INVALID',message:'TEST ONLY 재만료'}}});
 });
 await setup(page);
 const card=page.getByTestId('primary-results').getByTestId('scene-card').first();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await expect(card.getByRole('button',{name:'원본 다운로드',exact:true})).toBeEnabled();
 expect(transfers).toHaveLength(0);expect(originalInspections).toHaveLength(1);
 if(succeeds){
  const download=page.waitForEvent('download');await card.getByRole('button',{name:'원본 다운로드',exact:true}).click();
  expect((await download).suggestedFilename()).toBe('FRESH_TEST_ONLY.h5');
  await expect(card).toContainText('파일 전체 수신 완료');
 }else{
  await card.getByRole('button',{name:'원본 다운로드',exact:true}).click();
  await expect(card).toContainText('접근 갱신은 1회만 시도했습니다.');
 }
 expect(originalInspections).toEqual(Array(2).fill({...reference,asset_keys:['granule-0'],include_preview:false}));
 expect(transfers).toEqual(['/api/media/downloads/EXPIRED','/api/media/downloads/FRESH']);
});

for(const change of ['auth','bands'] as const)
test(`TEST ONLY 원본 갱신 도중 ${change} 변경은 새 receipt 전송·저장을 취소`,async({page})=>{
 let count=0,freshTransfers=0,downloads=0,release!:()=>void,finished!:()=>void;
 const held=new Promise<void>(resolve=>release=resolve),completed=new Promise<void>(resolve=>finished=resolve);
 page.on('download',()=>downloads++);
 await page.route('**/api/media/inspect',async r=>{
  const body=r.request().postDataJSON();
  if(!body.include_preview)count++;
  const refreshing=!body.include_preview&&count===2;
  if(refreshing)await held;
  await r.fulfill({json:{reference,preview:body.include_preview?{status:'not_provided',message:'TEST ONLY',access_verified:false}:null,
   assets:body.asset_keys.map((key:string)=>({key,status:'available',access_verified:true,message:'TEST ONLY',download_url:refreshing?'/api/media/downloads/FRESH':'/api/media/downloads/EXPIRED'})),notice:'TEST ONLY'}}).catch(()=>{});
  if(refreshing)finished();
 });
 await page.route('**/api/media/downloads/**',r=>{
  if(r.request().url().endsWith('FRESH'))freshTransfers++;
  return r.fulfill({status:404,json:{detail:{code:'MEDIA_RECEIPT_INVALID',message:'TEST ONLY 만료'}}});
 });
 await setup(page);
 const card=page.getByTestId('primary-results').getByTestId('scene-card').first();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await card.getByRole('button',{name:'원본 다운로드',exact:true}).click();
 await expect.poll(()=>count).toBe(2);
 if(change==='auth')await page.evaluate(()=>window.dispatchEvent(new Event('earthdata-connection-change')));
 else await card.getByTestId('band-granule-0').uncheck();
 release();await completed;
 await expect(card.getByRole('button',{name:'원본 다운로드',exact:true})).toHaveCount(0);
 expect(freshTransfers).toBe(0);expect(downloads).toBe(0);
});

for(const mode of ['known-expiry','receipt-404','repeated-expiry'] as const)
test(`TEST ONLY browse 명시 저장은 만료 receipt를 1회 갱신 · ${mode}`,async({page})=>{
 await page.clock.install();
 let inspections=0;const transfers:string[]=[],bodies:unknown[]=[];
 const expires=Date.now()/1000+120;
 await page.route('**/api/media/inspect',r=>{
  const body=r.request().postDataJSON();bodies.push(body);inspections++;
  const ticket=inspections===1?'EXPIRED':'FRESH';
  return r.fulfill({json:{reference,preview:{status:'available',access_verified:true,message:'TEST ONLY browse',url:`/api/media/previews/${ticket}`,download_url:`/api/media/previews/${ticket}?download=1`,
   ...(mode==='known-expiry'?{receipt_expires_at:inspections===1?expires:expires+3600}:{})},assets:[],notice:'TEST ONLY'}});
 });
 await page.route('**/api/media/previews/**',r=>{
  const url=new URL(r.request().url());
  if(url.searchParams.has('download')){
   transfers.push(url.pathname);
   if(url.pathname.endsWith('EXPIRED')||mode==='repeated-expiry')return r.fulfill({status:404,json:{detail:{code:'MEDIA_RECEIPT_INVALID',message:'TEST ONLY 만료'}}});
  }
  return r.fulfill({body:image,contentType:'image/png',headers:{'Content-Disposition':'attachment; filename="TEST_ONLY_BROWSE.png"'}});
 });
 await setup(page);
 const preview=page.locator('.imagery-preview');await preview.scrollIntoViewIfNeeded();
 await expect(preview.locator('img')).toBeVisible();expect(inspections).toBe(1);expect(transfers).toHaveLength(0);
 if(mode==='known-expiry')await page.clock.fastForward(121000);
 if(mode==='repeated-expiry'){
  await preview.getByRole('button',{name:'미리보기 이미지 저장',exact:true}).click();
  await expect(preview).toContainText('접근 갱신은 1회만 시도했습니다.');
 }else{
  const download=page.waitForEvent('download');await preview.getByRole('button',{name:'미리보기 이미지 저장',exact:true}).click();
  expect((await download).suggestedFilename()).toBe('TEST_ONLY_BROWSE.png');
  await expect(preview).toContainText('미리보기 이미지 수신 완료');
 }
 expect(inspections).toBe(2);
 expect(bodies).toEqual(Array(2).fill({...reference,asset_keys:[],include_preview:true}));
 expect(transfers).toEqual(mode==='known-expiry'?['/api/media/previews/FRESH']:['/api/media/previews/EXPIRED','/api/media/previews/FRESH']);
});

for(const [status,message] of [['permission_required','권한·앱 승인·EULA 원인 미확인'],['unauthorized','파일 인증 실패'],['usgs_login_required','USGS 로그인 필요 · Earthdata로 대체 불가'],['size_limit','크기 상한 초과'],['reconnection_required','Earthdata 재연결 필요']])
test(`TEST ONLY ${status}는 미제공/다운로드 성공으로 표시하지 않음`,async({page})=>{
 await page.route('**/api/media/inspect',r=>r.fulfill({json:{reference,preview:{status,message,access_verified:false},assets:[{key:'granule-0',status,message,access_verified:false}],notice:'TEST ONLY'}}));
 await setup(page);await page.locator('.imagery-preview').scrollIntoViewIfNeeded();
 await expect(page.locator('.imagery-preview')).toContainText(message);
 const card=page.getByTestId('primary-results').getByTestId('scene-card').first();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await expect(card.getByRole('button',{name:'원본 다운로드',exact:true})).toBeDisabled();
 await expect(card.locator('.managed-asset-access')).toContainText(message);
});

test('TEST ONLY 늦은 미리보기 응답과 밴드 접근 확인은 새 선택에 붙지 않음',async({page})=>{
 let release!:()=>void;const held=new Promise<void>(r=>release=r);
 await page.route('**/api/media/inspect',async r=>{await held;await r.fulfill({json:{reference,preview:{status:'available',message:'OLD TEST ONLY',url:'/api/media/previews/OLD',access_verified:true},assets:[{key:'granule-0',status:'available',message:'OLD TEST ONLY',access_verified:true,download_url:'/api/media/downloads/OLD'}],notice:'TEST ONLY'}}).catch(()=>{});});
 await setup(page);
 await page.locator('.imagery-preview').scrollIntoViewIfNeeded();
 await expect(page.locator('.imagery-preview')).toContainText('미리보기 자동 수신');
 const card=page.getByTestId('primary-results').getByTestId('scene-card').first();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await card.getByTestId('band-granule-0').uncheck();
 await page.getByTestId('other-results').getByRole('button',{name:'지도에서 선택'}).first().click();
 release();
 await expect(page.getByTestId('selected-scene-detail')).not.toContainText('Suomi NPP TEST ONLY');
 await expect(page.locator('.imagery-preview img[src="/api/media/previews/OLD"]')).toHaveCount(0);
 await expect(card.getByRole('button',{name:'원본 다운로드',exact:true})).toHaveCount(0);
});

test('TEST ONLY 모바일 접근 상태와 밴드 선택 유지',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.route('**/api/media/inspect',r=>r.fulfill({json:{reference,preview:{status:'login_required',message:'NASA 계정 연결과 파일 권한은 별도 확인',access_verified:false},assets:[],notice:'TEST ONLY'}}));
 await setup(page);await page.locator('.imagery-preview').scrollIntoViewIfNeeded();
 await expect(page.locator('.imagery-preview')).toContainText('NASA 계정 연결과 파일 권한은 별도 확인');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await page.locator('.imagery-preview').screenshot({path:'test-results/media-mobile.png'});
});

test('LIVE 공개 Landsat 대응·NASA browse 전체 이미지 수신과 원본 미인증 구별',async({page},testInfo)=>{
 test.skip(process.env.LIVE_STAC!=='1','LIVE_STAC=1 명시 실행에서만 실제 제공처 접근');
 await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
 await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');
 for(const [label,value] of [['서쪽 경도','126.7'],['남쪽 위도','36.4'],['동쪽 경도','126.71'],['북쪽 위도','36.41']])await page.getByLabel(label,{exact:true}).fill(value);
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-20');await page.getByLabel('종료일',{exact:true}).fill('2025-07-26');
 let response=page.waitForResponse(r=>r.url().endsWith('/api/media/inspect'));
 await searchProduct(page,'landsat_tirs');await expect(page.getByTestId('scene-card')).toHaveCount(1);
 await page.locator('.imagery-preview').scrollIntoViewIfNeeded();
 const landsat=await (await response).json();expect(landsat.landsat.product_id).toBe('LC09_L2SP_116035_20250723_20250726_02_T1');
 expect(['available','usgs_login_required']).toContain(landsat.preview.status);
 await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 response=page.waitForResponse(r=>r.url().endsWith('/api/media/inspect'));
 await searchProduct(page,'viirs_sr');await page.locator('.imagery-preview').scrollIntoViewIfNeeded();
 const nasa=await (await response).json();expect(nasa.preview.status).toBe('available');
 await expect(page.locator('.imagery-preview img')).toBeVisible();
 await expect(page.locator('.imagery-preview img')).toHaveAttribute('src',/^\/api\/media\/previews\//);
 await page.locator('.imagery-preview').screenshot({path:'test-results/media-nasa-live.png'});
 await testInfo.attach('public-provider-status',{body:JSON.stringify({landsat:landsat.preview.status,nasa:nasa.preview.status,scope:'Public image only; authenticated original not executed'}),contentType:'application/json'});
});
