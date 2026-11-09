import {test,expect} from '@playwright/test';
import {readFile,writeFile,mkdir} from 'node:fs/promises';
const clickArtifact=async(link:any)=>link.click();
test('LIVE natural place radius to ML artifact',async({page})=>{
 test.skip(process.env.LIVE_NATURAL_DEMO!=='1');test.setTimeout(240000);page.setDefaultTimeout(60000);
 await mkdir('../test-results/natural-demo',{recursive:true});
 const failures:string[]=[];page.on('pageerror',e=>failures.push(e.message));
 await page.route('**/api/request/interpret',async route=>{
  if(route.request().postDataJSON()?.resolve_conditions){
   let n=0;try{n=Number(await readFile('../test-results/natural-demo/ai-attempts.txt','utf8'));}catch{}
   if(n>=2&&process.env.CACHED_DEMO_ONLY!=='1')throw new Error('Approved two-call limit reached');
   if(n<2)await writeFile('../test-results/natural-demo/ai-attempts.txt',String(n+1));
  }
  await route.continue();
 });
 await page.goto('/');
 await page.getByLabel('분석 목적',{exact:true}).fill('충청남도 청양군 화성면 장계리의 지도 검색 중심점에서 반경 1000m 범위로, 2021년 7월 16일부터 2021년 7월 26일까지 식생 상태를 살펴보고 싶어. 한 시점의 NDVI 분석 준비가 목적이고 시기별 변화 비교는 하지 않을게. 구름 결측은 다른 날짜를 참조해서 보충하고 싶어.');
 await expect(page.getByLabel('서쪽 경도',{exact:true})).not.toHaveValue('',{timeout:70000});
 const coords=await Promise.all(['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].map(l=>page.getByLabel(l,{exact:true}).inputValue()));
 await writeFile('../test-results/natural-demo/coordinates.json',JSON.stringify(coords));
 await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2021-07-16');
 await expect(page.getByLabel('종료일',{exact:true})).toHaveValue('2021-07-26');
 await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
 await page.getByTestId('sensor-s2_msi').getByRole('button',{name:/이 제품 선택|선택한 제품/}).click();
 const searchResponse=page.waitForResponse(r=>r.url().endsWith('/api/search'));
 await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  const searched=await (await searchResponse).json();
  expect(searched.items.some((scene:any)=>scene.id==='S2B_52SBF_20210716_0_L2A')).toBe(true);
  expect(searched.items.some((scene:any)=>scene.id==='S2B_52SBF_20210726_0_L2A')).toBe(true);
  for(const id of ['S2B_52SBF_20210716_0_L2A','S2B_52SBF_20210726_0_L2A']){
    const card=page.getByTestId('scene-card').filter({hasText:id});
    await card.locator('details.asset-downloads > summary').click();
    for(const band of ['red','nir','green','scl'])await card.getByTestId('band-'+band).check();
  }
  await page.locator('.scene-card').filter({hasText:'S2B_52SBF_20210716_0_L2A'})
    .getByRole('button',{name:'지도에서 선택'}).click();
  await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();
  const selection=page.getByTestId('analysis-selection');
  await selection.locator('input[value="vegetation_index"]').check();
  await selection.getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
  const workflow=page.getByRole('region',{name:'다음 작업',exact:true});
  await workflow.getByRole('button',{name:'구름·그림자·NoData 대응 안내'}).click();
  await workflow.getByText('합성 후보 날짜 직접 선택').click();
  for(const id of ['S2B_52SBF_20210726_1_L2A','S2B_52SBF_20210716_1_L2A']){
    const input=workflow.locator('.workflow-candidates label').filter({hasText:id}).locator('input');
    if(await input.count()&&await input.isChecked())await input.uncheck();
  }
  const donor=workflow.locator('.workflow-candidates label').filter({hasText:'S2B_52SBF_20210726_0_L2A'}).locator('input');
  if(!await donor.isChecked())await donor.check();
  await workflow.getByLabel('현재 기간의 대체 후보와 날짜를 확인했습니다').check();
  const compositeResponse=page.waitForResponse(r=>r.url().endsWith('/api/cloud/plan'));
  await workflow.getByRole('button',{name:'현재 기간 후보 검사·합성 계획'}).click();
  expect((await (await compositeResponse).json()).remaining_gap_area_m2).toBeGreaterThan(0);
  await workflow.getByText('3. 남은 결측 · 실험적 ML 추정 (선택)',{exact:true}).click();
  const mode=page.getByRole('region',{name:'ML 추정영상 모드'});
  await expect(mode.getByRole('button',{name:'ML 추정 계획·검증 실행'})).toBeEnabled();
  const planResponse=page.waitForResponse(response=>response.url().endsWith('/api/estimate/plan'));
  await mode.getByRole('button',{name:'ML 추정 계획·검증 실행'}).click();
  const plan=await (await planResponse).json();
  expect(plan.status).toBe('planned');
  expect(plan.validation.status).toBe('passed');
  expect(plan.areas.estimated_m2).toBeGreaterThan(0);
  await expect(mode.getByTestId('estimate-plan')).toContainText('구름 아래 같은 시점의 참값 정확도가 아닙니다');
  await mode.getByLabel('원관측과 ML 추정의 차이, 검증 한계, 대상 AOI·기간·후보 날짜를 확인했습니다.').check();
  await mode.getByRole('button',{name:'확인한 계획으로 추정영상 생성'}).click();
  await expect(mode.getByTestId('estimate-job')).toContainText('succeeded',{timeout:110000});
  await expect(page.getByLabel(/추정 작업의 실제 원관측 픽셀/)).toBeEnabled();
  await expect(page.getByLabel(/ML 추정 픽셀/)).toBeEnabled();
  const downloadPromise=page.waitForEvent('download');
  await clickArtifact(mode.getByRole('link',{name:/추정 GeoTIFF/}));
  const download=await downloadPromise;await download.saveAs('../test-results/natural-demo/result.zip');
  const bytes=await readFile('../test-results/natural-demo/result.zip');expect(bytes.subarray(0,2).toString()).toBe('PK');
  await mode.screenshot({path:'../test-results/natural-demo/result.png'});
  expect(failures).toEqual([]);
});
