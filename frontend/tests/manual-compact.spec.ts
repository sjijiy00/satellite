import {test,expect} from './runtime';
import {configs,coordinates,interpretation,input,region} from './ai-primary-fixtures';
for(const width of [390,1440])test(`TEST ONLY ${width}px manual input stays compact, usable and free of AI calls`,async({page},info)=>{
 await page.setViewportSize({width,height:844});await configs(page);let calls=0;
 await page.route('**/api/request/interpret',r=>{if(r.request().postDataJSON().resolve_conditions)calls++;return r.fulfill({json:interpretation()});});
 await page.goto('/');await page.getByRole('button',{name:'직접 입력으로 계속',exact:true}).click();
 const panel=page.getByTestId('automatic-conditions');await expect(panel).toContainText('AI 호출 없이 검색');expect((await panel.innerText()).length).toBeLessThan(100);
 await expect(page.getByLabel('분석 목적',{exact:true})).toBeHidden();await expect(page.getByRole('region',{name:'요청의 큰 분석 분야'})).toBeHidden();
 await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');await page.getByLabel('시작일',{exact:true}).fill('2026-07-01');await page.getByLabel('종료일',{exact:true}).fill('2026-07-31');await coordinates(page,[128.28865,36.07461,128.39985,36.16453]);
 await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeEnabled();await page.reload();await expect(panel).toContainText('직접 입력 모드');await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2026-07-01');expect(calls).toBe(0);
 await panel.screenshot({path:info.outputPath('manual-mode.png')});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.getByRole('button',{name:'자연어 입력으로 전환',exact:true}).click();await expect(page.getByLabel('분석 목적',{exact:true})).toBeVisible();expect(calls).toBe(0);
});
test('TEST ONLY browser waits for the configured 45 second server deadline rather than old 15 seconds',async({page})=>{
 await configs(page);await page.route('**/api/request/config',r=>r.fulfill({json:{ready:true,provider:'openai',model:'TEST_ONLY',message:'TEST ONLY',usage:{requests:0},limits:{timeout_seconds:45,requests_per_minute:6,requests_per_process:100,max_output_tokens:4000}}}));
 let started=false,release!:()=>void;const held=new Promise<void>(r=>release=r);
 await page.route('**/api/request/interpret',async r=>{if(!r.request().postDataJSON().resolve_conditions)return r.fulfill({json:interpretation()});started=true;await held;await r.fulfill({json:interpretation()});});await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));
 await page.goto('/');await input(page);await expect.poll(()=>started).toBe(true);await page.waitForTimeout(17000);await expect(page.getByTestId('automatic-conditions')).not.toContainText('시간 상한');release();await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-15');
});
