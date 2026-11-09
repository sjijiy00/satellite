import {test,expect} from './runtime';
import {configs,input,interpretation,region,map,jejuMeta,chooseLocation,coordinates} from './ai-primary-fixtures';

test('TEST ONLY AI 추론 조건은 확인 전 확정하지 않고 명시 적용으로만 교체',async({page})=>{
 await configs(page);const data=interpretation();data.condition_proposals.fields!.resolution_m={value:10,evidence:'정밀하게',basis:'inferred'};
 await page.route('**/api/request/interpret',r=>r.fulfill({json:data}));await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));await page.goto('/');await input(page);
 await expect(page.getByRole('button',{name:'문장에서 다시 적용',exact:true})).toBeVisible();await page.getByText('관측 조건 선택 (선택 입력)',{exact:true}).click();await expect(page.getByLabel('요청 해상도 상한 (m)',{exact:true})).toHaveValue('');
 await page.getByRole('button',{name:'문장에서 다시 적용',exact:true}).click();await expect(page.getByLabel('요청 해상도 상한 (m)',{exact:true})).toHaveValue('10');
});

test('TEST ONLY 거리 없는 특정 장소는 자동 박스 없음·직접 거리 확인 후 범위',async({page})=>{
 await configs(page);const data=interpretation('제주공항');data.condition_proposals.extraction!.places=[{text:'제주공항',kind:'place',basis:'explicit',ambiguous:false,spatial_scope:'unspecified',radius_m:null}];
 await page.route('**/api/request/interpret',r=>r.fulfill({json:data}));const b=[126.48,33.49,126.51,33.52];await page.route('**/api/places/search',r=>{const radius=r.request().postDataJSON().radius_m;return r.fulfill({json:{...region(true),boundary:{status:'unsupported',message:'TEST ONLY 점 좌표'},...(radius?{extent:{bbox:b,radius_m:radius,scope:'TEST ONLY',method:'TEST ONLY'}}:{})}});});
 await page.goto('/');await input(page,'2025년 8월 제주공항 지표면 온도');await chooseLocation(page);await expect(page.getByLabel('분석 장소',{exact:true})).not.toHaveValue('');await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');
 await page.getByText('위치 재시도·직접 지명·거리 지정',{exact:true}).click();await page.getByLabel('장소 주변 거리 (m)',{exact:true}).fill('1000');await page.getByRole('button',{name:'확인한 장소에 거리 적용',exact:true}).click();await expect(page.getByRole('button',{name:'제주특별자치도',exact:true})).toBeVisible();await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');await coordinates(page,b);await expect(map(page)).toHaveAttribute('data-aoi-bbox',JSON.stringify(b));
});

test('TEST ONLY 명시하지 않은 행정구역 공간 범위는 재확인',async({page})=>{
 await configs(page);const data=interpretation();data.condition_proposals.extraction!.places![0].spatial_scope='unspecified';await page.route('**/api/request/interpret',r=>r.fulfill({json:data}));await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));await page.goto('/');await input(page,'2025년 8월 제주도 일대 지표면 온도');
 await chooseLocation(page);await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue('');
});

test('TEST ONLY AI 취소와 늦은 응답·실패 뒤 명시 재시도',async({page})=>{
 await configs(page);let release!:()=>void;const held=new Promise<void>(r=>release=r);let called=false,calls=0;
 await page.route('**/api/request/interpret',async r=>{calls++;called=true;if(calls===1)await held;await r.fulfill({json:interpretation()}).catch(()=>{});});await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));await page.goto('/');await input(page);await expect.poll(()=>called).toBe(true);await page.getByRole('button',{name:'해석 취소',exact:true}).click();release();await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('');await expect(page.getByTestId('automatic-conditions')).toContainText('취소');await page.getByRole('button',{name:'AI 해석 재시도',exact:true}).click();await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-15');expect(calls).toBe(2);
});

test('TEST ONLY 자동 박스 꼭짓점 드래그→수동 수정·좌표·확정 지도 일치',async({page})=>{
 await configs(page);await page.route('**/api/request/interpret',r=>r.fulfill({json:interpretation()}));await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));await page.goto('/');await input(page);await chooseLocation(page);await coordinates(page,jejuMeta.bbox);await expect(map(page)).toHaveAttribute('data-aoi-bbox',JSON.stringify(jejuMeta.bbox));await expect(map(page)).toHaveAttribute('data-aoi-confirmed','true');await map(page).scrollIntoViewIfNeeded();await page.waitForTimeout(700);
 const corner=page.locator('.aoi-corner').first(),pos=await corner.boundingBox();if(!pos)throw new Error('map handle unavailable');await page.mouse.move(pos.x+pos.width/2,pos.y+pos.height/2);await page.mouse.down();await page.mouse.move(pos.x+pos.width/2+35,pos.y+pos.height/2-25,{steps:8});await page.mouse.up();
 await expect(map(page)).not.toHaveAttribute('data-aoi-bbox',JSON.stringify(jejuMeta.bbox));await expect(page.getByTestId('coord-0-origin')).toHaveText('직접 수정');await page.getByRole('button',{name:'분석 AOI 확정',exact:true}).click();
 const b=JSON.parse((await map(page).getAttribute('data-aoi-bbox'))!);expect(Number(await page.getByLabel('서쪽 경도',{exact:true}).inputValue())).toBe(b[0]);
});
