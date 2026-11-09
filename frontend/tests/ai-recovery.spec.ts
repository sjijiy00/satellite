import {test,expect} from './runtime';
import {configs,input,interpretation,region,chooseLocation,coordinates} from './ai-primary-fixtures';
test.use({viewport:{width:390,height:844}});
test('TEST ONLY successful AI awaiting region/reference survives reload without another AI call',async({page},info)=>{
 await configs(page);let calls=0;const value=interpretation();value.condition_proposals.event_reference_required=true;value.condition_proposals.messages=['TEST ONLY 사건 기준일을 확인하세요'];
 await page.route('**/api/request/interpret',r=>{calls++;return r.fulfill({json:value});});await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));
 await page.goto('/');await input(page,'2026년 7월 충남의 집중호우 전후 침수 범위를 분석하고 싶어.');await expect(page.getByRole('button',{name:'제주특별자치도',exact:true})).toBeVisible();
 await page.reload();const panel=page.getByTestId('automatic-conditions');await expect(panel).not.toContainText('AI 해석 실패');await expect(panel).toContainText('TEST ONLY 사건 기준일');await expect(page.getByRole('button',{name:'제주특별자치도',exact:true})).toBeVisible();
 expect(calls).toBe(1);await chooseLocation(page);await coordinates(page,[126.7,36.4,126.71,36.41]);await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();
 await panel.screenshot({path:info.outputPath('restored-confirmation.png')});
});
test('TEST ONLY original quota error persists across reload with no automatic retry',async({page},info)=>{
 await configs(page);let calls=0;await page.route('**/api/request/interpret',r=>{calls++;return r.fulfill({json:{condition_proposals:{status:'failed',messages:['TEST ONLY OpenAI 크레딧·할당량 확인 필요'],period:{status:'absent'},region:{status:'absent'},engine:{mode:'ai',status:'quota_exceeded',provider:'openai',model:'TEST_ONLY'}}}});});
 await page.goto('/');await input(page);await expect(page.getByTestId('automatic-conditions')).toContainText('TEST ONLY OpenAI 크레딧·할당량');await page.reload();await expect(page.getByTestId('automatic-conditions')).toContainText('TEST ONLY OpenAI 크레딧·할당량');expect(calls).toBe(1);
 await expect(page.getByTestId('automatic-conditions')).not.toContainText('미확정인 문장을 복원');await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();
 await page.getByTestId('automatic-conditions').screenshot({path:info.outputPath('restored-quota-error.png')});
});

test('TEST ONLY confirmed AI input remains AI after reload; manual override stays explicit',async({page})=>{
 await configs(page);let calls=0;await page.route('**/api/request/interpret',r=>{calls++;return r.fulfill({json:interpretation()});});await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));
 await page.goto('/');await input(page);await chooseLocation(page);await coordinates(page,[126.7,36.4,126.71,36.41]);await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeEnabled();await page.reload();
 await expect(page.getByTestId('automatic-conditions')).toContainText('AI 해석 성공');await expect(page.getByTestId('automatic-conditions')).not.toContainText('직접 입력 모드');expect(calls).toBe(1);
 await page.getByLabel('시작일',{exact:true}).fill('2025-08-16');await page.getByRole('button',{name:'직접 입력으로 계속',exact:true}).click();await page.reload();await expect(page.getByTestId('automatic-conditions')).toContainText('직접 입력 모드');await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-16');expect(calls).toBe(1);
});

test('TEST ONLY location interruption preserves completed AI extraction without another AI call',async({page})=>{
 await configs(page);let calls=0,lookups=0,release!:()=>void;const held=new Promise<void>(r=>release=r);
 await page.route('**/api/request/interpret',r=>{calls++;return r.fulfill({json:interpretation()});});await page.route('**/api/places/search',async r=>{lookups++;if(lookups===1)await held;await r.fulfill({json:region(true)}).catch(()=>{});});
 await page.goto('/');await input(page);await expect.poll(()=>lookups).toBe(1);await page.reload();release();
 await expect(page.getByTestId('automatic-conditions')).toContainText('AI 재해석은 필요하지 않습니다');await expect(page.getByTestId('automatic-conditions')).not.toContainText('AI 해석 실패');await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-15');expect(calls).toBe(1);expect(lookups).toBe(1);
});

test('TEST ONLY legacy and mismatched saved AI state remain unknown without guessing or auto retry',async({page})=>{
 await configs(page);let calls=0;await page.route('**/api/request/interpret',r=>{calls++;return r.fulfill({json:interpretation()});});await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));
 await page.goto('/');await input(page);await expect(page.getByRole('button',{name:'제주특별자치도',exact:true})).toBeVisible();
 await page.evaluate(()=>{const key='satellite-workflow-v1',s=JSON.parse(sessionStorage.getItem(key)!);delete s.interpretation;s.inputConfirmed=false;sessionStorage.setItem(key,JSON.stringify(s));});await page.reload();
 await expect(page.getByTestId('automatic-conditions')).toContainText('실패 원인은 미확인');await expect(page.getByTestId('automatic-conditions')).not.toContainText('AI 해석 실패');expect(calls).toBe(1);
 await page.evaluate(()=>{const key='satellite-workflow-v1',s=JSON.parse(sessionStorage.getItem(key)!);s.interpretation={...s.interpretation,sentence:'TEST ONLY different sentence',phase:'ready',manual:true};s.inputConfirmed=true;sessionStorage.setItem(key,JSON.stringify(s));});await page.reload();await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();expect(calls).toBe(1);
 await page.getByTestId('sensor-landsat_tirs').getByRole('button',{name:'이 제품 선택',exact:true}).click();
 await expect(page.getByTestId('sensor-landsat_tirs').getByRole('button',{name:'선택한 제품',exact:true})).toHaveAttribute('aria-pressed','true');
 await expect(page.getByTestId('effective-search-selection')).toBeVisible();
 await expect(page.getByTestId('effective-search-selection')).toContainText('landsat-c2-l2');
 await expect(page.locator('#collection-next')).toContainText('위성 선택과는 별개');
 await page.getByRole('button',{name:'현재 조건으로 직접 입력 전환',exact:true}).click();
 await coordinates(page,[128.28865,36.07461,128.39985,36.16453]);
 await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeEnabled();
 await expect(page.getByTestId('sensor-landsat_tirs').getByRole('button',{name:'선택한 제품',exact:true})).toHaveAttribute('aria-pressed','true');expect(calls).toBe(1);
});
