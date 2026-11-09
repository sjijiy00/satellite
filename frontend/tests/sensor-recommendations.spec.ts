import {test,expect,searchProduct,type Page} from './runtime';
import {fixture,status,collections} from './fixtures';
import type {Recommendation} from '../src/lib/types';

async function purpose(page:Page,value:string) {
  await page.getByLabel('목적 직접 선택',{exact:false}).selectOption(value);
}
test('실제 추천 API: 모호한 목적·가정·SAR 검색 지원·열환경과 야간 필수 조건',async({page})=>{
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
  await expect(page.locator('.recommendation')).toContainText('어떤 분석인가요');
  await expect(page.locator('.sensor-card')).toHaveCount(0);
  await purpose(page,'vegetation');
  await expect(page.locator('.sensor-card')).toHaveCount(8);
  for(const id of ['s2_msi','landsat_oli','viirs_sr','pc_s2_msi','pc_landsat_oli','noaa_viirs_ndvi','hls_l30','hls_s30'])await expect(page.getByTestId('sensor-'+id)).toBeVisible();
  await expect(page.getByTestId('sensor-s2_msi')).toContainText('red:');
  await expect(page.getByTestId('sensor-s2_msi')).toContainText('nir:');
  await expect(page.locator('.sensor-assumptions')).toContainText('대상 크기 미입력');
  await expect(page.getByTestId('sensor-s2_msi').getByTestId('sensor-availability')).toContainText('미검색 / 미확인');
  await expect(page.getByTestId('sensor-s2_msi').getByTestId('sensor-qa')).toContainText('미검사');
  await page.getByRole('region',{name:'탑재체·센서 추천',exact:true}).screenshot({path:'test-results/sensor-desktop.png'});
  await purpose(page,'flood');
  await expect(page.getByTestId('sensor-s1_csar').getByRole('button')).toBeEnabled();
  await expect(page.getByTestId('sensor-s2_msi').getByTestId('sensor-fit')).toContainText('조건부 보완');
  await purpose(page,'thermal');
  await expect(page.locator('.sensor-card')).toHaveCount(2);
  await expect(page.getByTestId('sensor-pc_landsat_tirs')).toContainText('planetary-computer');
  await expect(page.getByTestId('sensor-landsat_tirs')).toContainText('TIRS-2');
  await expect(page.getByTestId('sensor-landsat_tirs')).toContainText('L2SP');
  await expect(page.getByTestId('sensor-s2_msi')).toHaveCount(0);
  await page.getByText('관측 조건 선택 (선택 입력)',{exact:true}).click();
  await page.getByLabel('구름·야간 관측 필요',{exact:true}).selectOption('night');
  await expect(page.getByTestId('sensor-landsat_tirs').getByRole('button')).toBeDisabled();
  await expect(page.getByTestId('sensor-pc_landsat_tirs').getByRole('button')).toBeDisabled();
  await expect(page.getByTestId('sensor-landsat_tirs').getByTestId('sensor-fit')).toContainText('필수 조건 미충족');
});

test('실제 카드 검색: AOI·기간·선택 조건 보존, 제품 필터와 추천 밴드 연결',async({page},testInfo)=>{
  test.skip(process.env.LIVE_STAC!=='1','실제 카드 검색은 LIVE_STAC=1 별도 실행');
  const failures:string[]=[];
  page.on('response',r=>{if(r.status()>=400){const u=new URL(r.url());failures.push(`${r.status()} ${u.origin}${u.pathname.replace(/[a-f0-9]{32}/g,'[id]')}`);}});
  page.on('pageerror',e=>failures.push(e.message));
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await purpose(page,'vegetation');
  await page.getByRole('button',{name:'충남 예시 영역'}).click();
  await page.getByLabel('시작일',{exact:true}).fill('2025-07-05');
  await page.getByText('관측 조건 선택 (선택 입력)',{exact:true}).click();
  await page.getByLabel('구분하려는 대상의 대략적 크기 (m)',{exact:true}).fill('100');
  await page.getByLabel('관측 시점',{exact:true}).selectOption('change');
  // A card supplies its supported collection even when manual selection is empty.
  await page.getByLabel('위성 선택',{exact:true}).selectOption('manual');
  await page.getByLabel('Sentinel-2 Level-2A',{exact:true}).uncheck();
  await page.getByLabel('Landsat Collection 2 Level-2',{exact:true}).uncheck();
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/search'));
  await searchProduct(page,'s2_msi');
  const response=await responsePromise, sent=response.request().postDataJSON(),data=await response.json();
  expect(response.status()).toBe(200);
  expect(sent).toMatchObject({recommendation_id:'s2_msi',collections:['sentinel-2-l2a'],bbox:[126.5,36.3,127,36.8],start_date:'2025-07-05',end_date:'2025-07-31',target_size_m:100,temporal_mode:'change'});
  expect(data.returned).toBeGreaterThan(0);
  expect(data.items.every((i:any)=>i.collection==='sentinel-2-l2a'&&i.purpose_plan.product_status==='met'&&!i.purpose_plan.missing_bands.length)).toBe(true);
  await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-07-05');
  await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue('126.5');
  await expect(page.getByTestId('sensor-s2_msi').getByTestId('sensor-availability')).toContainText('검색됨');
  await expect(page.getByTestId('sensor-s2_msi').getByTestId('sensor-qa')).toContainText('미검사');
  const card=page.getByTestId('primary-results').getByTestId('scene-card').first();
  const keys=data.items.find((i:any)=>i.purpose_plan.group==='primary').purpose_plan.default_keys;
  for(const key of keys)await expect(card.getByTestId('band-'+key)).toBeChecked();
  await testInfo.attach('live-network-errors',{body:JSON.stringify(failures),contentType:'application/json'});
  expect(failures).toEqual([]);
});

for(const failed of [false,true])test(`추천 카드 가용성: ${failed?'실패는 없음과 구별':'완료된 0건만 없음'}`,async({page})=>{
  // Only search transport is a test fixture; recommendation rules come from the real API.
  await page.route('**/api/search',async route=>{
    const recResponse=await page.request.post('/api/recommend',{data:{purpose:'식생',purpose_type:'vegetation'}});
    const rec:Recommendation=await recResponse.json();
    for(const card of rec.cards||[])if(card.id==='s2_msi')card.availability={status:failed?'failed':'none',count:failed?null:0,message:failed?'TEST ONLY 검색 실패':'TEST ONLY 목적을 유지하며 기간을 조정하세요.'};
    const result={...fixture('vegetation',0),recommendation:rec,outcome:failed?'failed':'empty',collection_statuses:[status(collections[0],failed?'failed':'empty')],error:failed?{message:'TEST ONLY timeout'}:undefined};
    await route.fulfill({status:failed?504:200,json:result});
  });
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await purpose(page,'vegetation');
  await page.getByRole('button',{name:'충남 예시 영역'}).click();
  await searchProduct(page,'s2_msi');
  await expect(page.getByTestId('sensor-s2_msi').getByTestId('sensor-availability')).toContainText(failed?'검색 실패':'없음');
  await expect(page.getByTestId('sensor-landsat_oli').getByTestId('sensor-availability')).toContainText('미검색 / 미확인');
  await expect(page.getByTestId('sensor-s2_msi').getByTestId('sensor-qa')).toContainText('미검사');
});

test('카드 검색 잘못된 기간 차단 및 모바일 카드 배치',async({page})=>{
  await page.setViewportSize({width:390,height:844});await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await purpose(page,'flood');
  await expect(page.locator('.sensor-card')).toHaveCount(7);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  const cards=page.locator('.sensor-card');
  const first=await cards.nth(0).boundingBox(),second=await cards.nth(1).boundingBox();
  expect(second!.y).toBeGreaterThan(first!.y+first!.height);
  await page.getByRole('region',{name:'탑재체·센서 추천',exact:true}).screenshot({path:'test-results/sensor-mobile.png'});
  await page.getByRole('button',{name:'충남 예시 영역'}).click();
  await page.getByLabel('시작일',{exact:true}).fill('2025-08-01');
  let searches=0;page.on('request',r=>{if(r.url().endsWith('/api/search'))searches++;});
  await searchProduct(page,'s2_msi');
  await expect(page.locator('.error[role="alert"]')).toContainText('시작일과 종료일');
  expect(searches).toBe(0);
});
