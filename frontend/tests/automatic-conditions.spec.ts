import {test,expect} from './runtime';
import {fixture} from './fixtures';
import {configs,input,interpretation,region,map,coordinates,jejuMeta,seoulMeta,chooseLocation} from './ai-primary-fixtures';

test('TEST ONLY AI 전체 문장→축약 날짜·목적·제주 카메라·수동 AOI→같은 명시 검색 요청',async({page})=>{
 let ai=0,geo=0,search=0;
 await configs(page);
 await page.route('**/api/request/interpret',r=>{ai++;expect(r.request().postDataJSON()).toMatchObject({interpretation_mode:'ai',resolve_conditions:true});return r.fulfill({json:interpretation()});});
 await page.route('**/api/places/search',r=>{geo++;expect(r.request().postDataJSON()).toEqual({place:'제주도',kind:'administrative',radius_m:null});return r.fulfill({json:region(true)});});
 await page.route('**/api/search',r=>{search++;return r.fulfill({json:fixture('thermal',0)});});
 await page.goto('/');await input(page);
 await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-15');await expect(page.getByLabel('종료일',{exact:true})).toHaveValue('2025-08-30');
 await expect(page.getByLabel('목적 직접 선택',{exact:false})).toHaveValue('thermal');await chooseLocation(page);await expect(page.getByLabel('분석 장소',{exact:true})).toHaveValue('제주특별자치도');
 await expect(map(page)).toHaveAttribute('data-aoi-bbox','null');await coordinates(page,jejuMeta.bbox);await expect(map(page)).toHaveAttribute('data-aoi-confirmed','true');
 for(const [i,l] of ['서쪽 경도','남쪽 위도','동쪽 경도','북쪽 위도'].entries())await expect(page.getByLabel(l,{exact:true})).toHaveValue(String(jejuMeta.bbox[i]));
 expect(ai).toBe(1);expect(geo).toBe(1);expect(search).toBe(0);await expect(page.getByRole('button',{name:'AI로 문장 해석',exact:true})).toHaveCount(0);
 const response=page.waitForResponse(r=>r.url().endsWith('/api/search'));await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
 expect((await response).request().postDataJSON()).toMatchObject({purpose_type:'thermal',bbox:jejuMeta.bbox,start_date:'2025-08-15',end_date:'2025-08-30'});expect(search).toBe(1);
});

test('TEST ONLY 서울→제주 새 해석 중 서울 수동 bbox 유지·검색 차단·최신 후보 명시 선택',async({page})=>{
 await configs(page);let release!:()=>void;const held=new Promise<void>(r=>release=r);
 await page.route('**/api/request/interpret',r=>r.fulfill({json:interpretation(r.request().postDataJSON().purpose.includes('서울')?'서울시':'제주도')}));
 await page.route('**/api/places/search',async r=>{const jeju=r.request().postDataJSON().place==='제주도';if(jeju)await held;await r.fulfill({json:region(jeju)}).catch(()=>{});});
 await page.goto('/');await input(page,'2025년 8/15~8/30 서울시 지표면 온도');await chooseLocation(page,'서울특별시');await coordinates(page,seoulMeta.bbox);
 await input(page);await expect(map(page)).toHaveAttribute('data-aoi-bbox',JSON.stringify(seoulMeta.bbox));await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();
 release();await chooseLocation(page);await expect(map(page)).toHaveAttribute('data-aoi-bbox',JSON.stringify(seoulMeta.bbox));await expect(map(page)).toHaveAttribute('data-camera-place','TEST_ONLY_JEJU');await expect(page.getByLabel('분석 장소',{exact:true})).toHaveValue('제주특별자치도');
});

test('TEST ONLY 늦은 AI 응답에도 수동 날짜·AOI 보호·유지 또는 문장에서 다시 적용',async({page})=>{
 await configs(page);let release!:()=>void;const held=new Promise<void>(r=>release=r);let entered=false;
 await page.route('**/api/request/interpret',async r=>{entered=true;await held;await r.fulfill({json:interpretation()}).catch(()=>{});});
 await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));await page.goto('/');await input(page);await expect.poll(()=>entered).toBe(true);
 await page.getByLabel('시작일',{exact:true}).fill('2025-08-16');await coordinates(page,[126.7,36.4,126.71,36.41]);release();await chooseLocation(page);
 await expect(page.getByRole('button',{name:'문장에서 다시 적용',exact:true})).toBeVisible();await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-16');
 await expect(map(page)).toHaveAttribute('data-aoi-bbox','[126.7,36.4,126.71,36.41]');await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeDisabled();
 await page.getByRole('button',{name:'직접 수정값 유지',exact:true}).click();await expect(page.getByRole('button',{name:'위성영상 검색',exact:false})).toBeEnabled();
 await page.getByLabel('시작일',{exact:true}).fill('2025-08-17');await page.getByRole('button',{name:'문장에서 다시 적용',exact:true}).click();await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-15');await expect(map(page)).toHaveAttribute('data-aoi-bbox','[126.7,36.4,126.71,36.41]');
});

test('TEST ONLY IME 중 AI 없음·안정화 후 자동·blur 중복 억제·동일 문장 캐시',async({page})=>{
 await configs(page);let calls=0;await page.route('**/api/request/interpret',r=>{calls++;return r.fulfill({json:interpretation()});});await page.route('**/api/places/search',r=>r.fulfill({json:region(true)}));await page.goto('/');const field=page.getByLabel('분석 목적',{exact:true});
 await field.dispatchEvent('compositionstart');await field.fill('2025년 8/15~8/30 제주도 지표면 온도');await page.waitForTimeout(1400);expect(calls).toBe(0);await field.dispatchEvent('compositionend');
 await expect.poll(()=>calls).toBe(1);await field.blur();await page.getByLabel('시작일',{exact:true}).focus();await field.focus();await field.blur();expect(calls).toBe(1);
 await field.fill('');await field.fill('2025년 8/15~8/30 제주도 지표면 온도');await field.blur();await expect(page.getByLabel('시작일',{exact:true})).toHaveValue('2025-08-15');expect(calls).toBe(1);
});
