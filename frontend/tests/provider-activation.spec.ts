// Current 3000 -> 8000 application, real public metadata only. No AI/pixel/download calls.
import {test,expect,type Page} from './runtime';
import type {Scene} from '../src/lib/types';
import {mkdirSync,writeFileSync} from 'node:fs';
import {fixture} from './fixtures';

const choices=[
  {purpose:'flood',profile:'s1_csar',collection:'sentinel-1-grd',provider:'copernicus',label:'Sentinel-1 GRD · Copernicus'},
  {purpose:'vegetation',profile:'viirs_sr',collection:'viirs-vnp09ga-002',provider:'nasa-cmr',label:'Suomi NPP VIIRS VNP09GA · NASA CMR'},
  {purpose:'vegetation',profile:'s2_msi',collection:'sentinel-2-l2a',provider:'earth-search',label:'Sentinel-2 Level-2A'},
] as const;
async function conditions(page:Page,purpose:string){
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
  await page.getByLabel('목적 직접 선택',{exact:false}).selectOption(purpose);
  await page.getByLabel('시작일',{exact:true}).fill('2025-07-20');
  await page.getByLabel('종료일',{exact:true}).fill('2025-07-26');
  for(const [label,value] of [['서쪽 경도','126.7'],['남쪽 위도','36.4'],['동쪽 경도','126.71'],['북쪽 위도','36.41']])
    await page.getByLabel(label,{exact:true}).fill(value);
  await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
}

test('현재 실행 백엔드/프록시 catalog와 화면 제공처 옵션',async({page,request})=>{
  for(const url of [(process.env.E2E_API_BASE_URL||'http://127.0.0.1:8000')+'/catalog','/api/catalog']){
    const r=await request.get(url);expect(r.status()).toBe(200);
    const catalog=await r.json();
    expect(Object.keys(catalog.providers).sort()).toEqual(['copernicus','earth-search','nasa-cmr','noaa-nodd','planetary-computer']);
    expect(Object.keys(catalog.collections).sort()).toEqual(['hls-l30-002','hls-s30-002','landsat-c2-l2','noaa-viirs-ndvi-cdr','pc-landsat-c2-l2','pc-sentinel-2-l2a','sentinel-1-grd','sentinel-2-l2a','viirs-vnp09ga-002']);
  }
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('위성 선택',{exact:true}).selectOption('manual');
  for(const choice of choices)await expect(page.getByLabel(choice.label,{exact:true})).toBeEnabled();
});

test('TEST ONLY 같은 수동 모드에서 체크박스 수정도 이전 추천 카드를 해제',async({page})=>{
  await page.route('**/api/search',r=>r.fulfill({json:fixture('vegetation',0)}));
  await conditions(page,'vegetation');
  await page.getByLabel('위성 선택',{exact:true}).selectOption('manual');
  const card=page.getByTestId('sensor-s2_msi').getByRole('button',{name:/이 제품 선택|선택한 제품/});
  await card.click();
  await expect(page.getByLabel('Sentinel-2 Level-2A',{exact:true})).toBeChecked();
  await expect(page.getByLabel('Landsat Collection 2 Level-2',{exact:true})).not.toBeChecked();
  await page.getByLabel('Sentinel-2 Level-2A',{exact:true}).uncheck();
  await page.getByLabel(choices[1].label,{exact:true}).check();
  await expect(card).toHaveAttribute('aria-pressed','false');
  await expect(page.getByTestId('effective-search-selection')).toContainText('수동 선택 적용');
  const response=page.waitForResponse(r=>r.url().endsWith('/api/search'));
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  expect((await response).request().postDataJSON()).toMatchObject({recommendation_id:null,collections:['viirs-vnp09ga-002']});
});

for(const choice of choices)for(const route of ['card','manual'] as const)
test(`현재 웹 실제 검색 ${choice.profile} / ${route}`,async({page})=>{
  test.skip(process.env.LIVE_STAC!=='1','공개 제공처 실제 검색은 LIVE_STAC=1 별도 실행');
  await conditions(page,choice.purpose);
  if(route==='card'){
    // A product card must replace an earlier, conflicting manual selection visibly.
    await page.getByLabel('위성 선택',{exact:true}).selectOption('manual');
    await page.getByTestId(`sensor-${choice.profile}`).getByRole('button',{name:'이 제품 선택'}).click();
  }else{
    // A later manual choice must release the previously selected product card.
    await page.getByTestId(`sensor-${choice.profile}`).getByRole('button',{name:'이 제품 선택'}).click();
    await page.getByLabel('위성 선택',{exact:true}).selectOption('manual');
    for(const name of ['Sentinel-2 Level-2A','Landsat Collection 2 Level-2',...choices.slice(0,2).map(c=>c.label)])
      await page.getByLabel(name,{exact:true}).uncheck();
    await page.getByLabel(choice.label,{exact:true}).check();
  }
  await expect(page.getByTestId('effective-search-selection')).toContainText(choice.collection);
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/search'));
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  const response=await responsePromise,sent=response.request().postDataJSON(),data=await response.json();
  expect(sent).toMatchObject({purpose_type:choice.purpose,bbox:[126.7,36.4,126.71,36.41],
    start_date:'2025-07-20',end_date:'2025-07-26',collections:[choice.collection],recommendation_id:route==='card'?choice.profile:null});
  // Store only bounded provenance fields, never Asset URLs or redirect/signature values.
  const evidence={profile:choice.profile,route,http_status:response.status(),sent,returned:data.returned,
    outcome:data.outcome,truncated:data.truncated,collections:data.collections,
    statuses:data.collection_statuses,items:(data.items||[]).map((s:Scene)=>({id:s.id,provider_id:s.provider_id,
      collection:s.collection,datetime:s.datetime,end_datetime:s.end_datetime,overlap_percent:s.overlap_percent,
      processing_level:s.processing_level,product_type:s.product_type,support:s.support,pixel_quality:s.pixel_quality,
      assets:s.download_assets?.map(a=>({key:a.key,authentication_required:a.authentication_required,
        direct_link_present:!!a.direct_url,access_verified:a.access_verified,requester_pays:a.requester_pays}))}))};
  mkdirSync('test-results',{recursive:true});
  const evidenceText=JSON.stringify(evidence,null,2);
  writeFileSync(`test-results/activation-${choice.profile}-${route}-${Date.now()}.json`,evidenceText);
  writeFileSync(`test-results/activation-${choice.profile}-${route}.json`,evidenceText);
  console.log(JSON.stringify({profile:choice.profile,route,status:response.status(),outcome:data.outcome,returned:data.returned,truncated:data.truncated}));
  expect(response.status()).toBe(200);
  expect(data.collections).toEqual([choice.collection]);
  expect(data.collection_statuses).toHaveLength(1);
  expect(data.collection_statuses[0].provider_id).toBe(choice.provider);
  expect(['success','empty']).toContain(data.outcome);
  for(const s of data.items as Scene[]){
    expect(s.provider_id).toBe(choice.provider);expect(s.collection).toBe(choice.collection);
    expect(s.datetime!.slice(0,10)>='2025-07-20'&&s.datetime!.slice(0,10)<='2025-07-26').toBe(true);
    expect(s.overlap_percent===null||(s.overlap_percent>=0&&s.overlap_percent<=100)).toBe(true);
    if(choice.profile!=='s2_msi')expect(s.download_assets?.every(a=>a.authentication_required&&!a.direct_url)).toBe(true);
  }
  await expect(page.getByTestId('applied-search-selection')).toContainText(choice.collection);
  if(data.returned>0)await expect(page.getByTestId('selected-scene-detail')).toBeVisible();
  if(choice.profile==='s1_csar'&&data.returned>0){
    const provenance=page.getByTestId('scene-card').first().getByTestId('scene-provenance');
    await expect(provenance).toContainText('관측 시작·종료 시각');
    await expect(provenance).not.toContainText('일별 집계');
  }
  if(route==='card')await page.getByRole('region',{name:'검색 결과',exact:true}).screenshot({path:`test-results/activation-${choice.profile}.png`});
});
