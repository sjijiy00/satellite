// TEST ONLY archive transport failures. These bytes are not provider imagery.
import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {test,expect,type Page} from './runtime';

const bytes=Buffer.from('PK TEST ONLY retained result');
const row={job_id:'d'.repeat(32),status:'succeeded',created_at:'2026-11-05T00:00:00Z',input:{analysis_id:'vegetation_index'},
 artifact:{filename:'TEST_ONLY_retained.zip',bytes:bytes.length,sha256:createHash('sha256').update(bytes).digest('hex')},
 retention:{state:'available',expires_at:'2099-01-01T00:00:00Z'}};
async function open(page:Page){
 await page.route('**/api/processing/jobs',r=>r.fulfill({json:{jobs:[row]}}));
 await page.goto('/');await page.getByText('내 결과 보관함 · 재시작 후 찾기',{exact:true}).click();
 await page.getByRole('button',{name:'보관 결과 조회',exact:true}).click();
 return page.locator('.result-archive');
}

test('TEST ONLY retained ZIP expires after listing: explain failure in place, then retry without rerunning analysis',async({page})=>{
 let attempts=0,downloads=0;
 page.on('download',()=>downloads++);
 await page.route('**/api/processing/jobs/*/download',r=>{
  attempts++;
  return attempts===1?r.fulfill({status:410,json:{detail:'TEST ONLY expired'}}):r.fulfill({body:bytes,contentType:'application/zip',headers:{'content-length':String(bytes.length)}});
 });
 const archive=await open(page);
 await archive.getByText('이전 결과 ZIP 저장',{exact:true}).click();
 await expect(archive.getByRole('alert')).toContainText('만료');
 expect(downloads).toBe(0);await expect(page).toHaveURL(/\/$/);
 await archive.getByRole('button',{name:'보관 결과 조회',exact:true}).click();
 const pending=page.waitForEvent('download');await archive.getByText('이전 결과 ZIP 저장',{exact:true}).click();
 const file=await pending;expect(await readFile((await file.path())!)).toEqual(bytes);
 await expect(archive).toContainText('SHA-256 확인');expect(attempts).toBe(2);
});

test('TEST ONLY retained ZIP with changed bytes is not saved as a verified result',async({page})=>{
 let downloads=0;page.on('download',()=>downloads++);
 const corrupt=Buffer.alloc(bytes.length,65);
 await page.route('**/api/processing/jobs/*/download',r=>r.fulfill({body:corrupt,contentType:'application/zip',headers:{'content-length':String(corrupt.length)}}));
 const archive=await open(page);await archive.getByText('이전 결과 ZIP 저장',{exact:true}).click();
 await expect(archive.getByRole('alert')).toContainText('SHA-256');expect(downloads).toBe(0);
});

test('TEST ONLY malformed archive response does not crash the page and a retry recovers',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('/');await page.getByText('내 결과 보관함 · 재시작 후 찾기',{exact:true}).click();
 await page.route('**/api/processing/jobs',r=>r.fulfill({json:{jobs:null}}));
 const archive=page.locator('.result-archive');await archive.getByRole('button',{name:'보관 결과 조회',exact:true}).click();
 await expect(archive.getByRole('alert')).toContainText('응답');expect(errors).toEqual([]);
 await page.route('**/api/processing/jobs',r=>r.fulfill({json:{jobs:[]}}));
 await archive.getByRole('button',{name:'보관 결과 조회',exact:true}).click();
 await expect(archive).toContainText('보관 중인 작업이 없습니다');
});
