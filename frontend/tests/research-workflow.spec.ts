import {test,expect} from './runtime';
import {configs,map,coordinates} from './ai-primary-fixtures';
import {mkdir} from 'node:fs/promises';
import path from 'node:path';

const suwon={id:'TEST_ONLY_SUWON',name:'경기 수원시',official_name:'경기 수원시',parent:'경기',admin_level:'시·군·구',center:[127.028715898311,37.2635846787741],role:'camera_only',source:'TEST ONLY Kakao',checked_at:'2026-11-04T02:00:00Z'};
async function direct(page:import('@playwright/test').Page){await page.getByText('위치 재시도·직접 지명·거리 지정',{exact:true}).click();await page.getByLabel('지명 직접 입력',{exact:true}).fill('수원');await page.getByRole('button',{name:'입력 지명 확인',exact:true}).click();}

for(const width of [390,768,1440])test(`TEST ONLY ${width}px Suwon selection moves camera, preserves manual AOI, no automatic science`,async({page})=>{
 await page.setViewportSize({width,height:844});await configs(page);let ai=0,queries:string[]=[];
 await page.route('**/api/request/interpret',r=>{ai++;return r.abort();});await page.route('**/api/places/search',r=>{const d=r.request().postDataJSON();expect(d.place).toBe('수원');expect(d).not.toHaveProperty('text');queries.push(d.place);return r.fulfill({json:{...suwon,status:'resolved',mentioned_text:'수원',candidates:[suwon]}});});
 await page.goto('/');await page.waitForFunction(()=>document.querySelector('[data-config-ready="true"]'));const bbox=[126.7,36.4,126.71,36.41];await coordinates(page,bbox);await direct(page);
 await page.getByRole('button',{name:'경기 수원시',exact:true}).click();await expect(map(page)).toHaveAttribute('data-camera-place','TEST_ONLY_SUWON');await expect(map(page)).toHaveAttribute('data-aoi-bbox',JSON.stringify(bbox));await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue(String(bbox[0]));
 await expect.poll(async()=>{const raw=await map(page).getAttribute('data-camera-center');const c=JSON.parse(raw||'null');return c?Math.abs(c[0]-suwon.center[0])<.001&&Math.abs(c[1]-suwon.center[1])<.001:false;}).toBe(true);
 await expect(page.getByRole('region',{name:'선택한 지도 위치'})).toContainText('기존 AOI를 유지');expect(ai).toBe(0);expect(queries).toEqual(['수원']);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await page.getByLabel('지명 직접 입력',{exact:true}).focus();await page.keyboard.press('Tab');await expect(page.getByRole('button',{name:'입력 지명 확인',exact:true})).toBeFocused();
 const root=process.env.E2E_EVIDENCE_DIR||'../test-results/research-workflow-ui';await mkdir(root,{recursive:true});await page.screenshot({path:path.join(root,`research-${width}.png`),fullPage:true});
});

for(const state of ['no_results','not_configured','authentication_failed','limited','timeout','invalid_response','failed'])test(`TEST ONLY place ${state} distinct from zero cloud, manual AOI remains available`,async({page})=>{
 await configs(page);await page.route('**/api/places/search',r=>r.fulfill({json:{status:state,mentioned_text:'수원',candidates:[],message:'TEST ONLY '+state}}));await page.goto('/');await page.waitForFunction(()=>document.querySelector('[data-config-ready="true"]'));await direct(page);await expect(page.getByTestId('automatic-conditions')).toContainText('TEST ONLY '+state);
 const b=[126.7,36.4,126.71,36.41];await coordinates(page,b);await expect(map(page)).toHaveAttribute('data-aoi-bbox',JSON.stringify(b));await expect(map(page)).toHaveAttribute('data-camera-place','');
});

test('TEST ONLY ambiguous district stays unselected; old location response cannot move latest view',async({page})=>{
 await configs(page);let release!:()=>void;const gate=new Promise<void>(r=>release=r);let began=false;
 await page.route('**/api/places/search',async r=>{began=true;await gate;await r.fulfill({json:{status:'ambiguous',mentioned_text:'수원',candidates:[suwon,{...suwon,id:'TEST_ONLY_OTHER',name:'TEST ONLY 다른 수원',parent:'TEST ONLY 상위'}]}}).catch(()=>{});});await page.goto('/');await page.waitForFunction(()=>document.querySelector('[data-config-ready="true"]'));await direct(page);await expect.poll(()=>began).toBe(true);await page.getByLabel('지명 직접 입력',{exact:true}).fill('서울 강서구');release();await expect(map(page)).toHaveAttribute('data-camera-place','');await expect(page.getByRole('button',{name:'경기 수원시',exact:true})).toHaveCount(0);
});

test('TEST ONLY archive distinguishes retained and expired result without replay',async({page})=>{
 await configs(page);let requests=0;await page.route('**/api/processing/jobs',r=>{expect(r.request().method()).toBe('GET');requests++;return r.fulfill({json:{jobs:[{job_id:'a'.repeat(32),status:'succeeded',created_at:'TEST_ONLY',input:{analysis_id:'vegetation_index'},artifact:{filename:'TEST_ONLY_result.zip',bytes:100},retention:{state:'expired',expires_at:'2025-01-01T00:00:00Z'}}]}});});
 await page.goto('/');await page.getByText('내 결과 보관함 · 재시작 후 찾기',{exact:true}).click();await page.getByRole('button',{name:'보관 결과 조회',exact:true}).click();await expect(page.locator('.result-archive')).toContainText('expired');await expect(page.getByRole('link',{name:'이전 결과 ZIP 저장',exact:true})).toHaveCount(0);expect(requests).toBe(1);
});
