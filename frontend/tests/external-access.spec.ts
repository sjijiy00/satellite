import {test,expect,openBandPanel} from './runtime';
import {fixture} from './fixtures';

test('연결된 SAR는 앱 검색 가능·원본 인증과 처리 지원을 별도로 안내',async({page})=>{
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
  await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('flood');
  const card=page.getByTestId('sensor-s1_csar');
  await expect(card.getByRole('button',{name:'이 제품 선택'})).toBeEnabled();
  await expect(card).toContainText('copernicus');
  await expect(card).toContainText('래스터 처리·픽셀 QA 미지원');
  await expect(card.getByTestId('sensor-availability')).toContainText('미검색');
});

test('제한된 Asset은 같은 Item·밴드의 다른 직접 링크와 공식 포털을 구분',async({page})=>{
  const data=fixture('vegetation',1),scene=data.items[0];
  scene.download_assets!.push({key:'blue',title:'Blue COG',href:'https://example.test/blue.tif',media_type:'image/tiff',direct_url:'https://example.test/blue.tif',requester_pays:false,access_note:'TEST ONLY',common_names:['blue'],roles:[]});
  scene.download_assets!.push({key:'blue-jp2',title:'Blue JP2',href:'s3://example.test/blue.jp2',media_type:'image/jp2',direct_url:null,requester_pays:true,access_note:'AWS 인증 및 요청자 비용 동의 필요',common_names:['blue'],roles:[]});
  await page.route('**/api/search',route=>route.fulfill({json:data}));
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
  await page.getByLabel('목적 직접 선택',{exact:false}).selectOption('vegetation');
  await page.getByRole('button',{name:'충남 예시 영역'}).click();
  await page.getByRole('button',{name:'좌표 적용',exact:true}).click();
  await page.getByRole('button',{name:'위성영상 검색',exact:false}).click();
  const card=page.getByTestId('primary-results').getByTestId('scene-card').first();
  await openBandPanel(card);await card.getByTestId('band-blue-jp2').check();
  const restricted=card.locator('.selected-links details').filter({hasText:'blue-jp2'});
  await restricted.locator('summary').click();
  await expect(restricted.getByRole('link',{name:/blue 직접 링크 열기/})).toHaveAttribute('href','https://example.test/blue.tif');
  await expect(restricted.getByRole('link',{name:/Copernicus Browser/})).toHaveAttribute('href','https://dataspace.copernicus.eu/browser/');
  await expect(restricted).toContainText(scene.id);
  await expect(card.getByTestId('band-blue-jp2')).toBeChecked();
  await expect(card.getByTestId('band-blue-jp2').locator('..')).toContainText('같은 밴드의 다른 형식 링크 있음');
});
