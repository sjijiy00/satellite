import {sceneKey} from '../src/lib/types';
import {test,expect,openComparison,searchProduct,confirmDetail,type Page} from './runtime';
import {readFile} from 'node:fs/promises';
import {fixture,key,collections} from './fixtures';

// TEST ONLY response exercises UI states. The live test below uses no API fixture.
const emptyZip='UEsFBgAAAAAAAAAAAAAAAAAAAAAAAA==';
function sample(label='TEST CURRENT',state:'computed'|'blocked'='computed'){
  return {status:state,analysis_completed:state==='computed',conclusion:label,
    error:state==='blocked'?'TEST ONLY 보정값 상충':null,
    aoi_area_m2:6400,common_observed_area_m2:3200,
    analysis_area_m2:state==='computed'?2400:null,excluded_common_area_m2:state==='computed'?800:null,
    excluded_aoi_area_m2:state==='computed'?4000:null,
    qa_excluded_area_m2:400,numeric_excluded_area_m2:400,
    ndvi_before_mean:.5,ndvi_after_mean:.6,ndvi_difference_mean:.1,
    artifact_base64:state==='computed'?emptyZip:null,artifact_name:'sentinel-2-ndvi-change.zip',
    scenes:[],grid:{width:4,height:4}};
}
async function setup(page:Page){
  await page.route('**/api/search',r=>{const data=fixture('vegetation',3);data.query.bbox=[126.7,36.4,126.71,36.41];return r.fulfill({json:data});});
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');await confirmDetail(page,'vegetation_change');
}
const run=(page:Page)=>page.getByRole('button',{name:'두 날짜 NDVI 계산',exact:true}).click();

test('A4 선택 입력 전달·면적 분모·ZIP 저장·실패 상태',async({page})=>{
  let sent:any,blocked=false;
  await page.route('**/api/change-analysis',r=>{sent=r.request().postDataJSON();return r.fulfill({json:sample('TEST CURRENT',blocked?'blocked':'computed')});});
  await setup(page);
  await page.getByLabel('최소 공통 유효율 운영 기준 (%)',{exact:true}).fill('80');
  await page.getByLabel('사건·변화 기준일 (UTC, 선택 입력)',{exact:true}).fill('2025-07-02');
  await run(page);
  expect(sent).toMatchObject({bbox:[126.7,36.4,126.71,36.41],purpose_type:'vegetation',reference_date:'2025-07-02',minimum_valid_percent:80,
    scene_a:{collection:collections[0],id:'TEST_ONLY_0'}});
  await expect(page.getByTestId('change-report')).toContainText('실제 분석 면적');
  await expect(page.getByTestId('change-report')).toContainText('2,400 m²');
  await expect(page.getByTestId('change-report')).toContainText('이후−이전');
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:'GeoTIFF 2개 + 처리기록 ZIP 저장'}).click();
  const download=await downloadPromise;
  expect(download.suggestedFilename()).toBe('sentinel-2-ndvi-change.zip');
  const bytes=await readFile((await download.path())!);
  expect(bytes.subarray(0,4).toString()).toBe('PK\u0005\u0006');
  blocked=true;await run(page);
  await expect(page.getByTestId('change-report')).toContainText('NDVI 계산 보류');
  await expect(page.getByTestId('change-report')).toContainText('보정값 상충');
  await expect(page.getByRole('button',{name:'GeoTIFF 2개 + 처리기록 ZIP 저장'})).toHaveCount(0);
  await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue('126.7');
});

for(const change of ['reference','scene','threshold'])test(`A4 요청 중 ${change} 변경 시 오래된 분석 폐기`,async({page})=>{
  let release!:()=>void,started!:()=>void,calls=0;
  const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
  await page.route('**/api/change-analysis',async r=>{const n=++calls;if(n===1){started();await gate;}await r.fulfill({json:sample(n===1?'TEST STALE':'TEST CURRENT')});});
  await setup(page);await run(page);await ready;
  if(change==='reference')await page.getByLabel('사건·변화 기준일 (UTC, 선택 입력)',{exact:true}).fill('2025-07-02');
  else if(change==='scene'){
    await page.getByLabel('비교 영상 2',{exact:true}).selectOption(key(collections[0],'TEST_ONLY_2'));
    // This fixture's third footprint has zero AOI overlap. The new preflight
    // must block it rather than accepting a fabricated computed second result.
    await expect(page.getByRole('button',{name:'두 날짜 NDVI 계산',exact:true})).toBeDisabled();
    await expect(page.getByTestId('analysis-selection')).toContainText('AOI 기하 중첩이 확인되지 않았습니다.');
    release();await expect(page.getByTestId('change-report')).toHaveCount(0);expect(calls).toBe(1);return;
  }
  else await page.getByLabel('최소 공통 유효율 운영 기준 (%)',{exact:true}).fill('85');
  await run(page);await expect(page.getByTestId('change-report')).toContainText('TEST CURRENT');release();
  await expect(page.getByTestId('change-report')).not.toContainText('TEST STALE');
});

test('A4 모바일·요청 오류·지원 대상 구분',async({page})=>{
  await page.setViewportSize({width:390,height:844});await setup(page);
  await page.route('**/api/change-analysis',r=>r.fulfill({status:504,json:{error:{message:'TEST ONLY timeout'}}}));
  await run(page);
  const panel=page.getByRole('region',{name:'A4 식생 NDVI 변화 분석',exact:true});
  await expect(panel.getByRole('alert')).toContainText('TEST ONLY timeout');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.getByLabel('비교 영상 2',{exact:true}).selectOption(key(collections[1],'TEST_ONLY_1'));
  await expect(panel.getByRole('button',{name:'A4 NDVI는 선택한 센서 조합 미지원'})).toBeDisabled();
});

test('A4 실제 두 날짜 NDVI 계산과 ZIP 다운로드',async({page},testInfo)=>{
  test.skip(true,'새 흐름은 원본 전체 확보가 선행돼야 하며, 실제 다중 원본 대용량 다운로드는 이번에 승인/실행하지 않음. 엔진은 backend fixture로 검증.');
  const failures:string[]=[];page.on('pageerror',e=>failures.push(e.message));
  page.on('response',r=>{if(r.status()>=400)failures.push(`${r.status()} ${r.url()}`);});
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  await page.getByLabel('시작일',{exact:true}).fill('2021-07-01');
  await page.getByLabel('종료일',{exact:true}).fill('2021-07-31');
  for(const [label,value] of [['서쪽 경도','126.70'],['남쪽 위도','36.40'],['동쪽 경도','126.71'],['북쪽 위도','36.41']])await page.getByLabel(label,{exact:true}).fill(value);
  const searched=page.waitForResponse(r=>r.url().endsWith('/api/search'));
  await searchProduct(page,'s2_msi');
  const items=(await (await searched).json()).items;
  const before=items.find((s:any)=>s.id==='S2B_52SBF_20210716_0_L2A'),after=items.find((s:any)=>s.id==='S2B_52SBF_20210726_0_L2A');
  expect(before?.id).toBeTruthy();expect(after?.id).toBeTruthy();
  await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
  await page.getByLabel('비교 영상 1',{exact:true}).selectOption(sceneKey(before));
  await page.getByLabel('비교 영상 2',{exact:true}).selectOption(sceneKey(after));
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/change-analysis'));
  await run(page);const response=await responsePromise,d=await response.json();
  expect(response.status()).toBe(200);expect(d.status).toBe('computed');
  expect(d.analysis_area_m2).toBeGreaterThan(0);expect(d.analysis_area_m2).toBeLessThan(d.common_observed_area_m2);
  expect(d.artifact_base64.length).toBeGreaterThan(100);
  await expect(page.getByTestId('change-report')).toContainText('NDVI 계산 완료');
  const explorer=page.getByRole('region',{name:'날짜별 영상 탐색과 레이어'});
  await expect(explorer.getByLabel(/실제 AOI 품질 마스크/)).toBeEnabled();
  await expect(explorer.getByLabel(/실제 처리 결과/)).toBeEnabled();
  await expect(page.locator('.map-legend')).toContainText('실제 NDVI 양수·음수');
  await explorer.getByLabel(/실제 처리 결과/).uncheck();
  await expect(page.locator('.map-legend')).not.toContainText('실제 NDVI 양수·음수');
  await explorer.getByLabel(/실제 처리 결과/).check();
  await page.locator('.map-panel').screenshot({path:'test-results/a4-live-map.png'});
  const downloadPromise=page.waitForEvent('download');
  await page.getByRole('button',{name:'GeoTIFF 2개 + 처리기록 ZIP 저장'}).click();
  const download=await downloadPromise;
  await download.saveAs('test-results/a4-live.zip');
  const bytes=await readFile('test-results/a4-live.zip');
  expect(bytes.subarray(0,2).toString()).toBe('PK');
  await page.getByRole('region',{name:'A4 식생 NDVI 변화 분석',exact:true}).screenshot({path:'test-results/a4-live.png'});
  await testInfo.attach('a4-live-summary',{body:JSON.stringify({...d,artifact_base64:'[downloaded ZIP]'},null,2),contentType:'application/json'});
  await testInfo.attach('a4-http-errors',{body:JSON.stringify(failures),contentType:'application/json'});
  expect(failures).toEqual([]);
});
