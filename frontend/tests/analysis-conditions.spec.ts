import {sceneKey} from '../src/lib/types';
import {test,expect,openComparison,searchProduct,type Page} from './runtime';
import {fixture,key,collections} from './fixtures';
import type {ConditionsReport} from '../src/lib/types';

// TEST ONLY: UI contract states; real condition calculations are backend-tested.
function report(label='TEST CURRENT'):ConditionsReport {
  return {version:'TEST_ONLY',checked_at:'2026-10-29T00:00:00Z',status:'conditional',conclusion:label+' 분석 가능 확정 판정은 보류합니다.',
    coverage:{scene_a_percent:75,scene_b_percent:75,common_area_m2:50,common_percent:50,method:'TEST ONLY 기하 면적'},
    checks:[{id:'grid',label:'CRS·해상도·격자',status:'conditional',reason:'격자 차이로 정합 필요',next_action:'공통 격자를 검토하세요.',evidence:{crs:'EPSG:32652'}},
      {id:'pixel-quality',label:'픽셀 품질',status:'unknown',reason:'픽셀 미검사',next_action:'A3 별도 요청',evidence:null}],
    request_count:8,limits:{max_requests:14},pixel_quality:'not_checked',file_headers_read:false};
}
async function setup(page:Page){
  await page.route('**/api/search',r=>r.fulfill({json:fixture('vegetation',3)}));
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  await page.getByRole('button',{name:'충남 예시 영역'}).click();
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
}

test('A2 기준일 전달·입력 보존·기하/픽셀 구분·비교 변경 시 초기화',async({page})=>{
  let sent:any;
  await page.route('**/api/analysis-conditions',r=>{sent=r.request().postDataJSON();return r.fulfill({json:report()});});
  await setup(page);await page.getByLabel('사건·변화 기준일 (UTC, 선택 입력)',{exact:true}).fill('2025-07-02');
  await page.getByRole('button',{name:'두 영상 조건 검사',exact:true}).click();
  const panel=page.getByRole('region',{name:'두 영상 분석 조건 검사',exact:true});
  await expect(panel.getByTestId('conditions-report')).toBeVisible();
  expect(sent).toMatchObject({bbox:[126.5,36.3,127,36.8],start_date:'2025-07-01',end_date:'2025-07-31',reference_date:'2025-07-02',purpose_type:'vegetation'});
  expect(sent.scene_a).toEqual({collection:collections[0],id:'TEST_ONLY_0'});
  await expect(panel.getByTestId('condition-pixel-quality')).toContainText('미확인');
  await expect(panel).toContainText('공통 촬영 영역 / AOI 전체');
  await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-07-01');
  await page.getByLabel('비교 영상 2',{exact:true}).selectOption(key(collections[0],'TEST_ONLY_2'));
  await expect(panel.getByTestId('conditions-report')).toHaveCount(0);
});

for(const change of ['reference','scene'])test(`A2 요청 중 ${change} 변경 시 오래된 검사 폐기`,async({page})=>{
  let release!:()=>void,started!:()=>void;
  const gate=new Promise<void>(r=>{release=r;}),ready=new Promise<void>(r=>{started=r;});
  let calls=0;
  await page.route('**/api/analysis-conditions',async r=>{
    const n=++calls;if(n===1){started();await gate;}
    await r.fulfill({json:report(n===1?'TEST STALE':'TEST CURRENT')});
  });
  await setup(page);await page.getByRole('button',{name:'두 영상 조건 검사',exact:true}).click();await ready;
  if(change==='reference')await page.getByLabel('사건·변화 기준일 (UTC, 선택 입력)',{exact:true}).fill('2025-07-02');
  else await page.getByLabel('비교 영상 2',{exact:true}).selectOption(key(collections[0],'TEST_ONLY_2'));
  await page.getByRole('button',{name:'두 영상 조건 검사',exact:true}).click();
  await expect(page.getByTestId('conditions-report')).toContainText('TEST CURRENT');
  release();
  await expect(page.getByTestId('conditions-report')).not.toContainText('TEST STALE');
});

test('A2 모바일·날짜 오류·검사 요청 실패',async({page})=>{
  await page.setViewportSize({width:390,height:844});await setup(page);
  await page.getByLabel('사건·변화 기준일 (UTC, 선택 입력)',{exact:true}).fill('2025-08-01');
  await page.getByRole('button',{name:'두 영상 조건 검사',exact:true}).click();
  const panel=page.getByRole('region',{name:'두 영상 분석 조건 검사',exact:true});
  await expect(panel.getByRole('alert')).toContainText('검색 기간 안');
  await page.getByLabel('사건·변화 기준일 (UTC, 선택 입력)',{exact:true}).fill('');
  await page.route('**/api/analysis-conditions',r=>r.fulfill({status:504,json:{error:{message:'TEST ONLY timeout'}}}));
  await page.getByRole('button',{name:'두 영상 조건 검사',exact:true}).click();
  await expect(panel.getByRole('alert')).toContainText('TEST ONLY timeout');
  await expect(panel.getByTestId('conditions-report')).toHaveCount(0);
  await page.unroute('**/api/analysis-conditions');
  await page.route('**/api/analysis-conditions',r=>r.fulfill({json:report()}));
  await page.getByRole('button',{name:'두 영상 조건 검사',exact:true}).click();
  await expect(panel.getByTestId('conditions-report')).toBeVisible();
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await panel.screenshot({path:'test-results/a2-mobile.png'});
});

test('A2 실제 원본 Item·Asset HEAD·격자 조건 연결',async({page},testInfo)=>{
  test.skip(process.env.LIVE_STAC!=='1','실제 원본 메타데이터/HEAD는 LIVE_STAC=1 별도 실행');
  const failures:string[]=[];page.on('pageerror',e=>failures.push(e.message));
  page.on('response',r=>{if(r.status()>=400){const u=new URL(r.url());failures.push(`${r.status()} ${u.origin}${u.pathname.replace(/[a-f0-9]{32}/g,'[id]')}`);}});
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  await page.getByRole('button',{name:'충남 예시 영역'}).click();
  await page.getByLabel('최대 조회 개수',{exact:true}).selectOption('25');
  const searched=page.waitForResponse(r=>r.url().endsWith('/api/search'));
  await searchProduct(page,'s2_msi');
  const data=await (await searched).json();
  const items=data.items.sort((a:any,b:any)=>a.datetime.localeCompare(b.datetime));
  const before=items[0],after=items[items.length-1];
  expect(before.datetime.slice(0,10)<after.datetime.slice(0,10)).toBe(true);
  await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
  await page.getByLabel('비교 영상 1',{exact:true}).selectOption(sceneKey(before));
  await page.getByLabel('비교 영상 2',{exact:true}).selectOption(sceneKey(after));
  await page.getByLabel('사건·변화 기준일 (UTC, 선택 입력)',{exact:true}).fill(after.datetime.slice(0,10));
  const inspected=page.waitForResponse(r=>r.url().endsWith('/api/analysis-conditions'));
  await page.getByRole('button',{name:'두 영상 조건 검사',exact:true}).click();
  const response=await inspected,result=await response.json();
  expect(response.status()).toBe(200);
  expect(result.checks.find((c:any)=>c.id==='reference').status).toBe('pass');
  expect(result.checks.find((c:any)=>c.id==='access-0-red').status).toBe('pass');
  expect(result.file_headers_read).toBe(false);expect(result.pixel_quality).toBe('not_checked');
  await expect(page.getByTestId('conditions-report')).toContainText('분석 가능 확정 판정은 보류');
  await page.getByRole('region',{name:'두 영상 분석 조건 검사',exact:true}).screenshot({path:'test-results/a2-live.png'});
  await testInfo.attach('a2-live-evidence',{body:JSON.stringify(result,null,2),contentType:'application/json'});
  await testInfo.attach('a2-http-errors',{body:JSON.stringify(failures),contentType:'application/json'});
  expect(failures).toEqual([]);
});
