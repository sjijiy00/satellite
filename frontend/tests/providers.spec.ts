import {test,expect,searchProduct,openCollectionComparison} from './runtime';
import {fixture,status} from './fixtures';
import {sceneKey,type Scene} from '../src/lib/types';

function providerFixture(){
  const data=fixture('vegetation',1);
  const base=data.items[0];
  const viirs:Scene={...structuredClone(base),provider_id:'nasa-cmr',provider:'NASA CMR / LP DAAC',
    collection:'viirs-vnp09ga-002',platform:'suomi-npp',instruments:['viirs'],processing_level:'L2G',
    product_type:'VNP09GA.002',native_resolution:'VIIRS 375 / 750 m',output_grid:'SIN 500 m / 1 km',
    end_datetime:'2025-07-01T23:59:59Z',scene_cloud_cover:null,resolution_m:[],
    support:{search:true,processing:'검색·메타데이터만 지원; 앱 내 픽셀 처리 미지원',file_access:'authentication_required',access_verified:false},
    download_assets:[{key:'granule-0',title:'TEST ONLY HDF5',href:'https://example.test/TEST.h5',direct_url:null,
       media_type:'application/x-hdf5',requester_pays:false,authentication_required:true,access_note:'Earthdata Login 인증 필요',common_names:[],roles:['data']}],
    purpose_plan:{...base.purpose_plan!,metadata_only:true,profile_id:'viirs_sr',product_status:'met',group:'other',
       analysis_keys:[],default_keys:['granule-0'],visual_keys:[],visual_mapping:{},analysis:'검색 후보 · 픽셀 미검사',visual_title:'제공처 미리보기',visual_missing:[]}};
  data.items=[{...base,provider_id:'earth-search'},viirs];
  data.returned=2;data.outcome='partial';data.collection_statuses=[{...status('sentinel-2-l2a','success',1),provider_id:'earth-search'},
    {...status(viirs.collection,'success',1),provider_id:'nasa-cmr'},
    {...status('sentinel-1-grd','failed'),provider_id:'copernicus'}];
  return data;
}

for(const width of [1440,390])test(`다중 제공처 · 동일 ID 구별·접근/QA/처리 상태·모바일 ${width}`,async({page})=>{
  await page.setViewportSize({width,height:900});
  const data=providerFixture();
  await page.route('**/api/search',r=>r.fulfill({json:data}));
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  await page.getByRole('button',{name:'충남 예시 영역'}).click();await searchProduct(page,'s2_msi');
  await expect(page.getByTestId('search-status')).toContainText('부분 검색');
  await expect(page.getByTestId('search-status')).toContainText('copernicus / sentinel-1-grd');
  const card=page.getByTestId('other-results').getByTestId('scene-card').first();
  await card.getByRole('button',{name:'지도에서 선택'}).click();
  await expect(page.getByTestId('map-selected-scene')).toHaveText(sceneKey(data.items[1]));
  await expect(page.getByTestId('selected-scene-detail')).toContainText('suomi-npp');
  await expect(card.getByTestId('scene-provenance')).toContainText('인증 필요');
  await expect(card.getByTestId('scene-provenance')).toContainText('픽셀 처리 미지원');
  await expect(card.getByTestId('scene-provenance')).toContainText('500 m / 1 km');
  await card.locator('.asset-downloads > summary').click();
  await expect(card.getByTestId('band-granule-0')).toBeChecked();
  await expect(card.getByRole('button',{name:'선택 링크 목록 저장 (.txt)'})).toBeDisabled();
  await expect(card.locator('.download-link')).toHaveCount(0);
  await expect(page.getByRole('button',{name:'선택 영상 실제 AOI 품질 검사'})).toHaveCount(0);
  const comparison=await openCollectionComparison(page);await comparison.getByLabel('수집 비교 목적',{exact:true}).selectOption('temporal');
  await comparison.getByLabel('수집 비교 영상 2',{exact:true}).selectOption(sceneKey(data.items[1]));
  await expect(comparison.getByRole('button',{name:'두 영상 조건 검사',exact:true})).toHaveCount(0);
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth)).toBe(true);
  await page.getByRole('region',{name:'검색 결과',exact:true}).screenshot({path:`test-results/providers-${width}.png`});
});

test('실제 공개 다중 제공처 검색: 동일 AOI·기간, SAR·광학·CMR를 한 응답에서 확인',async({page})=>{
  test.skip(process.env.LIVE_STAC!=='1','실제 다중 제공처 검색은 LIVE_STAC=1 별도 실행');
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  for(const [label,value] of [['서쪽 경도','126.7'],['남쪽 위도','36.4'],['동쪽 경도','126.71'],['북쪽 위도','36.41']])
    await page.getByLabel(label,{exact:true}).fill(value);
  await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
  await page.getByLabel('시작일',{exact:true}).fill('2025-07-20');await page.getByLabel('종료일',{exact:true}).fill('2025-07-26');
  await page.getByLabel('위성 선택',{exact:true}).selectOption('manual');
  await page.getByLabel('Sentinel-1 GRD · Copernicus',{exact:true}).check();
  await page.getByLabel('Suomi NPP VIIRS VNP09GA · NASA CMR',{exact:true}).check();
  const response=page.waitForResponse(r=>r.url().endsWith('/api/search'));
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  const r=await response,data=await r.json();expect(r.status()).toBe(200);
  expect([...new Set(data.items.map((s:Scene)=>s.provider_id))].sort()).toEqual(['copernicus','earth-search','nasa-cmr']);
  expect(data.query).toMatchObject({bbox:[126.7,36.4,126.71,36.41],start_date:'2025-07-20',end_date:'2025-07-26'});
  expect(data.items.every((s:Scene)=>s.datetime&&s.datetime.slice(0,10)>='2025-07-20'&&s.datetime.slice(0,10)<='2025-07-26')).toBe(true);
  await expect(page.getByTestId('footprint-count')).toHaveText(`${data.returned}개 범위`);
  const viirs=page.getByTestId('scene-card').filter({hasText:'VNP09GA.002'}).first();
  await expect(viirs).toContainText('인증 필요');
  expect(new Set(data.items.map(sceneKey)).size).toBe(data.returned);
});
