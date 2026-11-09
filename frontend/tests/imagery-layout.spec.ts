import {test,expect,prepareProcessing,openComparison,confirmDetail,type Page} from './runtime';
import {fixture,collections} from './fixtures';
const panel=(page:Page)=>page.getByRole('region',{name:'날짜별 영상 탐색과 레이어'});
const png='iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGNoclu1BQAE5wIngLnp3wAAAABJRU5ErkJggg==';
async function setup(page:Page,modify?:(data:ReturnType<typeof fixture>)=>void,small=false){
 let data:ReturnType<typeof fixture>|undefined;
 await page.route('**/api/search',r=>{const d=fixture('vegetation',3);d.query.bbox=r.request().postDataJSON().bbox;modify?.(d);data=d;return r.fulfill({json:d});});
 await page.route('**/api/media/session',r=>r.fulfill({json:{ready:true,session_generation:'TEST_ONLY_IMAGES'}}));
 await page.route('**/api/media/inspect',r=>{const ref=r.request().postDataJSON(),scene=data?.items.find(s=>s.id===ref.id&&s.collection===ref.collection);return r.fulfill({json:{reference:ref,assets:[],preview:scene?.thumbnail?{status:'available',url:'/api/media/previews/'+(scene.thumbnail.includes('missing.png')?'TEST_ONLY_MISSING':'TEST_ONLY_IMAGE'),message:'TEST ONLY provider preview'}:{status:'missing_asset',message:'TEST ONLY 이 영상에는 제공처 원본 미리보기가 없습니다'}}});});
 await page.route('**/api/media/previews/TEST_ONLY_IMAGE',r=>r.fulfill({contentType:'image/png',body:Buffer.from(png,'base64')}));
 await page.route('**/api/media/previews/TEST_ONLY_MISSING',r=>r.abort());
 await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
 if(small){for(const [i,label] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await page.getByLabel(label,{exact:true}).fill(String([126.7,36.4,126.71,36.41][i]));await page.getByRole('button',{name:'좌표 적용',exact:true}).click();}else await page.getByRole('button',{name:'충남 예시 영역',exact:true}).click();await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();await expect(panel(page)).toBeVisible();
}
async function alignment(page:Page){
 const rows=await panel(page).locator('.imagery-layer').evaluateAll(labels=>labels.map(label=>{
  const input=label.querySelector('input')!,name=label.querySelector('.imagery-layer-name')!,style=getComputedStyle(input),range=document.createRange();range.selectNodeContents(name);
  const a=input.getBoundingClientRect(),b=range.getClientRects()[0];
  return {width:a.width,height:a.height,shrink:style.flexShrink,gap:b.left-a.right,topDifference:Math.abs(b.top-a.top)};
 }));
 for(const row of rows){expect(row.width).toBe(16);expect(row.height).toBe(16);expect(row.shrink).toBe('0');expect(row.gap).toBeGreaterThanOrEqual(7);expect(row.gap).toBeLessThanOrEqual(11);expect(row.topDifference).toBeLessThanOrEqual(5);}
}

for(const width of [1440,390])test(`TEST ONLY ${width}px 선택 정보·체크박스 정렬·원본 ID 보존`,async({page})=>{
 await page.setViewportSize({width,height:1000});const id='TEST_ONLY_LONG_ITEM_'+ 'x'.repeat(180);
 await setup(page,d=>{d.items[0].id=id;});const explorer=panel(page),detail=explorer.getByTestId('selected-scene-detail');
 await expect(detail.locator('.imagery-scene-heading')).toContainText('sentinel-2b');await expect(detail.locator('time')).toHaveText('2025-07-01 02:00:00 UTC');await expect(detail.locator('.imagery-product')).toHaveText('제품 · S2MSI2A');
 await expect(detail.locator('.imagery-evidence code')).not.toBeVisible();await expect(detail.locator('.imagery-evidence code')).toHaveText(id);
 await expect(explorer.getByRole('checkbox',{name:'선택 영상 원본 미리보기',exact:true})).toBeDisabled();await expect(explorer.getByRole('checkbox',{name:'선택 영상 원본 미리보기',exact:true})).not.toBeChecked();
 await expect(explorer.getByRole('checkbox',{name:'실제 AOI 품질 마스크',exact:true})).toBeDisabled();await expect(explorer).toContainText('미검사');
 await alignment(page);
 const facts=await detail.locator('.imagery-facts>div').evaluateAll(rows=>rows.map(r=>({display:getComputedStyle(r).display,delta:Math.abs(r.querySelector('dt')!.getBoundingClientRect().left-r.querySelector('dd')!.getBoundingClientRect().left),align:getComputedStyle(r.querySelector('dd')!).textAlign})));
 for(const f of facts){expect(f.display).toBe('block');expect(f.delta).toBeLessThan(1);expect(f.align).toBe('left');}
 await expect(page.getByLabel('시작일',{exact:true})).toHaveCSS('width',await page.getByLabel('종료일',{exact:true}).evaluate(e=>getComputedStyle(e).width));
 expect(await page.getByLabel('서쪽 경도',{exact:true}).evaluate(e=>e.getBoundingClientRect().width)).toBeGreaterThan(80);
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await explorer.screenshot({path:`test-results/imagery-layout-${width}.png`});
 await detail.getByText('Item ID·추천 근거',{exact:true}).click();await expect(detail.locator('code')).toBeVisible();await expect(detail).toContainText('TEST GROUP');expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
 await explorer.getByRole('checkbox',{name:'실제 Item 촬영 범위',exact:true}).uncheck();await expect(page.getByTestId('footprint-count')).toHaveText('0개 범위');await explorer.getByRole('checkbox',{name:'실제 Item 촬영 범위',exact:true}).check();await expect(page.getByTestId('footprint-count')).toHaveText('6개 범위');
});

test('TEST ONLY 원본 미리보기 켜기/끄기·날짜 선택 뒤 미제공과 상태 보존',async({page})=>{
 await page.route('https://example.test/preview.png',r=>r.fulfill({contentType:'image/png',body:Buffer.from(png,'base64')}));
 await setup(page,d=>{d.items[0].thumbnail='https://example.test/preview.png';});const explorer=panel(page),preview=explorer.getByRole('checkbox',{name:'선택 영상 원본 미리보기',exact:true});
 await expect(preview).toBeEnabled();await expect(preview).toBeChecked();await expect(explorer.locator('.imagery-preview img')).toBeVisible();
 await preview.uncheck();await expect(explorer.locator('.imagery-preview')).toHaveCount(0);await expect(preview.locator('..')).toContainText('사용 가능');
 await preview.check();await expect(explorer.locator('.imagery-preview img')).toBeVisible();
 await explorer.getByRole('button',{name:/2025-07-02/}).click();await expect(preview).toBeDisabled();await expect(preview).not.toBeChecked();await expect(explorer).toContainText('이 영상에는 제공처 미리보기 후보가 없습니다');await expect(page.getByTestId('map-selected-scene')).toContainText('TEST_ONLY_1');
 await explorer.getByRole('button',{name:/2025-07-01/}).click();await expect(preview).toBeChecked();await explorer.locator('.imagery-preview').scrollIntoViewIfNeeded();await expect(explorer.locator('.imagery-preview img')).toBeVisible();
});

test('TEST ONLY 미리보기 접근 실패·누락 수치와 실제 AOI 검사 실패 구분',async({page})=>{
 await page.route('https://example.test/missing.png',r=>r.abort());
 await setup(page,d=>{Object.assign(d.items[0],{thumbnail:'https://example.test/missing.png',scene_cloud_cover:null,overlap_percent:null,pixel_quality:{status:'failed',message:'TEST ONLY AOI 검사 실패'}});});
 const explorer=panel(page),facts=explorer.locator('.imagery-facts');await expect(explorer).toContainText('미리보기 보관 기간 만료·접근 실패');await expect(explorer.locator('.imagery-preview img')).toHaveCount(0);
 await expect(facts.locator('div').filter({has:page.getByText('장면 전체 구름량',{exact:true})})).toContainText('미확인');await expect(facts.locator('div').filter({has:page.getByText('AOI 기하 중첩',{exact:true})})).toContainText('미확인');
 await expect(facts).toContainText('검사 실패·미확인');await expect(facts).toContainText('TEST ONLY AOI 검사 실패');await expect(explorer.getByRole('checkbox',{name:'실제 AOI 품질 마스크',exact:true})).toBeDisabled();
});

test('TEST ONLY 실제 상태/API 연결을 통한 QA·처리 레이어 켜기/끄기',async({page})=>{
 // Test-only raster overlays are explicit fixtures. The live A3/A4 regressions run separately.
 const overlay={png_base64:png,coordinates:[[126.7,36.5],[126.8,36.5],[126.8,36.4],[126.7,36.4]],label:'TEST ONLY QA',scene_ids:['TEST_ONLY_0'],source:'TEST ONLY'};
 const scene={id:'TEST_ONLY_0',datetime:'2025-07-01T02:00:00Z',status:'checked',valid_area_m2:850,valid_percent_aoi:85};
 await page.route('**/api/pixel-quality',r=>r.fulfill({json:{status:'checked',scenes:[scene],common_valid_area_m2:850,map_layers:{quality:[overlay],analysis:null}}}));
 await page.route('**/api/change-analysis',r=>r.fulfill({json:{status:'computed',scenes:[scene],map_layers:{quality:[overlay],analysis:{...overlay,label:'TEST ONLY 실제 NDVI',scene_ids:['TEST_ONLY_0','TEST_ONLY_1']}}}}));
 await setup(page,undefined,true);await openComparison(page);await page.getByLabel('비교 목적',{exact:true}).selectOption('temporal');
 await page.getByRole('button',{name:'작은 AOI 픽셀 진단',exact:true}).click();await expect(page.getByTestId('pixel-report')).toBeVisible();await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();const explorer=panel(page),quality=explorer.getByRole('checkbox',{name:'실제 AOI 품질 마스크',exact:true});
 await expect(quality).toBeEnabled();await expect(quality).toBeChecked();await expect(explorer.locator('.imagery-quality')).toContainText('85.00%');await expect(page.locator('.map-legend')).toContainText('실제 유효·제외 마스크');
 await quality.uncheck();await expect(page.locator('.map-legend')).not.toContainText('실제 유효·제외 마스크');await quality.check();
 await prepareProcessing(page);await confirmDetail(page,'vegetation_change');await page.getByRole('button',{name:'두 날짜 NDVI 계산',exact:true}).click();await expect(page.getByTestId('change-report')).toBeVisible();await page.getByRole('link',{name:'데이터 수집으로 돌아가기',exact:true}).click();const analysis=explorer.getByRole('checkbox',{name:'실제 처리 결과',exact:true});await expect(analysis).toBeEnabled();await expect(analysis).toBeChecked();
 await expect(page.locator('.map-legend')).toContainText('실제 NDVI');await analysis.uncheck();await expect(page.locator('.map-legend')).not.toContainText('실제 NDVI');await analysis.check();await alignment(page);
 await explorer.screenshot({path:'test-results/imagery-layout-available.png'});
});
