import {test,expect,searchProduct,type Page} from './runtime';
import {fixture} from './fixtures';
import {Buffer} from 'node:buffer';

// TEST ONLY: synthetic API responses and image bytes; no provider login or live network.
const png=Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScLbtAAAAABJRU5ErkJggg==','base64');
const ref={provider_id:'nasa-cmr',collection:'viirs-vnp09ga-002',id:'G_TEST_ONLY-LPCLOUD'};
function data(){
 const d=fixture('vegetation',1),s=d.items[0];
 Object.assign(s,{...ref,thumbnail:'https://example.test/TEST_ONLY.jpg',preview_diagnostic:{status:'unchecked',has_candidate:true,message:'TEST ONLY'}});
 return d;
}
function report(url='/api/media/previews/TEST_ONLY'){
 return {reference:ref,preview:{status:'available',message:'TEST ONLY',access_verified:true,url,source_asset:'browse'},assets:[],notice:'TEST ONLY'};
}
async function setup(page:Page, missingReceipt=false){
 await page.route('**/api/search',r=>r.fulfill({json:data()}));
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY',expires_at:4102444800}}));
 await page.route('**/api/media/previews/**',r=>missingReceipt?r.fulfill({status:404,body:'TEST ONLY'}):r.fulfill({body:png,contentType:'image/png'}));
 await page.route('https://example.test/**',r=>r.abort());
 await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
 await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 await page.getByRole('button',{name:'충남 예시 영역'}).click();
 await searchProduct(page,'s2_msi');
}

test('TEST ONLY visible preview loads automatically with no original requests and deduplicates the scene',async({page})=>{
 const bodies:unknown[]=[];let downloads=0;
 await page.route('**/api/media/downloads/**',r=>{downloads++;return r.abort();});
 await page.route('**/api/media/inspect',r=>{bodies.push(r.request().postDataJSON());return r.fulfill({json:report()});});
 await setup(page);
 const preview=page.locator('.imagery-preview');
 await preview.scrollIntoViewIfNeeded();
 await expect(preview.locator('img')).toBeVisible();
 await expect.poll(()=>bodies.length).toBe(1);
 expect(bodies).toEqual([{...ref,asset_keys:[],include_preview:true}]);
 expect(downloads).toBe(0);
});

test('TEST ONLY offscreen previews wait for intersection',async({page})=>{
 let count=0;
 await page.addInitScript(()=>{
  class NeverVisible {observe(){} unobserve(){} disconnect(){} takeRecords(){return [];} root=null;rootMargin='0px';thresholds=[0];}
  Object.defineProperty(window,'IntersectionObserver',{value:NeverVisible});
 });
 await page.route('**/api/media/inspect',r=>{count++;return r.fulfill({json:report()});});
 await setup(page);
 await expect(page.locator('.imagery-preview img')).toHaveCount(0);
 await page.waitForTimeout(500);
 expect(count).toBe(0);
});

test('TEST ONLY failed inspect stops and a user retry can display the image',async({page})=>{
 let count=0;
 await page.route('**/api/media/inspect',r=>{count++;return count===1?r.fulfill({status:503,json:{error:{code:'TEST_ONLY',message:'TEST ONLY 실패'}}}):r.fulfill({json:report()});});
 await setup(page);
 const preview=page.locator('.imagery-preview');await preview.scrollIntoViewIfNeeded();
 await expect(preview.getByRole('button',{name:'미리보기 재시도'})).toBeVisible();
 await page.waitForTimeout(500);expect(count).toBe(1);
 await preview.getByRole('button',{name:'미리보기 재시도'}).click();
 await expect(preview.locator('img')).toBeVisible();expect(count).toBe(2);
});

test('TEST ONLY expired media session is prepared again once',async({page})=>{
 let count=0;
 await page.route('**/api/media/inspect',r=>{count++;return count===1?r.fulfill({status:409,json:{error:{code:'MEDIA_SESSION_REQUIRED',message:'TEST ONLY'}}}):r.fulfill({json:report()});});
 await setup(page);
 const preview=page.locator('.imagery-preview');await preview.scrollIntoViewIfNeeded();
 await expect(preview.locator('img')).toBeVisible();expect(count).toBe(2);
});

test('TEST ONLY repeated missing receipt ends in retry state after one recovery',async({page})=>{
 let count=0;
 await page.route('**/api/media/inspect',r=>{count++;return r.fulfill({json:report(`/api/media/previews/TEST_ONLY_${count}`)});});
 await setup(page,true);
 const preview=page.locator('.imagery-preview');await preview.scrollIntoViewIfNeeded();
 await expect(preview.getByRole('button',{name:'미리보기 재시도'})).toBeVisible();
 await page.waitForTimeout(700);expect(count).toBe(2);
});

test('TEST ONLY late response does not appear on another scene; mobile has no horizontal overflow',async({page})=>{
 await page.setViewportSize({width:390,height:844});
 let release!:()=>void,started!:()=>void;const held=new Promise<void>(resolve=>release=resolve),requested=new Promise<void>(resolve=>started=resolve);
 await page.route('**/api/media/inspect',async r=>{started();await held;await r.fulfill({json:report('/api/media/previews/OLD_TEST_ONLY')}).catch(()=>{});});
 await setup(page);
 const preview=page.locator('.imagery-preview');await preview.scrollIntoViewIfNeeded();
 await requested;
 await page.getByTestId('other-results').getByRole('button',{name:'지도에서 선택'}).first().click();
 release();
 await expect(page.getByTestId('selected-scene-detail')).not.toContainText(ref.id);
 // The old scene remains in the results list and may legitimately finish its own
 // visible thumbnail. It must never become the newly selected scene's preview.
 await expect(page.locator('.imagery-preview img[src="/api/media/previews/OLD_TEST_ONLY"]')).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});


