import {test,expect} from './runtime';

test('Pages 정적 export 직접 진입과 이동에서 RSC 파일 404 없음',async({page})=>{
  const missing:string[]=[];
  page.on('response',response=>{
    const url=new URL(response.url());
    if(url.pathname.includes('__next')&&response.status()>=400)missing.push(url.pathname);
  });
  await page.goto('/');
  await page.getByRole('navigation',{name:'작업 페이지'}).getByRole('link',{name:'02 전처리·분석',exact:true}).click();
  await expect(page.getByTestId('processing-empty')).toBeVisible();
  await page.reload();
  await expect(page.getByTestId('processing-empty')).toBeVisible();
  await page.getByRole('navigation',{name:'작업 페이지'}).getByRole('link',{name:'01 데이터 수집',exact:true}).click();
  await expect(page.getByLabel('시작일',{exact:true})).toBeVisible();
  expect(missing).toEqual([]);
});
