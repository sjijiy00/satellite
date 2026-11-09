// Optional local API forwarding for testing current backend code without restarting a user's server.
// route.fetch performs real HTTP; individual TEST ONLY routes still explicitly supply fixtures.
import {test as base,type Route,type Locator,type Page} from '@playwright/test';
export * from '@playwright/test';
export async function searchProduct(page:Page,id:string){
  // Explicit manual defaults for engine regression fixtures; production has no
  // guessed dates and no rule fallback. AI contract tests supply their own dates.
  if(!await page.getByLabel('시작일',{exact:true}).inputValue())await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');
  if(!await page.getByLabel('종료일',{exact:true}).inputValue())await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
  const manual=page.getByRole('button',{name:'직접 입력으로 계속',exact:true});
  if(await manual.isVisible())await manual.click();
  await page.getByTestId(`sensor-${id}`).getByRole('button',{name:/이 제품 선택|선택한 제품/}).click();
  await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
}
// Explicit UI disclosure: production result cards now start with bands collapsed.
export async function openBandPanel(card:Locator){
 const details=card.locator('details.asset-downloads');
 if(!await details.evaluate(e=>(e as HTMLDetailsElement).open))await details.locator(':scope > summary').click();
}
export async function openCollectionComparison(page:Page){
 const details=page.locator('.collection-comparison');
 if(!await details.evaluate(e=>(e as HTMLDetailsElement).open))await details.locator(':scope > summary').click();
 const comparison=details.getByRole('region',{name:'여러 영상 비교와 해석'});await base.expect(comparison).toBeVisible();return comparison;
}
export async function openComparison(page:Page){
  await prepareProcessing(page);
  if(!await page.getByLabel('비교 목적',{exact:true}).isVisible())await page.getByTestId('next-work').getByRole('button',{name:'두 장면 비교·분석',exact:true}).click();
}
export async function confirmDetail(page:Page,id?:string){
  const panel=page.getByTestId('analysis-selection');await base.expect(panel).toBeVisible();
  if(id)await panel.locator(`input[value="${id}"]`).check();
  else if(!await panel.getByRole('radio',{checked:true}).count()){
    const domain=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('satellite-workflow-v1')||'null')?.form.purposeType);
    const fixtureChoice=({vegetation:'vegetation_index',thermal:'surface_temperature',flood:'water_extent',urban:'urban_index'} as Record<string,string>)[domain];
    if(fixtureChoice)await panel.locator(`input[value="${fixtureChoice}"]`).check();
  }
  const button=panel.getByRole('button',{name:'이 세부 분석 확인',exact:true});if(await button.count())await button.click();
}
export async function prepareProcessing(page:Page){
  if(new URL(page.url()).pathname==='/processing'){await confirmDetail(page);return;}
  // Legacy engine fixture tests predate acquisition tracking. Supply an explicit
  // TEST ONLY *past receipt* fixture; no provider bytes or real download claim.
  // New workflow-pages tests exercise the actual UI receipt path independently.
  await base.expect(page.getByRole('link',{name:'세부 분석 선택으로',exact:true})).toBeVisible();
  await page.waitForFunction(()=>!!JSON.parse(sessionStorage.getItem('satellite-workflow-v1')||'null')?.data);
  const seeded=await page.evaluate(()=>{
    const raw=sessionStorage.getItem('satellite-workflow-v1');if(!raw)return null;
    const saved=JSON.parse(raw),items=saved.data?.items;
    if(!Array.isArray(items)||!items.length||!items.every((s:{id:string})=>s.id.startsWith('TEST_ONLY')))return null;
    saved.bands??={};saved.acquisitions??={};
    const ready=items.every(s=>{
      const key=JSON.stringify(s.provider_id?[s.provider_id,s.collection,s.id]:[s.collection,s.id]);
      const required=[...(s.purpose_plan?.default_keys||[]),...(s.collection==='sentinel-2-l2a'?['green']:[])];
      return required.every((band:string)=>saved.bands[key]?.includes(band)&&saved.acquisitions[key]?.[band]?.status==='received');
    });if(ready)return null;
    for(const s of items){
      const key=JSON.stringify(s.provider_id?[s.provider_id,s.collection,s.id]:[s.collection,s.id]);
      const keys=[...(s.purpose_plan?.default_keys||[])];if(s.collection==='sentinel-2-l2a'&&!keys.includes('green'))keys.push('green');
      saved.bands[key]=keys;saved.acquisitions[key]=Object.fromEntries(keys.map((key:string)=>[key,{status:'received',bytes:64,at:Date.now()}]));
    }
    return JSON.stringify(saved);
  });
  if(seeded){await page.addInitScript(value=>sessionStorage.setItem('satellite-workflow-v1',value),seeded);await page.reload({waitUntil:'domcontentloaded'});}
  await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();
  await base.expect(page).toHaveURL(/\/processing$/);
  await confirmDetail(page);
}
export async function fetchCurrentApi(route:Route){
  const original=new URL(route.request().url()),target=process.env.E2E_API_BASE_URL;
  // Retry only a reset connection for small read-only local configuration GETs.
  // Never replay a search, job, download or other POST; HTTP failures remain failures.
  const configuration=route.request().method()==='GET'&&['/api/request/config','/api/places/config','/api/analysis/catalog','/api/auth/earthdata/status','/api/operator/status'].includes(original.pathname);
  return route.fetch({url:target?`${new URL(target).origin}${original.pathname.replace(/^\/api/,'')}${original.search}`:original.href,timeout:120000,maxRetries:configuration?1:0});
}
export async function clickArtifact(link:Locator){
  const target=process.env.E2E_API_BASE_URL;
  if(target){
    const path=await link.getAttribute('href');
    if(!path||!/^\/api\/(cloud|estimate)\/jobs\/[a-f0-9]{32}\/download$/.test(path))throw new Error('Unexpected application artifact URL');
    // Chromium cancels intercepted attachment navigations. Keep the app's validated job/path,
    // rebase only the test transport, and let the browser download the real backend bytes.
    await link.evaluate((node,href)=>{(node as HTMLAnchorElement).href=href;},`${new URL(target).origin}${path.slice(4)}`);
  }
  await link.click();
}
export const test=base.extend<{localApi:void}>({
  localApi:[async({context},use)=>{
    const target=process.env.E2E_API_BASE_URL;
    if(target){
      const origin=new URL(target);
      if(!['127.0.0.1','localhost'].includes(origin.hostname))throw new Error('E2E_API_BASE_URL must be a local backend');
      await context.route('**/api/**',async route=>{
        try{
          const response=await fetchCurrentApi(route);
          await route.fulfill({response}).catch(()=>{});
        }catch(error){
          // Playwright's API transport is disposed at test completion even when
          // an automatic thumbnail was started just before teardown. This is a
          // cancelled test request, never an application/provider success.
          if(error instanceof Error&&/route\.fetch: (Test ended\.|Target page, context or browser has been closed|Request context disposed)/.test(error.message))return;
          throw error; // real provider/network errors must still fail the test
        }
      });
    }
    // New automatic lookup must never spend a user's Kakao quota during default E2E.
    // Per-test explicit page routes supply TEST ONLY successes/errors where needed.
    await context.route('**/api/places/search',route=>route.fulfill({json:{status:'not_configured',mentioned_text:route.request().postDataJSON().place,message:'TEST ONLY 외부 Kakao 조회 차단',candidates:[],role:'camera_only'}}));
    // Automatic AI is paid. Default and LIVE_STAC tests MUST NOT reach OpenAI.
    await context.route('**/api/request/interpret',route=>{
      if(!route.request().postDataJSON()?.resolve_conditions)return route.fallback();
      return route.fulfill({json:{condition_proposals:{status:'failed',period:{status:'absent'},region:{status:'absent'},messages:['TEST ONLY 유료 AI 전송 차단'],event_reference_required:false,scope:'TEST ONLY',engine:{mode:'ai',status:'not_configured',provider:null,model:null}}}});
    });
    // Fixture runs must not silently depend on a public provider. Explicit
    // per-test page routes take precedence; unmocked searches are test errors.
    let accidentalLiveSearches=0;
    if(process.env.LIVE_STAC!=='1')await context.route('**/api/search',route=>{accidentalLiveSearches++;return route.fulfill({status:503,json:{error:{code:'TEST_LIVE_DISABLED',message:'Unmocked provider search requires explicit LIVE_STAC=1'}}});});
    await use();
    base.expect(accidentalLiveSearches,'Unmocked provider search requires explicit LIVE_STAC=1').toBe(0);
  },{auto:true}],
});
// Automatic thumbnails may still have transport requests in flight when the
// assertions finish. Detach routes before Playwright tears down the page/context;
// a cancelled test transport must not be attributed to the following test.
test.afterEach(async({page,context})=>{
  await page.unrouteAll({behavior:'ignoreErrors'});
  await context.unrouteAll({behavior:'ignoreErrors'});
});
