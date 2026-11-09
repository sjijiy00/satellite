import {test,expect,openBandPanel,openComparison,type Page} from './runtime';
import {readFile} from 'node:fs/promises';
import {fixture,collections,key,status} from './fixtures';
import type {Purpose} from '../src/lib/types';

// Capture exact failing URLs instead of declaring console 404s fixed without evidence.
test.beforeEach(async({page},testInfo)=>{
  const failures:string[]=[];
  page.on('response',r=>{if(r.status()>=400)failures.push(`${r.status()} ${r.url()}`);});
  page.on('console',m=>{if(m.type()==='error')failures.push('console '+m.text());});
  page.on('pageerror',e=>failures.push('pageerror '+e.message));
  // Saved through afterEach using an attachment-free in-memory test annotation.
  collectors.set(page,failures);
});
const collectors=new WeakMap<Page,string[]>();
test.afterEach(async({page},testInfo)=>{
  const failures=collectors.get(page)||[];
  await testInfo.attach('network-console',{body:failures.join('\n')||'No HTTP >=400 or console errors',contentType:'text/plain'});
  expect(failures.filter(x=>x.startsWith('pageerror'))).toEqual([]);
});
async function setup(page:Page) {
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
  await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('flood');
  await page.getByRole('button',{name:'충남 예시 영역'}).click();
}
async function run(page:Page) {
  await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  await expect(page.getByTestId('search-status')).toBeVisible();
}
async function synthetic(page:Page) {
  await page.route('**/api/search',route=>route.fulfill({json:fixture(route.request().postDataJSON().purpose_type as Purpose)}));
  await setup(page);await run(page);
}

test('밴드 선택·복원·실제 링크 파일 내용과 두 그룹 페이지 이동',async({page})=>{
  await synthetic(page);
  const primary=page.getByTestId('primary-results'),other=page.getByTestId('other-results');
  const card=primary.getByTestId('scene-card').first();await openBandPanel(card);
  await expect(card.getByTestId('band-green')).toBeChecked();
  await card.getByRole('button',{name:'전체 선택',exact:true}).click();
  await expect(card.locator('input:checked')).toHaveCount(8);
  await card.getByRole('button',{name:'선택 해제',exact:true}).click();
  await expect(card.locator('input:checked')).toHaveCount(0);
  await openBandPanel(card);await card.getByRole('button',{name:'목적 추천으로 복원'}).click();
  await expect(card.locator('input:checked')).toHaveCount(3);
  await card.getByTestId('band-red').check();
  const downloadPromise=page.waitForEvent('download');
  await card.getByRole('button',{name:'선택 링크 목록 저장 (.txt)'}).click();
  const download=await downloadPromise;
  const text=await readFile((await download.path())!,'utf8');
  const urls=text.split(/\r?\n/).filter(x=>x&&!x.startsWith('#'));
  expect(urls).toEqual(['red','green','swir16','scl'].map(n=>`https://example.test/${collections[0]}/TEST_ONLY_0/${n}.tif`));
  expect(text).toContain(collections[0]);expect(text).not.toContain('s3://');expect(text).not.toContain('visual.tif');
  await primary.getByRole('button',{name:'다음',exact:true}).click();
  await expect(primary.getByTestId('scene-card').first()).toContainText('TEST_ONLY_10');
  await other.getByRole('button',{name:'다음',exact:true}).click();
  await expect(other.getByTestId('scene-card').first()).toContainText('TEST_ONLY_10');
  await primary.getByRole('button',{name:'이전',exact:true}).click();
  await expect(card.getByTestId('band-red')).toBeChecked();
  await openBandPanel(card);await card.getByRole('button',{name:'목적 추천으로 복원'}).click();
  await expect(card.getByTestId('band-red')).not.toBeChecked();
  await other.getByRole('button',{name:'이전',exact:true}).click();
  await other.getByTestId('scene-card').first().getByRole('button',{name:'지도에서 선택'}).click();
  await expect(card.getByRole('button',{name:'지도에서 선택'})).toHaveAttribute('aria-pressed','false');
  await expect(other.getByTestId('scene-card').first().getByRole('button',{name:'지도에서 선택'})).toHaveAttribute('aria-pressed','true');
});

test('목적 변경 후 추천 밴드·그룹과 페이지 상태 초기화',async({page})=>{
  await synthetic(page);
  await page.getByTestId('primary-results').getByRole('button',{name:'다음',exact:true}).click();
  await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  await expect(page.getByTestId('primary-results')).toHaveCount(0);
  await run(page);
  const card=page.getByTestId('primary-results').getByTestId('scene-card').first();
  await expect(card).toContainText('TEST_ONLY_0');await expect(card).toContainText('NDVI');
  await expect(card.getByTestId('band-red')).toBeChecked();await expect(card.getByTestId('band-green')).not.toBeChecked();
  await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('thermal');await run(page);
  await expect(card).toContainText('landsat-9');await expect(card.getByTestId('band-lwir11')).toBeChecked();
});

test('센서 비교와 전후 선택 구분·중복·순서·공통 영역 안내',async({page})=>{
  await synthetic(page);
  await openComparison(page);
  const a=page.getByLabel('비교 영상 1',{exact:true}),b=page.getByLabel('비교 영상 2',{exact:true});
  await expect(a).toHaveValue(key(collections[0],'TEST_ONLY_0'));
  await expect(b).toHaveValue(key(collections[1],'TEST_ONLY_0'));
  await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
  await expect(a).toHaveValue(key(collections[0],'TEST_ONLY_0'));
  await expect(b).toHaveValue(key(collections[0],'TEST_ONLY_1'));
  await expect(page.getByTestId('common-geometry')).toContainText('공통 촬영 영역이 있습니다');
  await b.selectOption(key(collections[0],'TEST_ONLY_0'));
  await expect(page.getByText('동일 Item을 두 번 선택했습니다.',{exact:false})).toBeVisible();
  await a.selectOption(key(collections[0],'TEST_ONLY_2'));
  await expect(page.getByText('전후 순서가 역전되었습니다.',{exact:false})).toBeVisible();
  await expect(page.getByTestId('common-geometry')).toContainText('공통 촬영 영역이 없습니다');
  await b.selectOption(key(collections[1],'TEST_ONLY_1'));
  await expect(page.getByText('동일 센서·제품 조건이 확인되지 않습니다.',{exact:false})).toBeVisible();
  await expect(page.getByRole('region',{name:'여러 영상 비교와 해석'})).toContainText('판정 보류');
});

test('전후 모드에 동일 센서 제품 후보가 없으면 다른 컬렉션 자동 선택 금지',async({page})=>{
  await page.route('**/api/search',route=>route.fulfill({json:fixture('flood',1)}));
  await setup(page);await run(page);
  await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
  await expect(page.getByLabel('비교 영상 2',{exact:true})).toHaveValue('');
});

for(const change of ['purpose','date','aoi','collection','limit','size','observation','temporal'])test(`요청 중 ${change} 변경: 오래된 응답 덮어쓰기 차단`,async({page})=>{
  let release!:()=>void, started!:()=>void, completed!:()=>void;
  const gate=new Promise<void>(r=>{release=r;}),sent=new Promise<void>(r=>{started=r;}),done=new Promise<void>(r=>{completed=r;});
  let calls=0;
  await page.route('**/api/search',async route=>{
    const n=++calls;
    if(n===1){started();await gate;}
    const data=fixture(n===1?'flood':'vegetation',1);data.notice=n===1?'STALE_RESPONSE':'CURRENT_RESPONSE';
    try{await route.fulfill({json:data});}finally{if(n===1)completed();}
  });
  await setup(page);await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();await sent;
  if(change==='purpose'){
    await page.getByLabel('분석 목적',{exact:true}).fill('식생');
    await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();
    await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
    await page.getByRole('button',{name:'직접 입력으로 계속',exact:true}).click();
  }
  if(change==='date')await page.getByLabel('시작일',{exact:true}).fill('2025-07-02');
  if(change==='aoi')await page.getByLabel('서쪽 경도',{exact:true}).fill('126.6');
  if(change==='collection')await page.getByLabel('위성 선택',{exact:true}).selectOption('manual');
  if(change==='limit')await page.getByLabel('최대 조회 개수',{exact:true}).selectOption('25');
  if(['size','observation','temporal'].includes(change))await page.getByText('관측 조건 선택 (선택 입력)',{exact:true}).click();
  if(change==='size')await page.getByLabel('구분하려는 대상의 대략적 크기 (m)',{exact:true}).fill('100');
  if(change==='observation')await page.getByLabel('구름·야간 관측 필요',{exact:true}).selectOption('clear_day');
  if(change==='temporal')await page.getByLabel('관측 시점',{exact:true}).selectOption('change');
  await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeEnabled();
  await run(page);release();await done;
  await page.getByText('추천 순위 계산 근거와 조회 범위',{exact:true}).click();
  await expect(page.getByText('CURRENT_RESPONSE',{exact:true})).toBeVisible();
  await expect(page.getByText('STALE_RESPONSE',{exact:true})).toHaveCount(0);
});

test('부분 실패·전체 실패·빈 결과·프록시 타임아웃 구분',async({page})=>{
  let state='partial';
  await page.route('**/api/search',route=>{
    if(state==='proxy')return route.fulfill({status:504,json:{error:{message:'테스트용 프록시 응답 시간 초과'}}});
    const data=fixture('flood',1);
    if(state==='partial'){data.items=data.items.slice(0,1);data.returned=1;data.outcome='partial';data.collection_statuses=[status(collections[0],'success',1),status(collections[1],'failed')];}
    else {data.items=[];data.returned=0;data.outcome=state==='failed'?'failed':'empty';data.collection_statuses=collections.map(c=>status(c,state==='failed'?'failed':'empty'));}
    return route.fulfill({status:state==='failed'?504:200,json:data});
  });
  await setup(page);await run(page);
  await expect(page.getByTestId('search-status')).toContainText('부분 검색 완료');
  await expect(page.getByTestId('scene-card')).toHaveCount(1);
  state='failed';await run(page);await expect(page.getByTestId('search-status')).toContainText('전체 검색 실패');
  await expect(page.getByRole('heading',{name:'검색 결과가 없습니다',exact:true})).toHaveCount(0);
  state='empty';await run(page);await expect(page.getByRole('heading',{name:'검색 결과가 없습니다',exact:true})).toBeVisible();
  state='proxy';await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  await expect(page.locator('.error[role="alert"]')).toContainText('테스트용 프록시 응답 시간 초과');
});

test('모바일 실제 결과 레이아웃과 선택 컨트롤',async({page})=>{
  await page.setViewportSize({width:390,height:844});await synthetic(page);
  await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
  await expect(page.getByTestId('common-geometry')).toContainText('공통 촬영 영역이 있습니다');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await page.getByRole('region',{name:'여러 영상 비교와 해석'}).screenshot({path:'test-results/a1-mobile.png'});
});
