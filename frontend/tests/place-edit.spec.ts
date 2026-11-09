import {test,expect} from './runtime';
import {configs,input,interpretation,region,chooseLocation,coordinates,map} from './ai-primary-fixtures';
test('TEST ONLY confirmed place can be replaced and cleared without changing AOI or calling AI',async({page})=>{
 await configs(page);let ai=0,lookups=0;
 await page.route('**/api/request/interpret',r=>{ai++;return r.fulfill({json:interpretation()});});
 await page.route('**/api/places/search',r=>{lookups++;return r.fulfill({json:region(r.request().postDataJSON().place!=='서울')});});
 await page.goto('/');await input(page);await chooseLocation(page);await coordinates(page,[128.28865,36.07461,128.39985,36.16453]);
 const bbox=await map(page).getAttribute('data-aoi-bbox');const before=lookups;
 const place=page.getByLabel('분석 장소',{exact:true});await expect(place).toBeEditable();await place.fill('서울');await expect(place).toHaveValue('서울');
 await expect(page.getByText('입력한 장소는 아직 확인 전입니다.',{exact:false})).toBeVisible();expect(lookups).toBe(before);expect(ai).toBe(1);
 await page.getByRole('button',{name:'장소 찾기',exact:true}).click();await chooseLocation(page,'서울특별시');await expect(map(page)).toHaveAttribute('data-aoi-bbox',bbox!);expect(ai).toBe(1);
 await place.fill('');await expect(place).toHaveValue('');await expect(page.getByRole('button',{name:'장소 찾기',exact:true})).toBeDisabled();await expect(map(page)).toHaveAttribute('data-aoi-bbox',bbox!);
 await place.fill('라스베이거스');await expect(place).toHaveValue('라스베이거스');expect(ai).toBe(1);expect(lookups).toBe(before+1);
});
