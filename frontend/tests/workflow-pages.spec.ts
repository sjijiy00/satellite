// TEST ONLY full client workflow. Provider/processing bytes below are fixtures.
import {test,expect,searchProduct,openBandPanel,confirmDetail,type Page} from './runtime';
import {fixture} from './fixtures';
const bytes=Buffer.concat([Buffer.from([73,73,42,0]),Buffer.from('TEST_ONLY_ORIGINAL_FILE')]);
async function setup(page:Page){
 const data=fixture('vegetation',2);data.items=data.items.filter(s=>s.collection==='sentinel-2-l2a').map(s=>({...s,provider_id:'earth-search'}));data.returned=2;
 data.query.bbox=[126.7,36.4,126.71,36.41];
 await page.route('**/api/search',r=>r.fulfill({json:data}));
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY_WORKFLOW',expires_at:Date.now()/1000+3600}}));
 await page.route('**/api/media/inspect',r=>{
  const body=r.request().postDataJSON();return r.fulfill({json:{reference:body,preview:null,
   assets:body.asset_keys.map((key:string)=>({key,status:'available',access_verified:true,message:'TEST ONLY 범위 확인 · 전체 수신 전',size_bytes:bytes.length,download_url:'/api/media/downloads/TEST_ONLY_'+key})),notice:'TEST ONLY'}});
 });
 await page.route('**/api/media/downloads/**',r=>r.fulfill({body:bytes,contentType:'application/octet-stream',headers:{'Content-Disposition':'attachment; filename="TEST_ONLY_original.tif"'}}));
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
 await page.getByText('관측 조건 선택 (선택 입력)',{exact:true}).click();await page.getByLabel('관측 시점',{exact:true}).selectOption('single');
 for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String(data.query.bbox[i]));
 await searchProduct(page,'s2_msi');await expect(page.getByTestId('scene-card')).toHaveCount(2);
 return data;
}
async function acquire(page:Page,index:number,green=false){
 const card=page.getByTestId('scene-card').nth(index);const details=card.locator('.asset-downloads');
 if(!await details.evaluate(e=>(e as HTMLDetailsElement).open))await details.locator(':scope > summary').click();
 if(green)await card.getByTestId('band-green').check();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 const buttons=card.getByRole('button',{name:'원본 다운로드',exact:true});await expect(buttons.first()).toBeEnabled();
 const count=await buttons.count();for(let i=0;i<count;i++){
  const download=page.waitForEvent('download');await buttons.nth(i).click();const file=await download;
  expect(await file.failure()).toBeNull();
 }
 await expect(card.getByText('파일 전체 수신 완료',{exact:false})).toHaveCount(count);
}
async function enter(page:Page){await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();await expect(page).toHaveURL(/\/processing$/);await confirmDetail(page);}

test('TEST ONLY 수집에서 원본만 다운로드 · 링크 목록과 실제 전체 수신 구분',async({page})=>{
 let processing=0;await page.route('**/api/cloud/plan',r=>{processing++;return r.abort();});
 await setup(page);
 await expect(page.getByTestId('next-work')).not.toBeVisible();
 const card=page.getByTestId('scene-card').first();if(!await card.locator('.asset-downloads').evaluate(e=>(e as HTMLDetailsElement).open))await card.locator('.asset-downloads > summary').click();
 const pending=page.waitForEvent('download');await card.getByRole('button',{name:'선택 링크 목록 저장 (.txt)'}).click();
 expect((await pending).suggestedFilename()).toMatch(/links\.txt$/);
 await expect(page.getByRole('region',{name:'현재 작업 요약',exact:true})).toContainText('링크 목록 저장 기록 있음');
 await expect(page.getByRole('region',{name:'현재 작업 요약',exact:true})).toContainText('원본 전체 수신 0/3개');
 await acquire(page,0);await expect(page.getByRole('region',{name:'현재 작업 요약',exact:true})).toContainText('원본 전체 수신 3/3개');
 expect(processing).toBe(0);await expect(page).toHaveURL(/\/$/);
});

test('TEST ONLY 브라우저 미확보 상태 전달, 서버 검사 분리·뒤로 가기·새로고침·중복 실행 없음',async({page})=>{
 let searches=0,analyses=0;page.on('request',r=>{if(r.url().endsWith('/api/search'))searches++;if(/\/api\/(cloud\/jobs$|change-analysis$)/.test(r.url()))analyses++;});
 await setup(page);await enter(page);
 const summary=page.getByRole('region',{name:'현재 작업 요약',exact:true});await expect(summary).toContainText('126.7, 36.4, 126.71, 36.41');
 await expect(summary).toContainText('브라우저 원본 미확보');
 await page.getByRole('button',{name:'두 장면 비교·분석',exact:true}).click();await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
 await expect(page.getByRole('button',{name:'작은 AOI 픽셀 진단',exact:true})).toBeEnabled();
 await page.goBack();await expect(page).toHaveURL(/\/$/);await page.goForward();await expect(page).toHaveURL(/\/processing$/);
 await page.reload();await expect(page.getByRole('region',{name:'현재 작업 요약',exact:true})).toContainText('TEST_ONLY_0');
 await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();
 await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-07-01');
 await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue('126.7');
 await expect(page.getByTestId('scene-card').first().getByTestId('band-red')).toBeChecked();
 expect(searches).toBe(1);expect(analyses).toBe(0);
});

test('TEST ONLY 원본 확보 → QA → 선택 전처리 미구현 안내 → NDVI 산출물 저장·조건 변경 무효화',async({page})=>{
 await setup(page);await acquire(page,0,true);await acquire(page,1,true);
 await page.route('**/api/pixel-quality',r=>r.fulfill({json:{status:'checked',common_valid_area_m2:100,common_valid_percent_aoi:80,common_valid_percent_observed:90,scenes:[],conclusion:'TEST ONLY QA'}}));
 await page.route('**/api/change-analysis',r=>r.fulfill({json:{status:'computed',analysis_completed:true,common_valid_area_m2:100,common_valid_percent_aoi:80,common_valid_percent_observed:90,scenes:[],artifact_base64:Buffer.from('PK TEST ONLY RESULT').toString('base64'),artifact_name:'TEST_ONLY_analysis.zip'}}));
 await enter(page);await page.getByRole('button',{name:'두 장면 비교·분석',exact:true}).click();
 await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');await confirmDetail(page,'vegetation_change');
 await page.getByRole('button',{name:'작은 AOI 픽셀 진단',exact:true}).click();await expect(page.getByTestId('pixel-aoi-percent')).toHaveText('80%');
 await page.getByRole('button',{name:'③ 전처리',exact:true}).click();await expect(page.getByText('독립 AOI 자르기',{exact:false})).toBeVisible();
 await page.getByRole('button',{name:'분석으로 계속하기',exact:true}).click();
 await page.getByRole('button',{name:'두 날짜 NDVI 계산',exact:true}).click();await expect(page.getByTestId('change-report')).toContainText('NDVI 계산 완료');
 const pending=page.waitForEvent('download');await page.getByRole('button',{name:'GeoTIFF 2개 + 처리기록 ZIP 저장',exact:true}).click();
 expect((await pending).suggestedFilename()).toBe('TEST_ONLY_analysis.zip');
 await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();
 await page.getByLabel('종료일',{exact:true}).fill('2025-07-30');await expect(page.getByTestId('stale-results')).toBeVisible();
 await page.getByRole('navigation',{name:'작업 페이지'}).getByRole('link',{name:'02 전처리·분석',exact:true}).click();
 await expect(page.getByTestId('processing-empty')).toBeVisible();await expect(page.getByTestId('change-report')).toHaveCount(0);
});

test('TEST ONLY 직접 처리 진입·모바일·서명/비밀 URL 브라우저 보관 금지',async({page})=>{
 await page.setViewportSize({width:390,height:844});await page.goto('/processing');await expect(page.getByTestId('processing-empty')).toBeVisible();
 await setup(page);await enter(page);await expect(page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true})).toBeVisible();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 const stored=await page.evaluate(()=>sessionStorage.getItem('satellite-workflow-v1')||'');
 expect(stored).not.toMatch(/confirmation_digest|artifact_base64|download_url|png_base64|X-Amz-Signature|Authorization/);
});

test('TEST ONLY 미확정 문장 새로고침은 이전 날짜·AOI로 조용히 검색하지 않음',async({page})=>{
 await setup(page);await page.getByRole('button',{name:'자연어 입력으로 전환',exact:true}).click();await page.getByLabel('분석 목적',{exact:true}).fill('조건 확인이 필요한 새 문장 TEST ONLY');
 await page.waitForFunction(()=>JSON.parse(sessionStorage.getItem('satellite-workflow-v1')||'null')?.inputConfirmed===false);
 await page.reload();await expect(page.getByTestId('automatic-conditions')).toContainText('해석 결과 확인 필요');
 await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();
});

test('TEST ONLY 관측 합성 전처리 ZIP만 다운로드·페이지 이동·새로고침에서 재실행 금지',async({page})=>{
 let starts=0,plans=0;const id='c'.repeat(32);
 const result={status:'succeeded',original_valid_area_m2:50,composite_valid_area_m2:90,aoi_area_m2:100,remaining_gap_area_m2:0};
 await page.route('**/api/cloud/plan',r=>{plans++;return r.fulfill({json:{...result,status:'planned',can_execute:true,plan_id:'a'.repeat(32),confirmation_digest:'b'.repeat(64)}});});
 await page.route('**/api/cloud/jobs',r=>{starts++;return r.fulfill({status:202,json:{job_id:id,plan_id:'a'.repeat(32),status:'queued',stage:'TEST ONLY',result:null,error:null}});});
 await page.route('**/api/cloud/jobs/**',r=>new URL(r.request().url()).pathname.endsWith('/download')?
  r.fulfill({body:Buffer.from('PK TEST ONLY PREPROCESSING'),contentType:'application/zip',headers:{'Content-Disposition':'attachment; filename="TEST_ONLY_preprocessing.zip"'}}):
  r.fulfill({json:{job_id:id,plan_id:'a'.repeat(32),status:'succeeded',stage:'TEST ONLY',result,error:null}}));
 await setup(page);await acquire(page,0,true);await acquire(page,1,true);await enter(page);
 await page.getByRole('button',{name:'③ 전처리',exact:true}).click();
 await page.getByLabel('현재 기간의 대체 후보와 날짜를 확인했습니다',{exact:true}).check();
 await page.getByRole('button',{name:'현재 기간 후보 검사·합성 계획',exact:true}).click();
 await page.getByLabel('위 AOI·기간·목적·장면·마스크 정책과 기간 요약 합성을 확인했습니다',{exact:true}).check();
 await page.getByRole('button',{name:'확인한 계획으로 실제 합성 실행',exact:true}).click();
 const link=page.getByRole('link',{name:'전처리 결과 다운로드 · 실제 GeoTIFF·마스크·출처/날짜·manifest ZIP 저장',exact:true});
 await expect(link).toBeVisible();const receiving=page.waitForEvent('download');await link.click();expect((await receiving).suggestedFilename()).toBe('sentinel-2-observed-composite.zip');
 await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();await enter(page);
 expect(starts).toBe(1);expect(plans).toBe(1);
 await page.reload();await expect(page.getByRole('region',{name:'복원한 작업 상태'})).toContainText('succeeded');
 await expect(page.getByRole('region',{name:'복원한 작업 상태'}).getByRole('link',{name:'전처리 결과 ZIP 다운로드',exact:true})).toBeVisible();
 expect(starts).toBe(1);expect(plans).toBe(1);
});

test('TEST ONLY 인증 원본 수신 실패는 확보 완료로 전달하지 않음',async({page})=>{
 await setup(page);await page.route('**/api/media/downloads/**',r=>r.fulfill({status:401,json:{error:{code:'unauthorized',message:'TEST ONLY 인증 원본 수신 실패'}}}));
 const card=page.getByTestId('scene-card').first();await openBandPanel(card);await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();
 await card.getByRole('button',{name:'원본 다운로드',exact:true}).first().click();await expect(card).toContainText('TEST ONLY 인증 원본 수신 실패');
 await enter(page);await expect(page.getByRole('region',{name:'현재 작업 요약',exact:true})).toContainText('원본 확보 실패');
 await expect(page.getByRole('button',{name:'선택 영상 실제 AOI 품질 검사',exact:true})).toBeDisabled();
});
