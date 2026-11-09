import {test,expect,openBandPanel,openCollectionComparison,prepareProcessing,openComparison,type Page} from './runtime';
import {fixture,key,collections} from './fixtures';

async function setup(page:Page,modify?:(data:ReturnType<typeof fixture>)=>void){
  await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY_EXPLORER'}}));
  await page.route('**/api/media/inspect',r=>r.fulfill({json:{reference:r.request().postDataJSON(),assets:[],preview:{status:'missing_asset',message:'TEST ONLY 이 영상에는 제공처 원본 미리보기가 없습니다'}}}));
  await page.route('**/api/search',route=>{
    const data=fixture('vegetation',3);modify?.(data);
    const requested=route.request().postDataJSON();
    data.query={...data.query,start_date:requested.start_date,end_date:requested.end_date,bbox:requested.bbox};
    return route.fulfill({json:data});
  });
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
  await page.getByLabel('분석 목적',{exact:true}).fill('식생 분석');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');await page.getByRole('button',{name:'직접 입력으로 계속',exact:true}).click();
  await page.getByRole('button',{name:'충남 예시 영역'}).click();
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  await openComparison(page);await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();
  await expect(page.getByRole('region',{name:'날짜별 영상 탐색과 레이어'})).toBeVisible();
}

test('TEST ONLY 날짜·목록·지도 선택·비교와 미실행 레이어가 연결됨',async({page})=>{
  await setup(page);
  const explorer=page.getByRole('region',{name:'날짜별 영상 탐색과 레이어'});
  await expect(explorer.getByTestId('selected-scene-detail')).toContainText('TEST_ONLY_0');
  await expect(page.getByTestId('map-selected-scene')).toHaveText(key(collections[0],'TEST_ONLY_0'));
  await openBandPanel(page.getByTestId('primary-results').getByTestId('scene-card').first());await page.getByTestId('primary-results').getByTestId('scene-card').first().getByTestId('band-green').check();
  await explorer.getByRole('button',{name:/2025-07-02/}).click();
  await expect(page.getByTestId('active-day-results')).toContainText('2025-07-02 촬영 장면 2건');
  await expect(explorer.getByTestId('selected-scene-detail')).toContainText('TEST_ONLY_1');
  await expect(page.getByTestId('map-selected-scene')).toHaveText(key(collections[0],'TEST_ONLY_1'));
  await expect(page.getByTestId('primary-results').getByTestId('scene-card')).toHaveCount(1);
  await explorer.getByRole('button',{name:/2025-07-03/}).click();
  await expect(page.getByTestId('map-selected-scene')).toHaveText(key(collections[0],'TEST_ONLY_2'));
  await explorer.getByRole('button',{name:/전체/}).click();
  await expect(page.getByTestId('primary-results').getByTestId('scene-card').first().getByTestId('band-green')).toBeChecked();
  await page.getByTestId('other-results').getByTestId('scene-card').nth(1).getByRole('button',{name:'지도에서 선택'}).click();
  await expect(explorer.getByTestId('selected-scene-detail')).toContainText('landsat-9');
  await expect(page.getByTestId('map-selected-scene')).toHaveText(key(collections[1],'TEST_ONLY_1'));
  const comparison=await openCollectionComparison(page);await expect(comparison.getByLabel('수집 비교 영상 1',{exact:true})).toHaveValue(key(collections[0],'TEST_ONLY_0'));
  await comparison.getByLabel('수집 비교 영상 2',{exact:true}).selectOption(key(collections[0],'TEST_ONLY_2'));
  await expect(page.locator('.map-legend')).toContainText('비교 영상 1·2');
  await expect(explorer.getByText('실제 AOI 품질 마스크',{exact:false})).toBeVisible();
  await expect(explorer.getByLabel(/실제 AOI 품질 마스크/)).toBeDisabled();
  await expect(explorer.getByLabel(/실제 처리 결과/)).toBeDisabled();
  await expect(explorer).toContainText('이 영상에는 제공처 원본 미리보기가 없습니다');
  await explorer.getByLabel('실제 Item 촬영 범위').uncheck();
  await expect(page.getByTestId('footprint-count')).toHaveText('0개 범위');
});

test('TEST ONLY 기간 밖·날짜 미확인·구름 미확인은 실제 결과와 구분',async({page})=>{
  await setup(page,data=>{
    data.items[0].datetime='2025-08-01T00:00:00Z';
    data.items[1].datetime=null;
    data.items[2].scene_cloud_cover=null;
  });
  const explorer=page.getByRole('region',{name:'날짜별 영상 탐색과 레이어'});
  await expect(explorer).toContainText('확정 기간 밖 1건, 촬영일 미확인 1건');
  await expect(explorer).toContainText('구름량 미확인 1');
  await expect(page.getByTestId('footprint-count')).toHaveText('4개 범위');
  await expect(page.getByTestId('primary-results').getByTestId('scene-card')).toHaveCount(1);
  await prepareProcessing(page);await expect(page.getByRole('region',{name:'여러 영상 비교와 해석'})).not.toContainText('2025-08-01');
});

test('TEST ONLY 지도 촬영 범위 클릭이 목록·날짜·상세 선택에 반영됨',async({page})=>{
  await setup(page,data=>{
    for(const scene of data.items)scene.geometry=null;
    data.items[4].geometry={type:'Polygon',coordinates:[[[126.7,36.45],[126.9,36.45],[126.9,36.65],[126.7,36.65],[126.7,36.45]]]};
  });
  await expect(page.getByTestId('footprint-count')).toHaveText('1개 범위');
  const map=page.getByTestId('map');await map.scrollIntoViewIfNeeded();
  await page.getByRole('button',{name:'선택 영역으로 이동',exact:true}).click();
  // Navigation resizes the same map while preserving its camera. Locate the
  // actual fixture footprint inside the AOI, rather than assuming viewport
  // center is its geographic center. SW/NE markers project the confirmed bbox.
  await expect.poll(async()=>{
    const sw=await page.getByRole('button',{name:'AOI 꼭짓점 1 드래그',exact:true}).boundingBox();
    const ne=await page.getByRole('button',{name:'AOI 꼭짓점 3 드래그',exact:true}).boundingBox();
    const box=await map.boundingBox();
    return !!(sw&&ne&&box&&sw.x>box.x&&ne.x<box.x+box.width);
  }).toBe(true);
  await page.waitForTimeout(800); // Explicit fit animation, never a substitute for the selection assertion.
  const sw=await page.getByRole('button',{name:'AOI 꼭짓점 1 드래그',exact:true}).boundingBox();
  const ne=await page.getByRole('button',{name:'AOI 꼭짓점 3 드래그',exact:true}).boundingBox();
  expect(sw).not.toBeNull();expect(ne).not.toBeNull();
  await page.mouse.click(sw!.x+sw!.width/2+(ne!.x-sw!.x)*0.6,(sw!.y+sw!.height/2+ne!.y+ne!.height/2)/2);
  await expect(page.getByTestId('map-selected-scene')).toHaveText(key(collections[1],'TEST_ONLY_1'));
  await expect(page.getByTestId('selected-scene-detail')).toContainText('landsat-9');
  await expect(page.getByTestId('active-day-results')).toContainText('2025-07-02');
  await expect(page.getByTestId('other-results').getByTestId('scene-card').first().getByRole('button',{name:'지도에서 선택'})).toHaveAttribute('aria-pressed','true');
});

test('TEST ONLY 부분 실패와 빈 결과, 모바일 배치',async({page})=>{
  await page.setViewportSize({width:390,height:844});
  await setup(page,data=>{data.outcome='partial';data.collection_statuses![1].status='failed';data.collection_statuses![1].error='TEST ONLY timeout';data.items=data.items.filter(s=>s.collection===collections[0]);data.returned=data.items.length;});
  await expect(page.getByTestId('search-status')).toContainText('부분 검색 완료');
  await expect(page.getByTestId('search-status')).toContainText('TEST ONLY timeout');
  await expect(page.getByTestId('primary-results').getByTestId('scene-card')).toHaveCount(3);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByLabel('시작일',{exact:true}).fill('2025-08-01');
  await page.getByLabel('종료일',{exact:true}).fill('2025-08-31');
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  await expect(page.getByRole('region',{name:'날짜별 영상 탐색과 레이어'})).toContainText('현재 기간에 날짜가 확인된 실제 결과가 없습니다');
});

test('지원하는 자연어 후속 요청은 기존 비교·지도 조작으로 연결',async({page})=>{
  await setup(page);
  await prepareProcessing(page);
  const workflow=page.getByRole('region',{name:'다음 작업'});
  await workflow.getByText('다른 작업 요청',{exact:true}).click();
  await workflow.getByLabel('후속 요청').fill('선택한 두 날짜를 비교해');
  await expect(workflow.getByTestId('workflow-structure')).toContainText('두 영상 비교');
  await workflow.getByRole('button',{name:'요청 적용',exact:true}).click();
  await expect(page.getByLabel('비교 목적',{exact:true})).toHaveValue('temporal');
  await workflow.getByLabel('후속 요청').fill('이 지역으로 이동해');
  await expect(workflow.getByTestId('workflow-structure')).toContainText('확정 AOI로 이동');
  await workflow.getByRole('button',{name:'요청 적용',exact:true}).click();
  await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-07-01');
  await expect(page.getByLabel('서쪽 경도')).toHaveValue('126.5');
});
