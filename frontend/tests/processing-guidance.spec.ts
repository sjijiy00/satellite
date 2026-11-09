// TEST ONLY workflow fixtures. No AI, provider authentication or real raster reads.
import {mkdir} from 'node:fs/promises';
import {test,expect,searchProduct,type Page} from './runtime';
import {fixture} from './fixtures';
import {sceneKey,type Purpose} from '../src/lib/types';

async function setup(page:Page,domain:Purpose){
 const data=fixture(domain,2);data.items=data.items.filter(s=>s.collection===(domain==='thermal'?'landsat-c2-l2':'sentinel-2-l2a')).map(s=>({...s,provider_id:'earth-search'}));
 if(domain==='thermal')for(const s of data.items){
  s.platform='landsat-9';s.processing_level='L2SP';
  s.download_assets=['lwir11','qa_pixel','qa_radsat'].map(key=>({key,title:key,href:'https://example.test/TEST_ONLY/'+key+'.tif',direct_url:null,media_type:'image/tiff',requester_pays:false,access_note:'TEST ONLY',common_names:[key==='lwir11'?'thermal':key],roles:[]}));
  s.purpose_plan={...s.purpose_plan!,analysis_keys:['lwir11'],default_keys:['lwir11','qa_pixel','qa_radsat'],product_status:'met'};
 }
 data.returned=data.items.length;data.recommendation.label=domain==='thermal'?'열환경 분석':'식생 분석';
 let searches=0,processes=0,downloads=0;
 await page.route('**/api/search',r=>{searches++;const q=r.request().postDataJSON();data.query={bbox:q.bbox,start_date:q.start_date,end_date:q.end_date};return r.fulfill({json:data});});
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY_GUIDANCE'}}));
 const body=Buffer.from([73,73,42,0,84,69,83,84]);
 await page.route('**/api/media/inspect',r=>{const q=r.request().postDataJSON();return r.fulfill({json:{reference:q,preview:null,assets:q.asset_keys.map((key:string)=>({key,status:'available',access_verified:true,message:'TEST ONLY',size_bytes:body.length,download_url:'/api/media/downloads/TEST_ONLY_'+key}))}});});
 await page.route('**/api/media/downloads/**',r=>{downloads++;return r.fulfill({body,contentType:'application/octet-stream',headers:{'Content-Disposition':'attachment; filename="TEST_ONLY_original.tif"'}});});
 await page.route(/\/api\/(?:cloud\/plan|cloud\/jobs|estimate\/plan|estimate\/jobs|change-analysis|pixel-quality)(?:\?|$)/,r=>{processes++;return r.fulfill({status:503,json:{error:{message:'TEST ONLY must not execute automatically'}}});});
 await page.goto('/');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption(domain);
 await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
 for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));
 await searchProduct(page,domain==='thermal'?'landsat_tirs':'s2_msi');
 return {data,counts:()=>({searches,processes,downloads})};
}
async function enter(page:Page,id:string){
 await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();
 const panel=page.getByTestId('analysis-selection');await panel.locator(`input[value="${id}"]`).check();await panel.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
}

for(const width of [1280,390])test(`TEST ONLY ${width}px 빈 처리 화면은 단일 수집 복귀 안내`,async({page})=>{
 await page.setViewportSize({width,height:844});await page.goto('/processing');
 const empty=page.getByTestId('processing-empty');await expect(empty).toHaveCount(1);await expect(empty).toContainText('선택 영상이 없습니다');
 await expect(empty.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true})).toBeVisible();
 await expect(page.getByRole('region',{name:'현재 작업 요약'})).toHaveCount(0);await expect(page.locator('.map-panel')).not.toBeVisible();
 await expect(page.getByText('분석할 지역에서 어떤 영상이 촬영되었을까요?',{exact:true})).toHaveCount(0);
 await expect(page.getByTestId('next-work')).not.toBeVisible();await expect(page.getByRole('navigation',{name:'처리 단계'})).toHaveCount(0);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await mkdir('../test-results/processing-guidance',{recursive:true});await page.screenshot({path:`../test-results/processing-guidance/empty-${width}.png`,fullPage:true});
 await empty.getByRole('link').click();await expect(page.getByLabel('분석 목적',{exact:true})).toBeVisible();
});

for(const width of [1280,390])test(`TEST ONLY ${width}px 저장된 열환경 L2SP는 확보·메타데이터·GIS만 안내`,async({page})=>{
 await page.setViewportSize({width,height:844});const state=await setup(page,'thermal');await enter(page,'surface_temperature');
 const action=page.getByTestId('processing-next-action'),summary=page.getByRole('region',{name:'현재 작업 요약'});
 await summary.locator(':scope > details > summary').click();
 await expect(summary).toContainText('lwir11 · qa_pixel · qa_radsat');await expect(summary).toContainText('원본 전체 수신 0/3개');
 await expect(action).toContainText('앱 내부 계산 엔진이 연결되지 않았습니다');await expect(action).toContainText('외부 GIS');
 await expect(action.getByRole('link',{name:'원본 확보·선택 밴드 확인으로',exact:true})).toBeEnabled();
 await action.getByText('선택 영상 메타데이터 확인',{exact:true}).click();await expect(action).toContainText('L2SP');await expect(action).toContainText('QA·전처리·분석을 실행한 상태가 아닙니다');
 await expect(page.getByRole('navigation',{name:'처리 단계'})).toHaveCount(0);await expect(page.locator('#preprocess-stage')).toHaveCount(0);await expect(page.locator('#analysis-stage')).toHaveCount(0);
 await expect(page.getByRole('button',{name:'두 날짜 NDVI 작업 열기',exact:true})).toHaveCount(0);await expect(page.getByRole('region',{name:'세부 분석 전처리 계획'})).toHaveCount(0);
 await page.reload();await expect(summary).toContainText('원본 전체 수신 0/3개');await expect(action).toContainText('외부 GIS');
 await expect(page.getByTestId('analysis-selection').locator('input[value="surface_temperature"]')).toBeChecked();
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
 await mkdir('../test-results/processing-guidance',{recursive:true});await summary.screenshot({path:`../test-results/processing-guidance/thermal-${width}.png`});
 await summary.locator(':scope > details > summary').click();await action.getByRole('link').click();await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-07-01');await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue('126.7');
 const card=page.getByTestId('scene-card').first();await expect(card.getByTestId('band-lwir11')).toBeChecked();await expect(card.locator('.asset-downloads')).toHaveAttribute('open','');
 expect(state.counts()).toEqual({searches:1,processes:0,downloads:0});
});

test('TEST ONLY 일부 수신 기록·밴드·뒤로/앞으로·새로고침은 유지하며 미지원 실행 없음',async({page})=>{
 const state=await setup(page,'thermal'),card=page.getByTestId('scene-card').first();
 const details=card.locator('.asset-downloads');if(!await details.evaluate(e=>(e as HTMLDetailsElement).open))await details.locator(':scope > summary').click();
 // Explicit manual edit: defaults are intentionally derived rather than duplicated in saved.bands.
 await card.getByTestId('band-qa_radsat').uncheck();await card.getByTestId('band-qa_radsat').check();
 await card.getByRole('button',{name:'선택 원본 접근 확인',exact:true}).click();const receiving=page.waitForEvent('download');await card.getByRole('button',{name:'원본 다운로드',exact:true}).first().click();expect(await(await receiving).failure()).toBeNull();
 await enter(page,'surface_temperature');await expect(page.getByTestId('work-summary').filter({visible:true})).toContainText('원본 전체 수신 1/3개');
 await page.goBack();await expect(card.getByTestId('band-qa_pixel')).toBeChecked();await page.goForward();await page.reload();
 const summary=page.getByRole('region',{name:'현재 작업 요약'});await expect(summary).toContainText('원본 전체 수신 1/3개');
 const saved=await page.evaluate(()=>JSON.parse(sessionStorage.getItem('satellite-workflow-v1')||'null'));
 expect(saved.acquisitions[sceneKey(state.data.items[0])].lwir11.status).toBe('received');expect(saved.bands[sceneKey(state.data.items[0])]).toEqual(['lwir11','qa_pixel','qa_radsat']);
 expect(state.counts()).toEqual({searches:1,processes:0,downloads:1});
});

test('TEST ONLY 지원 NDVI는 관련 단계 유지 · 브라우저 원본 수신 없이 서버 검사 가능',async({page})=>{
 const state=await setup(page,'vegetation');await enter(page,'vegetation_change');const action=page.getByTestId('processing-next-action');
 await expect(action).toContainText('브라우저 원본 다운로드는 선택 사항입니다');
 const steps=page.getByRole('navigation',{name:'처리 단계'});await expect(steps.getByRole('button')).toHaveCount(3);
 await page.getByRole('button',{name:'두 날짜 NDVI 작업 열기',exact:true}).click();await expect(page.getByRole('button',{name:'두 날짜 NDVI 계산',exact:true})).toBeEnabled();
 await expect(page.getByRole('button',{name:'작은 AOI 픽셀 진단',exact:true})).toBeEnabled();
 await expect(page.locator('#preprocess-stage')).toContainText('NDVI 변화 엔진 내부');expect(state.counts()).toEqual({searches:1,processes:0,downloads:0});
});
