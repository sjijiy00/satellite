import {test,expect,prepareProcessing,searchProduct,clickArtifact,type Page} from './runtime';
import {readFile} from 'node:fs/promises';
import {fixture,collections} from './fixtures';

// TEST ONLY: these responses never enter the application runtime.
const png='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNoclu1BQAE5wIngLnp3wAAAABJRU5ErkJggg==';
const overlay={png_base64:png,coordinates:[[126.7,36.5],[126.8,36.5],[126.8,36.4],[126.7,36.4]],
  label:'TEST ONLY 거짓색',scene_ids:['TEST_ONLY_0'],source:'TEST ONLY'};
const plan={status:'planned',plan_id:'a'.repeat(32),confirmation_digest:'b'.repeat(64),can_execute:true,
  target_id:'TEST_ONLY_0',target_date:'2025-07-01',period:{start:'2025-07-01',end:'2025-07-31',timezone:'UTC'},
  method:{name:'TEST ONLY supervised regressor',version:'TEST_ONLY.1',description:'맑은 픽셀을 가리고 다른 날짜를 입력해 추정합니다.',
    training:'TEST ONLY clear pixels',validation:'TEST ONLY spatial holdout',limitations:['같은 시점 가린 지면의 참값은 미확인']},
  validation:{status:'passed',train_pixels:120,holdout_pixels:30,rmse_by_band:{red:0.08,nir:0.12},
    baseline_rmse_by_band:{red:0.1,nir:0.16},mae_by_band:{red:0.05,nir:0.07},
    error_q90_by_band:{red:0.13,nir:0.18},baseline_mae_by_band:{red:0.06,nir:0.1},note:'TEST ONLY holdout'},
  areas:{aoi_m2:1000,observed_m2:600,estimated_m2:300,remaining_gap_m2:100},
  source_dates:['2025-07-01','2025-07-02'],grid:{resolution_m:20,width:2,height:2,crs:'TEST ONLY',extent:[0,0,40,40]}};

const compositeEvidence={status:'planned',plan_id:'d'.repeat(32),confirmation_digest:'e'.repeat(64),can_execute:true,
  aoi_area_m2:1000,original_valid_area_m2:600,composite_valid_area_m2:800,remaining_gap_area_m2:200,
  scenes:[{id:'TEST_ONLY_0',collection:collections[0],datetime:'2025-07-01T02:00:00Z',status:'checked',valid_area_m2:600,valid_percent_aoi:60,exclusions_m2:{cloud_cirrus:400}}]};
async function setup(page:Page){
  await page.route('**/api/cloud/plan',r=>r.fulfill({json:compositeEvidence}));
  await page.route('**/api/search',r=>{const data=fixture('vegetation',3);data.query.bbox=[126.7,36.4,126.71,36.41];return r.fulfill({json:data});});
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
  await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));await page.getByRole('button',{name:'좌표 적용',exact:true}).click();await page.getByText('관측 조건 선택 (선택 입력)',{exact:true}).click();await page.getByLabel('관측 시점',{exact:true}).selectOption('single');
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  await prepareProcessing(page);
  const workflow=page.getByTestId('next-work');
  await workflow.getByRole('button',{name:'구름·그림자·NoData 대응 안내'}).click();
  await workflow.getByLabel('현재 기간의 대체 후보와 날짜를 확인했습니다').check();
  await workflow.getByRole('button',{name:'현재 기간 후보 검사·합성 계획'}).click();
  await workflow.getByText('3. 남은 결측 · 실험적 ML 추정 (선택)',{exact:true}).click();
  await expect(page.getByRole('region',{name:'ML 추정영상 모드'}).getByRole('button',{name:'ML 추정 계획·검증 실행'})).toBeEnabled();
}

test('TEST ONLY 추정 방법·검증·원관측 분리와 확인 후 실제 작업 상태',async({page})=>{
  let sent:any,started:any;
  await page.route('**/api/estimate/plan',r=>{sent=r.request().postDataJSON();return r.fulfill({json:plan});});
  await page.route('**/api/estimate/jobs',r=>{started=r.request().postDataJSON();return r.fulfill({status:202,json:{job_id:'c'.repeat(32),plan_id:plan.plan_id,status:'queued',stage:'TEST ONLY queue',error:null,result:null}});});
  await page.route('**/api/estimate/jobs/**',r=>r.fulfill({json:{job_id:'c'.repeat(32),plan_id:plan.plan_id,status:'succeeded',stage:'TEST ONLY complete',error:null,
    result:{...plan,status:'succeeded',artifact_name:'estimated-image.zip',map_layers:{observed:overlay,estimated:overlay}}}}));
  await setup(page);
  const mode=page.getByRole('region',{name:'ML 추정영상 모드'});
  await expect(page.getByLabel(/ML 추정 픽셀/)).toHaveCount(0);
  await mode.getByRole('button',{name:'ML 추정 계획·검증 실행'}).click();
  expect(sent).toMatchObject({purpose_type:'vegetation',temporal_mode:'single',bbox:[126.7,36.4,126.71,36.41],
    start_date:'2025-07-01',end_date:'2025-07-31',target_scene:{collection:collections[0],id:'TEST_ONLY_0'},allow_date_change:false});
  expect(sent.scene_refs).toHaveLength(3);
  await expect(mode.getByTestId('estimate-plan')).toContainText('TEST ONLY supervised regressor');
  await expect(mode.getByTestId('estimate-plan')).toContainText('보류 픽셀 오차');
  await expect(mode.getByTestId('estimate-plan')).toContainText('같은 시점의 참값 정확도가 아닙니다');
  const run=mode.getByRole('button',{name:'확인한 계획으로 추정영상 생성'});
  await expect(run).toBeDisabled();
  await mode.getByLabel('원관측과 ML 추정의 차이, 검증 한계, 대상 AOI·기간·후보 날짜를 확인했습니다.').check();
  await run.click();
  expect(started).toEqual({plan_id:plan.plan_id,confirmation_digest:plan.confirmation_digest});
  await expect(mode.getByTestId('estimate-job')).toContainText('succeeded');
  await expect(mode.getByTestId('estimate-job')).toContainText('한 날짜의 실측 영상이 아닙니다');
  await expect(mode.getByRole('link',{name:/추정 GeoTIFF/})).toHaveAttribute('href',`/api/estimate/jobs/${'c'.repeat(32)}/download`);
  await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();
  await expect(page.getByLabel(/추정 작업의 실제 원관측 픽셀/)).toBeEnabled();
  await expect(page.getByLabel(/ML 추정 픽셀/)).toBeEnabled();
  await expect(page.locator('.map-legend')).toContainText('ML 추정 픽셀 거짓색');
  await page.getByLabel(/ML 추정 픽셀/).uncheck();
  await expect(page.locator('.map-legend')).not.toContainText('ML 추정 픽셀 거짓색');
  await page.getByLabel('시작일',{exact:true}).fill('2025-07-02');
  await expect(page.getByLabel(/ML 추정 픽셀/)).toHaveCount(0);
});

test('TEST ONLY 학습·검증 불가가 0%나 실행 가능으로 표시되지 않음',async({page})=>{
  await page.route('**/api/estimate/plan',r=>r.fulfill({json:{status:'blocked',error:'TEST ONLY 검증할 맑은 픽셀 부족',can_execute:false,
    validation:{status:'insufficient',train_pixels:0,holdout_pixels:0,rmse_by_band:null,baseline_rmse_by_band:null,note:'TEST ONLY unknown'},
    areas:{aoi_m2:1000,observed_m2:0,estimated_m2:null,remaining_gap_m2:null}}}));
  await setup(page);const mode=page.getByRole('region',{name:'ML 추정영상 모드'});
  await mode.getByRole('button',{name:'ML 추정 계획·검증 실행'}).click();
  await expect(mode.getByTestId('estimate-plan')).toContainText('현재 조건에서 추정 불가');
  await expect(mode.getByTestId('estimate-plan')).toContainText('TEST ONLY 검증할 맑은 픽셀 부족');
  await expect(mode.getByTestId('estimate-plan')).toContainText('미확인');
  await expect(mode.getByRole('button',{name:'확인한 계획으로 추정영상 생성'})).toHaveCount(0);
  await expect(page.getByLabel(/ML 추정 픽셀/)).toHaveCount(0);
});

test('TEST ONLY 기간 변경 중 오래된 계획 폐기·모바일 배치',async({page})=>{
  let release!:()=>void,started!:()=>void;
  const gate=new Promise<void>(resolve=>release=resolve),ready=new Promise<void>(resolve=>started=resolve);
  await page.route('**/api/estimate/plan',async r=>{started();await gate;await r.fulfill({json:plan}).catch(()=>{});});
  await page.setViewportSize({width:390,height:844});await setup(page);
  const mode=page.getByRole('region',{name:'ML 추정영상 모드'});
  await mode.getByRole('button',{name:'ML 추정 계획·검증 실행'}).click();await ready;
  await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();await page.getByLabel('시작일',{exact:true}).fill('2025-07-02');release();
  await expect(mode.getByTestId('estimate-plan')).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});

test('실제 검색→국소 ML 검증→확인→추정 ZIP 저장·지도 출처 구분',async({page})=>{
  test.skip(process.env.LIVE_STAC!=='1','LIVE_STAC=1 enables real public imagery processing.');
  test.setTimeout(180000);
  page.setDefaultTimeout(20000);
  const failures:string[]=[];page.on('pageerror',error=>failures.push(error.message));
  await page.goto('/');
  await page.getByRole('button',{name:'직접 입력으로 계속',exact:true}).click();
  await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  await page.getByLabel('시작일',{exact:true}).fill('2021-07-16');
  await page.getByLabel('종료일',{exact:true}).fill('2021-07-26');
  for(const [label,value] of [['서쪽 경도','126.70'],['남쪽 위도','36.40'],['동쪽 경도','126.71'],['북쪽 위도','36.41']])
    await page.getByLabel(label,{exact:true}).fill(value);
  const searchResponse=page.waitForResponse(response=>response.url().endsWith('/api/search'));
  if(!await page.getByLabel('관측 시점',{exact:true}).isVisible())await page.getByText('관측 조건 선택 (선택 입력)',{exact:true}).click();await page.getByLabel('관측 시점',{exact:true}).selectOption('single');await searchProduct(page,'s2_msi');
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
  const download=await downloadPromise;await download.saveAs('test-results/estimate-live.zip');
  const bytes=await readFile('test-results/estimate-live.zip');expect(bytes.subarray(0,2).toString()).toBe('PK');
  await mode.screenshot({path:'test-results/estimate-live.png'});
  expect(failures).toEqual([]);
});
