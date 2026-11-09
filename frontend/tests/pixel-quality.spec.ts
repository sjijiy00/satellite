import {sceneKey} from '../src/lib/types';
import {test,expect,openComparison,searchProduct,type Page} from './runtime';
import {fixture,key,collections} from './fixtures';
import type {PixelReport} from '../src/lib/types';

// TEST ONLY contract fixtures; live test below does not intercept any API.
function report(state:'checked'|'failed'='checked',label='TEST CURRENT'):PixelReport {
  return {status:state,conclusion:label,error:state==='failed'?'TEST ONLY SCL 읽기 실패':undefined,
    aoi_area_m2:6400,common_observed_area_m2:3200,common_valid_area_m2:state==='checked'?0:null,
    common_valid_percent_aoi:state==='checked'?0:null,common_valid_percent_observed:state==='checked'?0:null,
    operational_threshold:{minimum_percent:80,met:state==='checked'?false:null},
    scenes:state==='checked'?[{id:'TEST_ONLY_0',datetime:'2025-07-01T02:00:00Z',status:'checked',error:null,
      valid_area_m2:0,valid_in_common_area_m2:0,valid_percent_aoi:0,valid_percent_common:0,
      exclusions_m2:{cloud_cirrus:6400},headers:[],radiometry:[{status:'unknown'}]}]:[]};
}
async function setup(page:Page){
  await page.route('**/api/search',r=>{const data=fixture('vegetation',3);data.query.bbox=[126.7,36.4,126.71,36.41];return r.fulfill({json:data});});
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
}
const run=(page:Page)=>page.getByRole('button',{name:'작은 AOI 픽셀 진단',exact:true}).click();

test('A3 입력 보존·운영 기준 전달·실제 0%와 실패 null·QA 카드 연결',async({page})=>{
  let sent:any,fail=false;
  await page.route('**/api/pixel-quality',r=>{sent=r.request().postDataJSON();return r.fulfill({json:report(fail?'failed':'checked')});});
  await setup(page);
  await page.getByLabel('최소 공통 유효율 운영 기준 (%)',{exact:true}).fill('80');
  await page.getByLabel('사건·변화 기준일 (UTC, 선택 입력)',{exact:true}).fill('2025-07-02');
  await run(page);await expect(page.getByTestId('pixel-common-percent')).toHaveText('0%');
  expect(sent).toMatchObject({bbox:[126.7,36.4,126.71,36.41],start_date:'2025-07-01',end_date:'2025-07-31',purpose_type:'vegetation',minimum_valid_percent:80,reference_date:'2025-07-02'});
  expect(sent.scene_a).toEqual({collection:collections[0],id:'TEST_ONLY_0'});
  await expect(page.getByTestId('pixel-report')).toContainText('반사도 scale/offset 누락·상충');
  await expect(page.getByTestId('primary-results').getByTestId('scene-card').first()).toContainText('개별 유효 0.00%');
  await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue('126.7');
  fail=true;await run(page);await expect(page.getByTestId('pixel-common-percent')).toHaveText('미확인');
  await expect(page.getByTestId('pixel-report')).toContainText('SCL 읽기 실패');
  await page.getByLabel('비교 영상 2',{exact:true}).selectOption(key(collections[1],'TEST_ONLY_1'));
  await expect(page.getByTestId('pixel-report')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Sentinel-2 L2A 쌍만 지원'})).toBeDisabled();
});

for(const change of ['reference','scene','threshold'])test(`A3 요청 중 ${change} 변경 시 늦은 결과 폐기`,async({page})=>{
  let release!:()=>void,started!:()=>void,calls=0;
  const gate=new Promise<void>(r=>release=r),ready=new Promise<void>(r=>started=r);
  await page.route('**/api/pixel-quality',async r=>{const n=++calls;if(n===1){started();await gate;}await r.fulfill({json:report('checked',n===1?'TEST STALE':'TEST CURRENT')});});
  await setup(page);await run(page);await ready;
  if(change==='reference')await page.getByLabel('사건·변화 기준일 (UTC, 선택 입력)',{exact:true}).fill('2025-07-02');
  else if(change==='scene')await page.getByLabel('비교 영상 2',{exact:true}).selectOption(key(collections[0],'TEST_ONLY_2'));
  else await page.getByLabel('최소 공통 유효율 운영 기준 (%)',{exact:true}).fill('85');
  await run(page);await expect(page.getByTestId('pixel-report')).toContainText('TEST CURRENT');release();
  await expect(page.getByTestId('pixel-report')).not.toContainText('TEST STALE');
});

test('A3 모바일·시간 초과·상한 안내',async({page})=>{
  await page.setViewportSize({width:390,height:844});await setup(page);
  await page.route('**/api/pixel-quality',r=>r.fulfill({status:504,json:{error:{message:'TEST ONLY timeout'}}}));
  await run(page);
  const panel=page.getByRole('region',{name:'A3 픽셀 품질 진단',exact:true});
  await expect(panel.getByRole('alert')).toContainText('TEST ONLY timeout');
  await page.unroute('**/api/pixel-quality');
  await page.route('**/api/pixel-quality',r=>r.fulfill({json:report()}));
  await run(page);await expect(page.getByTestId('pixel-report')).toBeVisible();
  await expect(panel).toContainText('최대 25 km²');
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await panel.screenshot({path:'test-results/a3-mobile.png'});
});

test('A3 실제 두 날짜 SCL·밴드 범위 읽기와 품질 진단',async({page},testInfo)=>{
  test.skip(true,'새 흐름은 원본 전체 확보가 선행돼야 하며, 실제 다중 원본 대용량 다운로드는 이번에 승인/실행하지 않음. 엔진은 backend fixture로 검증.');
  const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
  page.on('response',r=>{if(r.status()>=400)errors.push(`${r.status()} ${r.url()}`);});
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  for(const [label,value] of [['서쪽 경도','126.70'],['남쪽 위도','36.40'],['동쪽 경도','126.71'],['북쪽 위도','36.41']])await page.getByLabel(label,{exact:true}).fill(value);
  await page.getByLabel('최대 조회 개수',{exact:true}).selectOption('25');
  const searched=page.waitForResponse(r=>r.url().endsWith('/api/search'));
  await searchProduct(page,'s2_msi');
  const items=(await (await searched).json()).items.sort((a:any,b:any)=>a.datetime.localeCompare(b.datetime));
  const a=items[0],b=items[items.length-1];
  await openComparison(page);
  await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
  await page.getByLabel('비교 영상 1',{exact:true}).selectOption(sceneKey(a));
  await page.getByLabel('비교 영상 2',{exact:true}).selectOption(sceneKey(b));
  const inspected=page.waitForResponse(r=>r.url().endsWith('/api/pixel-quality'));
  await run(page);const response=await inspected,d=await response.json();
  expect(response.status()).toBe(200);expect(d.status).toBe('checked');
  expect(d.transfer.bytes).toBeGreaterThan(0);expect(d.transfer.bytes).toBeLessThanOrEqual(64*1024*1024);
  expect(d.common_valid_area_m2).toBeGreaterThanOrEqual(0);expect(d.analysis_ready).toBe(false);
  expect(d.scenes.every((s:any)=>s.status==='checked'&&s.headers.every((h:any)=>h.file_header_read))).toBe(true);
  await expect(page.getByTestId('pixel-report')).toContainText('진단 완료');
  await page.getByRole('region',{name:'A3 픽셀 품질 진단',exact:true}).screenshot({path:'test-results/a3-live.png'});
  await testInfo.attach('a3-live-evidence',{body:JSON.stringify(d,null,2),contentType:'application/json'});
  await testInfo.attach('a3-http-errors',{body:JSON.stringify(errors),contentType:'application/json'});
  expect(errors).toEqual([]);
});
