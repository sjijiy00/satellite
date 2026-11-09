import {test,expect} from './runtime';
import {configs,input,interpretation,region,map,seoulMeta,jejuMeta,chooseLocation,coordinates} from './ai-primary-fixtures';
for(const status of ['no_results','failed','not_configured','limited','timeout'])test('TEST ONLY 위치 '+status+'는 자동 bbox 생성 없음',async({page})=>{
 await configs(page);await page.route('**/api/request/interpret',r=>r.fulfill({json:interpretation()}));await page.route('**/api/places/search',r=>r.fulfill({json:{status,mentioned_text:'제주도',message:'TEST ONLY '+status}}));await page.goto('/');await input(page);await expect(page.getByTestId('condition-stages')).toContainText(status==='no_results'?'검색 0건':status==='failed'?'위치 검색 실패':status==='not_configured'?'위치 서비스 미설정':status==='limited'?'요청 제한':'시간 초과');await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();
});

test('TEST ONLY 동명 후보는 상위 지역 선택 후 카메라만 이동',async({page})=>{
 await configs(page);await page.route('**/api/request/interpret',r=>r.fulfill({json:interpretation('중구')}));const a=region(),b=region(true);await page.route('**/api/places/search',r=>r.fulfill({json:{status:'ambiguous',mentioned_text:'중구',candidates:[{...a,name:'서울특별시 중구',parent:'서울특별시'},{...b,name:'제주 후보 TEST ONLY',parent:'제주특별자치도'}]}}));await page.goto('/');await input(page,'2025년 8월 중구 지표면 온도');await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');await page.getByRole('button',{name:'서울특별시 중구',exact:true}).click();await expect(map(page)).toHaveAttribute('data-camera-place','TEST_ONLY_SEOUL');await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');
});

test('TEST ONLY 미지원 행정경계는 점 지도 이동만·임의 bbox 없음',async({page})=>{
 await configs(page);const point={...region(),name:'경기도 연천군',boundary:{status:'unsupported',message:'TEST ONLY 경계 미등록'},center:[127.07,38.09]};await page.route('**/api/request/interpret',r=>r.fulfill({json:interpretation('연천군')}));await page.route('**/api/places/search',r=>r.fulfill({json:point}));await page.goto('/');await input(page,'2025년 8월 연천군 지표면 온도');await chooseLocation(page,'경기도 연천군');await expect(page.getByLabel('분석 장소',{exact:true})).toHaveValue('경기도 연천군');await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');await expect(map(page)).toHaveAttribute('data-camera-place',point.id);
});

test('TEST ONLY 늦은 서울 위치 응답이 제주 좌표를 덮지 않음',async({page})=>{
 await configs(page);let release!:()=>void;const held=new Promise<void>(r=>release=r);let waiting=false;
 await page.route('**/api/request/interpret',r=>r.fulfill({json:interpretation(r.request().postDataJSON().purpose.includes('서울')?'서울시':'제주도')}));
 await page.route('**/api/places/search',async r=>{const old=r.request().postDataJSON().place==='서울시';if(old){waiting=true;await held;}await r.fulfill({json:region(!old)}).catch(()=>{});});await page.goto('/');await input(page,'2025년 8월 서울시 지표면 온도');await expect.poll(()=>waiting).toBe(true);await input(page);await chooseLocation(page);await coordinates(page,jejuMeta.bbox);release();await expect(map(page)).toHaveAttribute('data-aoi-bbox',JSON.stringify(jejuMeta.bbox));
});

test('TEST ONLY 장소+명시 거리도 자동 bbox 없음·직접 AOI·모바일·큰 AOI 제한 구분·지도 핸들',async({page})=>{
 await configs(page);const data=interpretation('제주공항');data.condition_proposals.extraction!.places=[{text:'제주공항',ambiguous:false,basis:'explicit',kind:'place',spatial_scope:'radius',radius_m:1000}];const b=[126.48,33.49,126.51,33.52];
 await page.route('**/api/request/interpret',r=>r.fulfill({json:data}));await page.route('**/api/places/search',r=>{expect(r.request().postDataJSON()).toEqual({place:'제주공항',kind:'place',radius_m:1000});return r.fulfill({json:{...region(true),boundary:{status:'unsupported',message:'TEST ONLY 점'},extent:{bbox:b,radius_m:1000,scope:'TEST ONLY 명시 거리',method:'TEST ONLY',polygon_clipping:false}}});});
 await page.setViewportSize({width:390,height:844});await page.goto('/');await input(page,'2025년 8월 제주공항 주변1km 지표면 온도');await chooseLocation(page);await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');await coordinates(page,b);await expect(page.locator('.aoi-corner')).toHaveCount(4);expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);await page.getByTestId('automatic-conditions').screenshot({path:'test-results/ai-primary-mobile.png'});
});
