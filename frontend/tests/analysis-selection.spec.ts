// TEST ONLY AI transport/search fixtures. Product/task catalog is the current local API.
import {test,expect,searchProduct,type Page} from './runtime';
import {configs,input,interpretation,coordinates} from './ai-primary-fixtures';
import {fixture} from './fixtures';
import {mkdir} from 'node:fs/promises';
import {assessTask,taskInputs,automaticTaskBands} from '../src/lib/analysisFlow';
import {sceneKey} from '../src/lib/types';
import type {AnalysisTask,Purpose} from '../src/lib/types';

test('필수 QA 자동 포함은 기존 밴드를 보존하고 없는 Asset은 생성하지 않음',async({request})=>{
 const catalog=await(await request.get((process.env.E2E_API_BASE_URL||'http://127.0.0.1:8000')+'/analysis/catalog')).json();
 const task=catalog.analyses.find((t:AnalysisTask)=>t.id==='surface_temperature') as AnalysisTask;
 const scene=fixture('thermal',1).items.find(s=>s.collection==='landsat-c2-l2')!;
 scene.provider_id='planetary-computer';scene.collection='pc-landsat-c2-l2';
 const template=scene.download_assets![0];
 scene.download_assets!.push(...['qa','cdist','qa_pixel','qa_radsat'].map(key=>({...template,key,common_names:[],roles:[]})));
 const id=sceneKey(scene),initial={[id]:['lwir11','visual']};
 const result=automaticTaskBands(task,[scene],initial);
 expect(result[id]).toEqual(expect.arrayContaining(['lwir11','visual','qa','cdist']));
 expect(initial[id]).toEqual(['lwir11','visual']);expect(automaticTaskBands(task,[scene],result)).toBe(result);
 scene.download_assets=scene.download_assets!.filter(a=>a.key!=='cdist');
 const missing=automaticTaskBands(task,[scene],initial);expect(missing[id]).not.toContain('cdist');
 expect(assessTask(task,[scene],missing,[126.7,36.4,126.71,36.41],'2025-07-01','2025-07-31').missing.join(' ')).toContain('cdist 필수 밴드/품질 자료 미제공');
});

async function setup(page:Page,domain:Purpose,detail:string|null,text:string,count=2){
 let ai=0,searches=0;const requests:any[]=[];
 await configs(page);
 await page.route('**/api/request/interpret',r=>{
  if(!r.request().postDataJSON().resolve_conditions)return r.fallback();
  ai++;const p=interpretation('', '2025-07-01','2025-07-31').condition_proposals;
  p.request_summary='TEST ONLY '+text;p.domain_candidates=[];p.region={status:'absent'};
  p.fields={purpose_type:{value:domain,evidence:text,basis:'explicit'},detail_intent:{value:detail,evidence:detail?text:null,basis:detail?'explicit':'unspecified'}};
  if(detail==='vegetation_change')p.fields.temporal_mode={value:'change',evidence:'변화',basis:'explicit'};
  p.extraction={purpose_type:domain,temporal_mode:'unspecified',places:[]};return r.fulfill({json:{condition_proposals:p}});
 });
 await page.route('**/api/search',r=>{searches++;const q=r.request().postDataJSON();requests.push(q);const data=fixture(domain,count);data.items=data.items.filter(s=>s.collection===(domain==='thermal'?'landsat-c2-l2':'sentinel-2-l2a'));data.returned=data.items.length;data.query={bbox:q.bbox,start_date:q.start_date,end_date:q.end_date};return r.fulfill({json:data});});
 await page.goto('/');await input(page,text);await expect(page.getByLabel('목적 직접 선택',{exact:false})).toHaveValue(domain);
 await coordinates(page,[126.7,36.4,126.71,36.41]);
 return {counts:()=>({ai,searches}),requests};
}
const panel=(page:Page)=>page.getByTestId('analysis-selection');
async function enter(page:Page){await page.getByRole('link',{name:'세부 분석 선택으로',exact:true}).click();await expect(panel(page)).toBeVisible();}

test('TEST ONLY 더운 곳은 큰 열환경부터 · 세부 분석 강요/자동 실행 없음',async({page})=>{
 const state=await setup(page,'thermal',null,'더운 곳을 보고 싶어');
 await expect(page.getByRole('region',{name:'요청의 큰 분석 분야'})).toContainText('열환경');expect(state.counts()).toEqual({ai:1,searches:0});
 await searchProduct(page,'landsat_tirs');await expect.poll(()=>state.requests.length).toBe(1);expect(state.requests[0].detail_intent).toBeNull();await enter(page);
 await expect(panel(page).getByRole('radio',{checked:true})).toHaveCount(0);
 await expect(page.getByRole('button',{name:'두 날짜 NDVI 작업 열기',exact:true})).toHaveCount(0);
 await panel(page).locator('input[value="hotspots"]').check();
 const detail=panel(page).locator('.analysis-choice-details');await expect(detail).not.toHaveAttribute('open');
 await detail.locator('summary').focus();await page.keyboard.press('Enter');await expect(detail.getByText('주의사항',{exact:true})).toBeVisible();
 await panel(page).locator('input[value="surface_temperature"]').check();await expect(detail).not.toHaveAttribute('open');
 await panel(page).locator('input[value="hotspots"]').check();
 await mkdir('../test-results/analysis-disclosure',{recursive:true});
 for(const width of [1440,390]){await page.setViewportSize({width,height:900});await panel(page).screenshot({path:`../test-results/analysis-disclosure/selection-${width}.png`});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);}
 await panel(page).getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 await expect(panel(page).getByRole('region',{name:'세부 분석 전처리 계획'})).toHaveCount(0);
 await expect(page.getByTestId('processing-next-action')).toContainText('외부 GIS');
 await expect(panel(page)).toContainText('서버 카탈로그가 이 제공처·제품');expect(state.counts().searches).toBe(1);
});

test('TEST ONLY 지표면 온도 의도·추천 요청 보존 → 미리 선택 → 미지원 온도 계산 안내',async({page})=>{
 const state=await setup(page,'thermal','surface_temperature','지표면 온도를 보고 싶어');await searchProduct(page,'landsat_tirs');
 await expect.poll(()=>state.requests.length).toBe(1);
 expect(state.requests[0]).toMatchObject({purpose_type:'thermal',detail_intent:'surface_temperature',bbox:[126.7,36.4,126.71,36.41]});
 await enter(page);await expect(panel(page).locator('input[value="surface_temperature"]')).toBeChecked();
 await panel(page).getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 await expect(panel(page)).toContainText('선택은 의도 확인이며 분석 실행 허가가 아닙니다.');
 await expect(page.getByRole('button',{name:'두 날짜 NDVI 작업 열기',exact:true})).toHaveCount(0);
});

test('TEST ONLY 식생 변화 → 두 시점 입력 재검사·관련 격자/QA 계획 · 서버 입력은 브라우저 수신과 별개',async({page})=>{
 await setup(page,'vegetation','vegetation_change','식생 변화를 보고 싶어');await searchProduct(page,'s2_msi');await enter(page);
 await expect(panel(page).locator('input[value="vegetation_change"]')).toBeChecked();
 await panel(page).getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 await expect(panel(page)).toContainText('필요 입력 메타데이터/선택 확인');
 const plan=panel(page).getByRole('region',{name:'세부 분석 전처리 계획'});await expect(plan).toContainText('좌표계·공통 격자 정렬 · 필수');await expect(plan).toContainText('다중 시기 실제 관측 합성 · 불필요');
 await page.getByRole('button',{name:'두 날짜 NDVI 작업 열기',exact:true}).click();
 await expect(page.getByRole('button',{name:'두 날짜 NDVI 계산',exact:true})).toBeEnabled();
 await panel(page).locator('input[value="vegetation_index"]').check();await expect(panel(page).getByRole('region',{name:'세부 분석 전처리 계획'})).toHaveCount(0);
 await panel(page).getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();await expect(plan).toContainText('좌표계·공통 격자 정렬 · 불필요');
});

test('TEST ONLY 세부 목적 변경·두 시점 부족 → 원문/AOI/기간/기존 장면 유지한 추가 수집',async({page})=>{
 const state=await setup(page,'vegetation',null,'나무가 줄었는지 보고 싶어',1);await searchProduct(page,'s2_msi');await enter(page);
 await panel(page).locator('input[value="vegetation_change"]').check();await panel(page).getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();
 await expect(panel(page)).toContainText('자료 보완 필요');await expect(panel(page)).toContainText('필요한 서로 다른 장면 2개');
 await panel(page).getByRole('link',{name:'같은 조건으로 자료 보완하기',exact:true}).click();
 await expect(page.getByLabel('분석 목적',{exact:true})).toHaveValue('나무가 줄었는지 보고 싶어');
 await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue('126.7');await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-07-01');
 await expect(page.getByRole('region',{name:'현재 작업 요약'})).toContainText('TEST_ONLY_0');expect(state.counts().searches).toBe(1);
 await expect(page.getByTestId('sensor-s2_msi')).toContainText('가능한 대표 세부 분석');
});

test('TEST ONLY 확정 세부 분석 새로고침 복원 · AI/검색/처리 중복 없음',async({page})=>{
 const state=await setup(page,'vegetation','vegetation_index','NDVI를 보고 싶어');await searchProduct(page,'s2_msi');await enter(page);
 await panel(page).getByRole('button',{name:'이 세부 분석 확인',exact:true}).click();await page.reload();
 await expect(panel(page).locator('input[value="vegetation_index"]')).toBeChecked();await expect(panel(page).getByRole('button',{name:'세부 분석 확정됨',exact:true})).toBeDisabled();
 expect(state.counts()).toEqual({ai:1,searches:1});
});

test('TEST ONLY 호환성은 서버 실행 계약의 변수/시점/격자/면적을 표시 · 없는 엔진을 허용하지 않음',async({request})=>{
 const endpoint=process.env.E2E_API_BASE_URL||'http://127.0.0.1:8000';
 const catalog=await (await request.get(endpoint+'/analysis/catalog')).json();
 const task=catalog.analyses.find((t:AnalysisTask)=>t.id==='vegetation_change') as AnalysisTask;
 const data=fixture('vegetation',2),scenes=data.items.filter(s=>s.collection==='sentinel-2-l2a');
 expect(assessTask(task,scenes,{},[126.7,36.4,126.71,36.41],'2025-07-01','2025-07-31').metadataReady).toBe(true);
 expect(assessTask(task,scenes,{},[126.7,36.4,126.71,36.41],'2025-07-01','2025-07-31',10).missing.join(' ')).toContain('20m');
 expect(assessTask(task,scenes,{},[126.5,36.3,127,36.8],'2025-07-01','2025-07-31').missing.join(' ')).toContain('25 km²');
 scenes[1].platform='OTHER';scenes[0].download_assets=scenes[0].download_assets?.filter(a=>a.key!=='nir');
 const result=assessTask(task,scenes,{},[126.7,36.4,126.71,36.41],'2025-07-10','2025-07-31');
 expect(result.engineReady).toBe(false);expect(result.missing.join(' ')).toContain('동일 플랫폼');expect(result.missing.join(' ')).toContain('nir');
 expect(taskInputs(task,scenes[0],scenes,['',''])).toHaveLength(0);
});

test('TEST ONLY 여러 분야의 모호한 요청은 강제 분류 없이 사용자가 큰 분야 수정',async({page})=>{
 await configs(page);await page.route('**/api/request/interpret',r=>{
  if(!r.request().postDataJSON().resolve_conditions)return r.fallback();
  const p=interpretation().condition_proposals;p.fields={purpose_type:{value:null,evidence:null,basis:'unspecified'}};p.domain_candidates=['vegetation','thermal'];p.request_summary='TEST ONLY 나무와 도시 열환경';p.extraction={purpose_type:null,temporal_mode:'unspecified',places:[]};p.region={status:'absent'};return r.fulfill({json:{condition_proposals:p}});
 });
 await page.goto('/');await input(page,'나무와 도시 더위가 궁금해');
 await expect(page.getByLabel('목적 직접 선택',{exact:false})).toHaveValue('');
 const broad=page.getByRole('region',{name:'요청의 큰 분석 분야'});await expect(broad).toContainText('여러 분야 후보');
 await broad.getByRole('button',{name:'열환경 분석',exact:true}).click();await expect(page.getByLabel('목적 직접 선택',{exact:false})).toHaveValue('thermal');
 await expect(page.getByTestId('sensor-landsat_tirs')).toBeVisible();await expect(page.getByTestId('scene-card')).toHaveCount(0);
});

test('TEST ONLY 세부 목록 API 실패는 원본 수집을 막지 않고 처리만 보류',async({page})=>{
 await page.route('**/api/analysis/catalog',r=>r.fulfill({status:503,json:{detail:'TEST ONLY catalog failure'}}));
 await setup(page,'vegetation',null,'나무 상태를 보고 싶어');await searchProduct(page,'s2_msi');await enter(page);
 await expect(panel(page)).toContainText('세부 분석 목록을 불러오지 못했습니다.');await expect(panel(page).getByRole('radio')).toHaveCount(0);
 await expect(page.getByRole('button',{name:'두 날짜 NDVI 작업 열기',exact:true})).toHaveCount(0);
 await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();
 await expect(page.getByRole('region',{name:'현재 작업 요약'}).getByRole('button',{name:'원본 다운로드',exact:true})).toBeEnabled();
});
