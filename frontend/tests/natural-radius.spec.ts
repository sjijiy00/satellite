import {test,expect} from './runtime';
import {configs,input,interpretation} from './ai-primary-fixtures';
for(const manual of [false,true])test(`TEST ONLY radius autofill preserves manual=${manual}`,async({page})=>{
 await configs(page);
 const p=interpretation('TEST place');p.condition_proposals.extraction!.places![0].spatial_scope='radius';
 p.condition_proposals.extraction!.places![0].radius_m=1000;
 await page.route('**/api/request/interpret',r=>r.fulfill({json:p}));
 await page.route('**/api/places/search',r=>r.fulfill({json:{status:'resolved',id:'TEST',name:'TEST place',center:[126.7,36.4],extent:{bbox:[126.69,36.39,126.71,36.41],radius_m:1000}}}));
 await page.goto('/');await input(page);
 await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue('126.69');
 await expect(page.getByTestId('coord-0-origin')).toHaveText('자동 설정');
 if(manual){
  await page.getByLabel('서쪽 경도',{exact:true}).fill('126.68');
  await input(page,'새 문장 TEST place 반경 1000m');
  await expect(page.getByTestId('automatic-conditions')).toContainText('위치 확인 완료');
  await expect(page.getByLabel('서쪽 경도',{exact:true})).toHaveValue('126.68');
 }
});
