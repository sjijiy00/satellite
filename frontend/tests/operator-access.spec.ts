import {test,expect,searchProduct,type Page} from './runtime';
import {fixture} from './fixtures';
import {readFile} from 'node:fs/promises';
import {Buffer} from 'node:buffer';

const ref={provider_id:'nasa-cmr',collection:'viirs-vnp09ga-002',id:'G_TEST_ONLY_OPERATOR-LPCLOUD'};
const hdf=Buffer.concat([Buffer.from([137,72,68,70,13,10,26,10]),Buffer.from('TEST ONLY ORIGINAL')]);
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==','base64');
async function setup(page:Page,state:string){
 await page.route('**/api/auth/earthdata/status',r=>r.fulfill({json:{configured:true,connected:false,operator_mode:true,storage:'server_encrypted'}}));
 await page.route('**/api/auth/providers/status',r=>r.fulfill({json:{providers:[{provider_id:'nasa-cmr',configured:true,connected:false,operator_mode:true,integration:'operator',access_state:state,message:'TEST ONLY 운영자 제공 상태'}]}}));
 await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
}

for(const state of ['active','not_ready','expired','revoked','permission_denied'])test(`TEST ONLY 운영자 ${state}는 방문자 로그인·관리자 설정 안내와 분리`,async({page})=>{
 await setup(page,state);await expect(page.getByText('NASA · 운영자 제공 자료 접근',{exact:true})).toBeVisible();
 await expect(page.getByRole('link',{name:'Earthdata 계정 연결',exact:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'계정 상태·갱신 확인',exact:true})).toHaveCount(0);
 const panel=page.locator('.earthdata-connection');await expect(panel).not.toContainText('OPERATOR_');
 await page.getByText('제공처별 연결 상태',{exact:true}).click();await expect(page.getByText(`운영자 제공 · ${state}`,{exact:true})).toBeVisible();
});

test('TEST ONLY 제공처 쿠키 없는 방문자 · 미리보기 자동·원본 명시 수신·파일 내용',async({page,context})=>{
 let originals=0;const data=fixture('vegetation',1),scene=data.items[0];
 Object.assign(scene,{...ref,thumbnail:'https://example.test/TEST_ONLY.png',preview_diagnostic:{status:'unchecked',has_candidate:true,message:'TEST ONLY'},download_assets:[{key:'granule',href:'s3://TEST_ONLY/ORIGINAL.h5',direct_url:null,title:'TEST ONLY VNP09GA',media_type:'application/x-hdf5',common_names:[],roles:['data'],requester_pays:false,authentication_required:true,access_verified:false,access_note:'TEST ONLY'}]});
 scene.purpose_plan!.default_keys=['granule'];scene.purpose_plan!.analysis_keys=['granule'];
 await page.route('**/api/search',r=>r.fulfill({json:data}));
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY'}}));
 await page.route('**/api/media/previews/**',r=>r.fulfill({body:png,contentType:'image/png'}));
 await page.route('**/api/media/downloads/**',r=>{originals++;return r.fulfill({body:hdf,headers:{'content-type':'application/octet-stream','content-disposition':'attachment; filename="TEST_ONLY.h5"','content-length':String(hdf.length)}});});
 await page.route('**/api/media/inspect',r=>r.fulfill({json:{reference:ref,preview:{status:'available',url:'/api/media/previews/TEST_ONLY',source_asset:'browse'},assets:r.request().postDataJSON().asset_keys.map((key:string)=>({key,status:'available',download_url:'/api/media/downloads/TEST_ONLY',message:'TEST ONLY 범위 확인 · 전체 미수신'}))}}));
 await setup(page,'active');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');await page.getByRole('button',{name:'충남 예시 영역',exact:true}).click();await searchProduct(page,'s2_msi');
 await page.locator('.imagery-preview').scrollIntoViewIfNeeded();await expect(page.locator('.imagery-preview img')).toBeVisible();expect(originals).toBe(0);
 expect((await context.cookies()).some(c=>/earthdata|edl/i.test(c.name))).toBe(false);
 // Download controls live in the selected result card's existing band panel.
 const card=page.getByTestId('scene-card').filter({hasText:ref.id}).first(),details=card.locator('details.asset-downloads');if(!await details.evaluate(el=>(el as HTMLDetailsElement).open))await details.locator('summary').first().click();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();expect(originals).toBe(0);
 const receipt=page.waitForEvent('download');await card.getByRole('button',{name:'원본 다운로드',exact:true}).click();
 const download=await receipt;await download.saveAs('test-results/operator-test-only.h5');expect(await readFile('test-results/operator-test-only.h5')).toEqual(hdf);expect(originals).toBe(1);
});

test('LIVE 제공처 로그인 없는 새 브라우저 · 공개 S2 원본 명시 다운로드·TIFF',async({page,context},testInfo)=>{
 test.skip(process.env.LIVE_STAC!=='1','별도 공개 실연결 검증에서만 실행');test.setTimeout(180000);
 let pendingInspects=0;
 page.on('request',r=>{if(r.url().endsWith('/api/media/inspect'))pendingInspects++;});
 page.on('response',r=>{if(r.url().endsWith('/api/media/inspect'))pendingInspects--;});
 page.on('requestfailed',r=>{if(r.url().endsWith('/api/media/inspect'))pendingInspects=Math.max(0,pendingInspects-1);});
 await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 for(const [label,value] of [['시작일','2025-07-20'],['종료일','2025-07-26'],['서쪽 경도','126.7'],['남쪽 위도','36.4'],['동쪽 경도','126.71'],['북쪽 위도','36.41']])await page.getByLabel(label,{exact:true}).fill(value);
 await searchProduct(page,'s2_msi');await expect(page.getByTestId('scene-card').first()).toBeVisible();
 const card=page.getByTestId('scene-card').first(),details=card.locator('details.asset-downloads');if(!await details.evaluate(el=>(el as HTMLDetailsElement).open))await details.locator('summary').first().click();
 await card.getByRole('button',{name:'선택 해제',exact:true}).click();await card.getByTestId('band-scl').check();
 await expect.poll(()=>pendingInspects,{timeout:90000}).toBe(0);
 const inspected=page.waitForResponse(r=>r.url().endsWith('/api/media/inspect')&&r.request().postDataJSON()?.asset_keys?.includes('scl'));
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 const report=await (await inspected).json();console.log(JSON.stringify({scope:'LIVE public S2 original access',error:report.error?.code,assets:report.assets?.map((a:{key:string;status:string;http_status?:number})=>({key:a.key,status:a.status,http_status:a.http_status}))}));
 const button=card.getByRole('button',{name:'원본 다운로드',exact:true});await expect(button).toBeEnabled({timeout:90000});
 expect((await context.cookies()).some(c=>/earthdata|edl/i.test(c.name))).toBe(false);
 const pending=page.waitForEvent('download');await button.click();const file=await pending;await file.saveAs('test-results/operator-public-s2.tif');
 const bytes=await readFile('test-results/operator-public-s2.tif');expect(['49492a00','4d4d002a','49492b00','4d4d002b']).toContain(bytes.subarray(0,4).toString('hex'));expect(bytes.length).toBeGreaterThan(1024);
 await testInfo.attach('public-original-evidence',{body:JSON.stringify({bytes:bytes.length,format:'TIFF',scope:'Public S2 SCL; operator private authentication NOT verified'}),contentType:'application/json'});
});
