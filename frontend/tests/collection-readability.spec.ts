// TEST ONLY viewport/keyboard/input fixtures; no paid AI or provider file requests.
import {mkdir} from 'node:fs/promises';
import {test,expect,type Page} from './runtime';
import type {Locator} from '@playwright/test';
import {configs,input,interpretation,region,coordinates,map,jejuMeta,chooseLocation} from './ai-primary-fixtures';
import {fixture} from './fixtures';

async function tabTo(page:Page,target:Locator,max=45){
 for(let n=0;n<max;n++){
  if(await target.evaluate(e=>e===document.activeElement))return;
  await page.keyboard.press('Tab');
 }
 await expect(target).toBeFocused();
}
async function noOverflow(page:Page){expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);}
async function readable(target:Locator,min=14){
 const style=await target.evaluate(e=>({size:parseFloat(getComputedStyle(e).fontSize),color:getComputedStyle(e).color,bg:(()=>{let p:Element|null=e;while(p){const b=getComputedStyle(p).backgroundColor;if(/^rgb\(/.test(b))return b;p=p.parentElement;}return 'rgb(255, 255, 255)';})()}));
 expect(style.size).toBeGreaterThanOrEqual(min);
 const luminance=(rgb:string)=>rgb.match(/[\d.]+/g)!.slice(0,3).map(Number).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((v,n,i)=>v+n*[.2126,.7152,.0722][i],0);
 const a=luminance(style.color),b=luminance(style.bg);expect((Math.max(a,b)+.05)/(Math.min(a,b)+.05)).toBeGreaterThanOrEqual(4.5);
}

for(const [width,height] of [[1440,1000],[834,1112],[390,844]])test(`TEST ONLY ${width}px 핵심 입력·키보드·단일 검색 도달성·글자 대비`,async({page})=>{
 await page.setViewportSize({width,height});await configs(page);let searches=0;let sent:any;
 await page.route('**/api/search',r=>{searches++;sent=r.request().postDataJSON();const data=fixture('vegetation',0);data.query={bbox:sent.bbox,start_date:sent.start_date,end_date:sent.end_date};return r.fulfill({json:data});});
 await page.goto('/');const form=page.getByRole('form',{name:'영상 검색 조건'}),purpose=page.getByLabel('분석 목적',{exact:true}),search=page.getByRole('button',{name:'위성영상 검색',exact:false});
 await expect(form).toBeVisible();await expect(purpose).toBeEnabled();await expect(search).toHaveCount(1);expect((await purpose.boundingBox())!.y).toBeLessThan(height);
 const shortcuts=page.getByRole('navigation',{name:'조건 입력 바로가기'});
 await shortcuts.getByRole('link',{name:'목적',exact:true}).focus();await page.keyboard.press('Enter');await expect(purpose).toBeFocused();
 expect((await purpose.boundingBox())!.y).toBeLessThan(height);await readable(purpose,16);
 const kind=page.getByLabel('목적 직접 선택',{exact:false});await tabTo(page,kind);await kind.selectOption('vegetation');
 const start=page.getByLabel('시작일',{exact:true}),end=page.getByLabel('종료일',{exact:true});await tabTo(page,start);await start.fill('2025-07-01');await tabTo(page,end);await end.fill('2025-07-31');
 for(const [i,l] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries()){
  const field=page.getByLabel(l,{exact:true});await tabTo(page,field);await field.fill(String([126.7,36.4,126.71,36.41][i]));await readable(field,16);
 }
 await tabTo(page,page.getByRole('button',{name:'좌표 적용',exact:true}));await page.keyboard.press('Enter');await expect(map(page)).toHaveAttribute('data-aoi-confirmed','true');
 await tabTo(page,search);await expect(search).toBeFocused();await expect(search).toBeInViewport();await readable(search,16);
 const focus=await search.evaluate(e=>({width:parseFloat(getComputedStyle(e).outlineWidth),style:getComputedStyle(e).outlineStyle}));expect(focus.width).toBeGreaterThanOrEqual(3);expect(focus.style).toBe('solid');
 const bounds=await search.boundingBox(),mapBox=await map(page).boundingBox();if(width<=1000)expect(bounds!.y+bounds!.height).toBeLessThan(mapBox!.y);else expect(mapBox!.x).toBeGreaterThan(bounds!.x+bounds!.width);
 await noOverflow(page);const formBox=await form.boundingBox();for(const field of [start,end,...['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].map(l=>page.getByLabel(l,{exact:true}))]){const box=await field.boundingBox();expect(box!.x).toBeGreaterThanOrEqual(formBox!.x);expect(box!.x+box!.width).toBeLessThanOrEqual(formBox!.x+formBox!.width-8);}expect(searches).toBe(0);
 await mkdir('../test-results/collection-readability',{recursive:true});await form.screenshot({path:`../test-results/collection-readability/inputs-${width}.png`});
 await page.keyboard.press('Enter');await expect.poll(()=>searches).toBe(1);expect(sent).toMatchObject({purpose_type:'vegetation',bbox:[126.7,36.4,126.71,36.41],start_date:'2025-07-01',end_date:'2025-07-31'});
});

test('TEST ONLY 모바일 AI 성공 요약·기술 상세 접기·키보드 펼침·수정 보호',async({page})=>{
 await page.setViewportSize({width:390,height:844});await configs(page);
 await page.route('**/api/request/interpret',r=>r.fulfill({json:interpretation()}));await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));
 await page.goto('/');await input(page);await chooseLocation(page);await coordinates(page,jejuMeta.bbox);const ai=page.getByTestId('automatic-conditions');await expect(ai.locator('.condition-status')).toContainText('AI 해석 성공');
 await expect(ai.getByText('문장이 OpenAI로 자동 전송되며 사용량·비용이 발생할 수 있습니다.',{exact:true})).toBeVisible();
 await expect(ai.getByTestId('ai-usage')).not.toBeVisible();await expect(ai.getByText(/TEST_ONLY_MODEL/)).not.toBeVisible();
 const summary=ai.getByText('AI 해석 상세·출처·사용량',{exact:true});await summary.focus();await page.keyboard.press('Enter');await expect(ai.getByTestId('ai-usage')).toBeVisible();
 await readable(ai.locator('.condition-status strong'),16);await readable(ai.locator('.ai-cost-notice'),14);
 const evidence=ai.getByText('AI 값·원문 근거·명시/추론',{exact:true});await evidence.focus();await page.keyboard.press('Enter');await expect(ai.getByText('근거:').first()).toBeVisible();
 await summary.focus();await page.keyboard.press('Enter');await page.getByLabel('시작일',{exact:true}).fill('2025-08-16');await expect(ai).toContainText('확인 필요');await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();
 await page.getByRole('button',{name:'직접 수정값 유지',exact:true}).focus();await page.keyboard.press('Enter');await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-16');await expect(map(page)).toHaveAttribute('data-aoi-bbox',JSON.stringify(jejuMeta.bbox));await noOverflow(page);
});

test('TEST ONLY 모바일 AI 실패·직접 입력·좌표 오류가 읽히고 검색은 차단',async({page})=>{
 await page.setViewportSize({width:390,height:844});await configs(page);let searches=0;await page.route('**/api/search',r=>{searches++;return r.abort();});
 await page.route('**/api/request/interpret',r=>r.fulfill({json:{condition_proposals:{status:'failed',messages:['TEST ONLY 응답 시간 초과'],period:{status:'absent'},region:{status:'absent'},engine:{mode:'ai',status:'timeout',provider:'openai',model:'TEST_ONLY_MODEL'}}}}));
 await page.goto('/');await input(page);const ai=page.getByTestId('automatic-conditions');await expect(ai.locator('.condition-status')).toContainText('AI 해석 실패');await expect(ai.locator('.condition-status')).toContainText('직접 입력');
 await expect(ai.getByRole('alert')).toContainText('응답 시간 초과');await readable(ai.getByRole('alert'),14);
 await page.getByRole('button',{name:'직접 입력으로 계속',exact:true}).focus();await page.keyboard.press('Enter');
 await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
 await coordinates(page,[127,36.4,126.71,36.41]);const error=page.locator('#collection-input-error');await expect(error).toContainText('서 < 동');await readable(error,14);
 await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();expect(searches).toBe(0);await expect(page.getByRole('form',{name:'영상 검색 조건'})).toHaveAttribute('aria-describedby','collection-input-error');
 await page.getByRole('navigation',{name:'조건 입력 바로가기'}).getByRole('link',{name:'검색으로 이동',exact:true}).focus();await page.keyboard.press('Enter');await expect(page.locator('#collection-search')).toBeInViewport();await noOverflow(page);
 await mkdir('../test-results/collection-readability',{recursive:true});await page.screenshot({path:'../test-results/collection-readability/error-390.png'});
});

test('TEST ONLY 바로가기는 지도 선택으로 이동하며 AOI를 자동 확정하지 않음',async({page})=>{
 await page.setViewportSize({width:390,height:844});await configs(page);await page.goto('/');await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');
 const jump=page.getByRole('link',{name:'지도에서 AOI 지정하기 ↓',exact:true});await jump.focus();await page.keyboard.press('Enter');
 const draw=page.getByRole('button',{name:'▧ 영역 선택',exact:true});await expect(draw).toBeEnabled();await tabTo(page,draw);await page.keyboard.press('Enter');await expect(page.getByRole('button',{name:'선택 취소',exact:true})).toBeFocused();
 await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');await expect(map(page)).toHaveAttribute('data-aoi-confirmed','false');await page.keyboard.press('Enter');await expect(draw).toBeEnabled();await noOverflow(page);
});
