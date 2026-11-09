import {test,expect} from './runtime';
import {configs,input,interpretation,region,map,coordinates,jejuMeta,chooseLocation} from './ai-primary-fixtures';
test('TEST ONLY AI 목적과 수동 목적의 분류 출처를 구분',async({page})=>{
 await configs(page);
 await page.route('**/api/request/interpret',r=>r.fulfill({json:interpretation()}));
 await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));
 await page.goto('/');await input(page);
 const recommendation=page.locator('.recommendation');
 await expect(recommendation).toContainText('분류 근거: AI 해석으로 설정');
 await expect(recommendation).not.toContainText('사용자 직접 선택');
 await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 await expect(recommendation).toContainText('분류 근거: 사용자 직접 선택');
});
for(const status of ['provider_error','timeout','invalid_response','not_configured','limited'])test('TEST ONLY AI '+status+'는 규칙 값·이전 성공으로 대체하지 않음',async({page})=>{
 await configs(page);let geo=0;await page.route('**/api/request/interpret',r=>r.fulfill({json:{condition_proposals:{status:'failed',messages:['TEST ONLY '+status],period:{status:'absent'},region:{status:'absent'},engine:{mode:'ai',status,provider:'openai',model:'TEST_ONLY'}}}}));
 await page.route('**/api/places/search',r=>{geo++;return r.fulfill({json:region(true)});});await page.goto('/');await input(page);await expect(page.getByTestId('automatic-conditions')).toContainText('AI 해석 실패');
 await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('');await expect(page.getByLabel('목적 직접 선택',{exact:false})).toHaveValue('');await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');expect(geo).toBe(0);
 await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();await page.getByRole('button',{name:'직접 입력으로 계속',exact:true}).click();await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');await page.getByLabel('시작일',{exact:true}).fill('2025-08-15');await page.getByLabel('종료일',{exact:true}).fill('2025-08-30');await coordinates(page,[126.7,36.4,126.71,36.41]);await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeEnabled();
});

test('TEST ONLY 이전 AI 응답이 새 입력을 덮지 않음',async({page})=>{
 await configs(page);let release!:()=>void;const held=new Promise<void>(r=>release=r);let first=false;
 await page.route('**/api/request/interpret',async r=>{const old=r.request().postDataJSON().purpose.includes('서울');if(old){first=true;await held;}await r.fulfill({json:interpretation(old?'서울시':'제주도',old?'2024-01-01':'2025-08-15',old?'2024-01-31':'2025-08-30')}).catch(()=>{});});await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));
 await page.goto('/');await input(page,'2024년 1월 서울시 지표면 온도');await expect.poll(()=>first).toBe(true);await input(page);await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-15');release();await chooseLocation(page);await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-15');
});

test('TEST ONLY 상대 날짜·비교 기준 누락은 임의 확정하지 않음',async({page})=>{
 await configs(page);const data=interpretation();data.condition_proposals.period={status:'needs_confirmation',start:undefined,end:undefined,timezone:'UTC'} as never;data.condition_proposals.messages=['상대 날짜 기준과 비교 기준일을 확인하세요'];data.condition_proposals.event_reference_required=true;
 await page.route('**/api/request/interpret',r=>r.fulfill({json:data}));await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));await page.goto('/');await input(page,'최근 제주도 지표면 온도 전후');await expect(page.getByTestId('automatic-conditions')).toContainText('상대 날짜 기준');await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('');await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();
});

test('TEST ONLY 이전 규칙 응답 자체를 차단',async({page})=>{
 await configs(page);const data=interpretation();data.condition_proposals.engine!.mode='rules';await page.route('**/api/request/interpret',r=>r.fulfill({json:data}));await page.goto('/');await input(page);await expect(page.getByTestId('automatic-conditions')).toContainText('계약이 아닌 응답을 차단');await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('');
});

test('TEST ONLY AI 목적 미지정은 키워드로 채우지 않고 직접 목적 확인 전 검색 차단',async({page})=>{
 await configs(page);const data=interpretation();data.condition_proposals.fields!.purpose_type={value:null,evidence:null,basis:'unspecified'};data.condition_proposals.extraction!.purpose_type=null;
 await page.route('**/api/request/interpret',r=>r.fulfill({json:data}));await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));await page.goto('/');await input(page,'2025년 8월 제주도');await chooseLocation(page);await coordinates(page,[126.7,36.4,126.71,36.41]);await expect(page.getByLabel('분석 장소',{exact:true})).toHaveValue('제주특별자치도');await expect(page.getByLabel('목적 직접 선택',{exact:false})).toHaveValue('');await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeEnabled();
});
