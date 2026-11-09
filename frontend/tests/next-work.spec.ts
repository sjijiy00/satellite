import {test,expect,prepareProcessing,confirmDetail,openComparison,type Page} from './runtime';
import {fixture,collections,key} from './fixtures';

function evidence(gap=200,valid=60){return {status:'planned',can_execute:true,plan_id:'d'.repeat(32),confirmation_digest:'e'.repeat(64),
  aoi_area_m2:1000,original_valid_area_m2:valid*10,composite_valid_area_m2:1000-gap,remaining_gap_area_m2:gap,
  scenes:[0,1].map(i=>({id:`TEST_ONLY_${i}`,collection:collections[0],datetime:`2025-07-0${i+1}T02:00:00Z`,status:'checked',
    valid_area_m2:valid*10,valid_percent_aoi:valid,exclusions_m2:{cloud_cirrus:(100-valid)*10}}))};}
async function setup(page:Page,purpose='vegetation',modify?:(data:ReturnType<typeof fixture>)=>void,supported=true){
  await page.route('**/api/search',route=>{const data=fixture(purpose as any,3);data.query.bbox=[126.7,36.4,126.71,36.41];modify?.(data);return route.fulfill({json:data});});
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption(purpose);await page.getByText('관측 조건 선택 (선택 입력)',{exact:true}).click();await page.getByLabel('관측 시점',{exact:true}).selectOption('single');await page.getByText('관측 조건 선택 (선택 입력)',{exact:true}).click();
  // TEST ONLY supported small AOI. Oversized-city rejection has a separate
  // explicit LIVE test; a positive QA test must not exceed the real engine cap.
  for(const [i,label]of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));
  await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  await prepareProcessing(page);
  await confirmDetail(page,({vegetation:'vegetation_index',flood:'water_extent',urban:'urban_index',thermal:'surface_temperature'} as Record<string,string>)[purpose]);
  if(supported&&purpose!=='thermal')await expect(page.getByTestId('next-work')).toBeVisible();else await expect(page.getByTestId('next-work')).not.toBeVisible();
}
const next=(page:Page)=>page.getByTestId('next-work');
async function recovery(page:Page){
  await next(page).getByRole('button',{name:'구름·그림자·NoData 대응 안내'}).click();
  await next(page).getByLabel('현재 기간의 대체 후보와 날짜를 확인했습니다').check();
}

test('TEST ONLY 검색 전 입력·추천·단일 검색과 제품 선택은 검색을 실행하지 않음',async({page})=>{
  let searches=0;page.on('request',r=>{if(r.url().endsWith('/api/search'))searches++;});
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  await page.getByTestId('sensor-s2_msi').getByRole('button',{name:'이 제품 선택'}).click();
  await expect(page.getByLabel('후속 요청',{exact:true})).toHaveCount(0);
  await expect(page.getByRole('region',{name:'ML 추정영상 모드'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toHaveCount(1);expect(searches).toBe(0);
});

test('TEST ONLY 미선택·한 장면·두 장면의 다음 작업과 접힌 후속 요청',async({page})=>{
  await setup(page,'vegetation',data=>{data.items=data.items.slice(0,1);data.returned=1;});
  await expect(next(page).getByRole('button',{name:'두 장면 비교·분석'})).toBeDisabled();
  await expect(next(page).getByRole('button',{name:'선택 영상 실제 AOI 품질 검사'})).toBeVisible();
  await expect(next(page).getByLabel('후속 요청')).not.toBeVisible();
  await next(page).getByRole('button',{name:'장면 선택 해제'}).click();
  await expect(page.getByTestId('processing-empty')).toBeVisible();
  await expect(page.locator('.map-panel')).not.toBeVisible();
  await expect(page.getByRole('button',{name:'선택 영상 실제 AOI 품질 검사'})).toHaveCount(0);
});

test('TEST ONLY 장면 구름량으로 AOI 불가 판정 금지·검사 양호/실패 구분',async({page})=>{
  let failed=false;await page.route('**/api/cloud/plan',r=>r.fulfill({json:failed?{status:'failed',error:'TEST ONLY SCL 실패',scenes:[]}:evidence(0,100)}));
  await setup(page,'vegetation',d=>d.items.forEach(s=>s.scene_cloud_cover=99));
  await expect(next(page).getByTestId('next-work-state')).toContainText('미검사');
  await expect(page.getByRole('region',{name:'품질 문제 해결'})).toHaveCount(0);
  await next(page).getByRole('button',{name:'선택 영상 실제 AOI 품질 검사'}).click();
  await expect(next(page).getByTestId('cloud-plan')).toContainText('품질 검사 완료');
  await expect(next(page).getByTestId('next-work-state')).toContainText('실제 AOI 검사 완료');
  await expect(page.getByRole('region',{name:'품질 문제 해결'})).toHaveCount(0);
  failed=true;await next(page).getByRole('button',{name:'선택 영상 실제 AOI 품질 검사'}).click();
  await expect(next(page).getByTestId('cloud-plan')).toContainText('TEST ONLY SCL 실패');
  await expect(next(page).getByTestId('next-work-state')).toContainText('AOI 검사 실패');
  await expect(page.getByRole('region',{name:'ML 추정영상 모드'})).toHaveCount(0);
});

test('TEST ONLY 원본 작업은 선택 장면의 밴드·다운로드를 실제로 엶',async({page})=>{
  await setup(page);
  await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();await page.getByTestId('other-results').getByTestId('scene-card').nth(1).getByRole('button',{name:'지도에서 선택'}).click();await prepareProcessing(page);
  await page.getByTestId('processing-next-action').getByRole('link',{name:'원본 확보·선택 밴드 확인으로',exact:true}).click();
  const selected=page.getByTestId('other-results').locator('.scene-card.selected');
  await expect(selected.locator('.asset-downloads')).toHaveJSProperty('open',true);
  await expect(selected.getByRole('button',{name:'선택 링크 목록 저장 (.txt)',exact:true})).toBeEnabled();
});

test('TEST ONLY QA HTTP 실패는 다음 작업에 미확인으로 전달하고 ML을 열지 않음',async({page})=>{
  await page.route('**/api/pixel-quality',r=>r.fulfill({status:503,json:{error:{message:'TEST ONLY provider unreachable'}}}));
  await setup(page);await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
  await page.getByRole('button',{name:'작은 AOI 픽셀 진단',exact:true}).click();
  await expect(next(page).getByTestId('next-work-state')).toContainText('검사 실패·미확인');
  await expect(page.getByRole('region',{name:'품질 문제 해결'})).toHaveCount(0);
  await expect(page.getByRole('region',{name:'ML 추정영상 모드'})).toHaveCount(0);
  await expect(page.getByLabel(/실제 AOI 품질 마스크/)).toBeDisabled();
});

test('TEST ONLY 실제 QA 저하→대체 영상→합성 근거→결측의 ML 단계와 문맥 초기화',async({page})=>{
  let gap=200;await page.route('**/api/cloud/plan',r=>r.fulfill({json:evidence(gap)}));
  await setup(page);
  await next(page).getByRole('button',{name:'선택 영상 실제 AOI 품질 검사'}).click();
  await expect(page.getByRole('region',{name:'품질 문제 해결'})).toContainText('같은 기간의 다른 실제 영상');
  await expect(next(page).getByRole('button',{name:'현재 기간 후보 검사·합성 계획'})).toBeDisabled();
  await expect(page.getByRole('region',{name:'ML 추정영상 모드'})).toHaveCount(0);
  await next(page).getByLabel('현재 기간의 대체 후보와 날짜를 확인했습니다').check();
  gap=0;await next(page).getByRole('button',{name:'현재 기간 후보 검사·합성 계획'}).click();
  await expect(next(page).getByTestId('cloud-plan')).toContainText('남는 결측');
  await expect(page.getByRole('region',{name:'ML 추정영상 모드'})).toHaveCount(0);
  gap=200;await next(page).getByRole('button',{name:'현재 기간 후보 검사·합성 계획'}).click();
  await expect(next(page).getByText('3. 남은 결측 · 실험적 ML 추정 (선택)',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'ML 추정 계획·검증 실행'})).not.toBeVisible();
  await next(page).getByText('3. 남은 결측 · 실험적 ML 추정 (선택)',{exact:true}).click();
  await expect(page.getByRole('button',{name:'ML 추정 계획·검증 실행'})).toBeEnabled();
  await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();await page.locator('.scene-card').filter({hasText:'TEST_ONLY_1'}).first().getByRole('button',{name:'지도에서 선택'}).click();await prepareProcessing(page);
  await expect(page.getByRole('region',{name:'ML 추정영상 모드'})).toHaveCount(0);
  await expect(next(page).getByTestId('cloud-plan')).toHaveCount(0);
});

for(const purpose of ['flood','thermal','urban'])test(`TEST ONLY ${purpose} 목적은 실제 지원 작업만 제공`,async({page})=>{
  await setup(page,purpose);
  if(purpose==='thermal'){await expect(page.getByTestId('processing-next-action')).toContainText('외부 GIS');await expect(page.getByTestId('processing-next-action')).toContainText('Sentinel-2는 열적외선 지표면 온도 대안이 아닙니다');await expect(page.getByRole('navigation',{name:'처리 단계'})).toHaveCount(0);return;}
  await next(page).getByRole('button',{name:'구름·그림자·NoData 대응 안내'}).click();
  await expect(page.getByRole('region',{name:'ML 추정영상 모드'})).toHaveCount(0);
  await expect(next(page).getByRole('button',{name:'현재 기간 후보 검사·합성 계획'})).toHaveCount(0);
  await expect(next(page).getByRole('link',{name:'원본·밴드·다운로드 확인'})).toBeEnabled();
  if(purpose==='flood')await expect(next(page)).toContainText('SAR 픽셀 처리 미지원');
});

test('TEST ONLY 미지원 제품·후속 요청은 실행한 척하지 않음',async({page})=>{
  const calls:string[]=[];page.on('request',r=>{if(/\/api\/(cloud\/|estimate\/|pixel-quality|change-analysis)/.test(r.url()))calls.push(r.url());});
  await setup(page,'vegetation',d=>d.items.forEach(s=>s.processing_level='L1C'),false);
  await expect(page.getByTestId('processing-next-action')).toContainText('앱 내부 계산 엔진이 연결되지 않았습니다');
  await expect(next(page)).not.toBeVisible();expect(calls).toEqual([]);
});

test('TEST ONLY 지원 자료에서도 미지원 후속 요청을 실행한 척하지 않음',async({page})=>{
  const calls:string[]=[];page.on('request',r=>{if(/\/api\/(cloud\/|estimate\/|pixel-quality|change-analysis)/.test(r.url()))calls.push(r.url());});
  await setup(page);
  await next(page).getByText('다른 작업 요청',{exact:true}).click();
  await next(page).getByLabel('후속 요청').fill('홍수 원인을 AI로 분석해');
  await expect(next(page).getByTestId('workflow-structure')).toContainText('지원하지 않는 요청');
  await expect(next(page).getByRole('button',{name:'요청 적용',exact:true})).toBeDisabled();expect(calls).toEqual([]);
});

test('TEST ONLY 늦은 작업 시작 응답은 취소하고 새 선택에 붙이지 않음',async({page})=>{
  let release!:()=>void,started!:()=>void;const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);let cancelled=false;
  await page.route('**/api/cloud/plan',r=>r.fulfill({json:evidence()}));
  await page.route('**/api/cloud/jobs',async r=>{started();await gate;await r.fulfill({status:202,json:{job_id:'c'.repeat(32),status:'queued',plan_id:'d'.repeat(32)}}).catch(()=>{});});
  await page.route('**/api/cloud/jobs/**/cancel',r=>{cancelled=true;return r.fulfill({json:{status:'cancelled'}});});
  await setup(page);await recovery(page);await next(page).getByRole('button',{name:'현재 기간 후보 검사·합성 계획'}).click();
  await next(page).getByLabel('위 AOI·기간·목적·장면·마스크 정책과 기간 요약 합성을 확인했습니다').check();
  await next(page).getByRole('button',{name:'확인한 계획으로 실제 합성 실행'}).click();await ready;
  await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();await page.locator('.scene-card').filter({hasText:'TEST_ONLY_1'}).first().getByRole('button',{name:'지도에서 선택'}).click();await prepareProcessing(page);release();
  await expect.poll(()=>cancelled).toBe(true);await expect(next(page).getByTestId('cloud-job')).toHaveCount(0);
});

test('TEST ONLY 모바일 핵심 입력·단일 검색→추천/목록→다음 작업과 비교 QA 중복 없음',async({page})=>{
  await page.setViewportSize({width:390,height:844});await setup(page);
  await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();
  // The later collection-readability contract keeps the sole search control
  // with the input, before map/recommendations; choosing a product never runs it.
  const order=await page.evaluate(()=>{const selectors=['#analysis-input','.search-entry[aria-label="실제 영상 검색"]','.sensor-recommendations','#search-results'];
    const all=[...document.querySelectorAll('*')];return selectors.map(s=>all.indexOf(document.querySelector(s)!));});
  expect(order).toEqual([...order].sort((a,b)=>a-b));
  await expect(next(page)).toBeHidden();
  await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();
  await expect(next(page)).toBeVisible();
  await next(page).getByRole('button',{name:'두 장면 비교·분석'}).click();
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
  await expect(page.getByRole('button',{name:'선택 영상 실제 AOI 품질 검사'})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'작은 AOI 픽셀 진단',exact:true})).toHaveCount(1);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await next(page).screenshot({path:'test-results/next-work-mobile.png'});
});
