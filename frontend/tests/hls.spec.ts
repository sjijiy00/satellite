// TEST ONLY NASA catalog/file transports. Never sends operator credentials.
import {test,expect,searchProduct,type Page} from './runtime';
import fixture from './hls-fixture.json';
const image=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==','base64');

async function setup(page:Page,family:'l30'|'s30',status='available'){
 const data=structuredClone(fixture);data.items=data.items.filter(s=>s.collection==='hls-'+family+'-002');data.returned=data.items.length;
 await page.route('**/api/search',r=>{expect(r.request().postDataJSON()).toMatchObject({purpose_type:'vegetation',collections:['hls-'+family+'-002'],bbox:[126.7,36.4,126.71,36.41],start_date:'2025-07-20',end_date:'2025-07-26'});return r.fulfill({json:data});});
 await page.route('**/api/auth/earthdata/status',r=>r.fulfill({json:{operator_mode:true,configured:true,connected:false,access_state:'not_initialized',message:'TEST ONLY 운영자 모드'}}));
 await page.route('**/api/auth/providers/status',r=>r.fulfill({json:{providers:[]}}));
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY_HLS',expires_at:Date.now()/1000+3600}}));
 await page.route('**/api/media/inspect',r=>{
  const body=r.request().postDataJSON();expect(body).toMatchObject({provider_id:'nasa-cmr',collection:'hls-'+family+'-002'});
  return r.fulfill({json:{reference:body,preview:body.include_preview?{status,access_verified:status==='available',message:status==='available'?'TEST ONLY 제공처 browse':'TEST ONLY 미리보기 Asset 없음',url:status==='available'?'/api/media/previews/TEST_ONLY_HLS':undefined}:null,
    assets:body.asset_keys.map((key:string)=>({key,status:'available',access_verified:true,size_bytes:256,message:'TEST ONLY 범위 접근 확인 · 전체 다운로드 미실행',download_url:'/api/media/downloads/TEST_ONLY_HLS'})),notice:'TEST ONLY'}});
 });
 await page.route('**/api/media/previews/**',r=>r.fulfill({body:image,contentType:'image/png'}));
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-20');await page.getByLabel('종료일',{exact:true}).fill('2025-07-26');
 for(const [i,l] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(l,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));
 await searchProduct(page,'hls_'+family);
 const card=page.getByTestId('other-results').getByTestId('scene-card').first();
 await card.locator('.asset-downloads > summary').click();
 return card;
}

for(const family of ['l30','s30'] as const)test('TEST ONLY HLS '+family+' 추천→검색→실제 밴드 선택→별도 browse/명시 원본 다운로드',async({page})=>{
 let transfers=0;
 await page.route('**/api/media/downloads/**',r=>{transfers++;return r.fulfill({body:Buffer.from('II*\x00TEST_ONLY_TRANSPORT'),contentType:'application/octet-stream',headers:{'Content-Disposition':'attachment; filename="TEST_ONLY_HLS.B04.tif"'}});});
 const card=await setup(page,family);
 await expect(card).toContainText(family==='l30'?'HLSL30':'HLSS30');
 await expect(card.getByTestId('band-B04')).toBeChecked();await expect(card.getByTestId('band-'+(family==='l30'?'B05':'B8A'))).toBeChecked();await expect(card.getByTestId('band-Fmask')).toBeChecked();
 if(family==='s30')await expect(card.getByTestId('band-B08')).not.toBeChecked();
 await page.locator('.imagery-preview').scrollIntoViewIfNeeded();await expect(page.locator('.imagery-preview img')).toHaveAttribute('src','/api/media/previews/TEST_ONLY_HLS');
 expect(transfers).toBe(0);
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await expect(card).toContainText('원본 전체 파일 크기 256 bytes');expect(transfers).toBe(0);
 const received=page.waitForEvent('download');await card.getByRole('button',{name:'원본 다운로드',exact:true}).first().click();expect((await received).suggestedFilename()).toBe('TEST_ONLY_HLS.B04.tif');
 await expect(card).toContainText('파일 전체 수신 완료');expect(transfers).toBe(1);
 await page.getByLabel('위성 선택',{exact:true}).selectOption('manual');
 await expect(page.getByLabel(family==='l30'?'NASA HLS L30 · Landsat · v2.0':'NASA HLS S30 · Sentinel-2 · v2.0',{exact:true})).toBeChecked();
});

test('TEST ONLY HLS 미리보기 없음과 다운로드 HTML 오류는 성공으로 표시하지 않음 · 모바일',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 await page.route('**/api/media/downloads/**',r=>r.fulfill({status:502,json:{error:{code:'login_page',message:'TEST ONLY 파일 대신 로그인 HTML'}}}));
 const card=await setup(page,'s30','missing_asset');
 await page.locator('.imagery-preview').scrollIntoViewIfNeeded();await expect(page.locator('.imagery-preview')).toContainText('미리보기 Asset 없음');
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();await card.getByRole('button',{name:'원본 다운로드',exact:true}).first().click();
 await expect(card).toContainText('TEST ONLY 파일 대신 로그인 HTML');await expect(card).not.toContainText('파일 전체 수신 완료');
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
});

test('TEST ONLY HLS 제공처 HTTP 400은 인증 성공·원본 저장으로 표시하지 않음',async({page})=>{
 const card=await setup(page,'l30','provider_error');let downloads=0;
 await page.route('**/api/media/inspect',r=>{
  const body=r.request().postDataJSON();
  const failure={status:'provider_error',http_status:400,access_verified:false,message:'TEST ONLY 제공처 HTTP 400 · 인증 원인 미확정'};
  return r.fulfill({json:{reference:body,preview:body.include_preview?failure:null,
   assets:body.asset_keys.map((key:string)=>({key,...failure})),notice:'TEST ONLY'}});
 });
 await page.route('**/api/media/downloads/**',r=>{downloads++;return r.abort();});
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await expect(card).toContainText('TEST ONLY 제공처 HTTP 400');
 await expect(card.getByRole('button',{name:'원본 다운로드',exact:true}).first()).toBeDisabled();
 await expect(card).not.toContainText('파일 전체 수신 완료');expect(downloads).toBe(0);
 await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-07-20');
 await expect(page.getByLabel('종료일',{exact:true})).toHaveValue('2025-07-26');
});
