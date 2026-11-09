import {test,expect} from '@playwright/test';

test.beforeEach(async({context})=>{
  await context.route('**/api/auth/providers/status',route=>route.fulfill({json:{providers:[
    {provider_id:'usgs',name:'USGS',configured:false,connected:false,integration:'not_implemented',storage:'none',message:'USGS 원본 인증 미연결'},
    {provider_id:'cdse',name:'Copernicus',configured:false,connected:false,integration:'not_implemented',storage:'none',message:'CDSE 원본 인증 미연결'}
  ]}}));
});

test('Earthdata connection offers one link only when the server is configured',async({page})=>{
  await page.route('**/api/auth/earthdata/status',route=>route.fulfill({json:{
    configured:false,connected:false,scope:'TEST ONLY',message:'Earthdata 앱 등록 정보가 아직 설정되지 않았습니다.'
  }}));
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');
  const account=page.getByLabel('NASA Earthdata 계정');
  await expect(account).toContainText('Earthdata 연결 준비 중');
  await expect(account.getByRole('link',{name:'Earthdata 계정 연결'})).toHaveCount(0);
  await page.route('**/api/auth/earthdata/status',route=>route.fulfill({json:{
    configured:true,connected:false,scope:'TEST ONLY',message:null
  }}));
  await page.reload();
  await expect(account.getByRole('link',{name:'Earthdata 계정 연결'})).toHaveAttribute('href','/api/auth/earthdata/start');
});

test('connected account is not presented as a verified download',async({page})=>{
  let connected=true;
  await page.route('**/api/auth/earthdata/status',route=>route.fulfill({json:{
    configured:true,connected,scope:'TEST ONLY',message:null,storage:'local_single_process_windows_dpapi',refresh_available:true,connection_expires_at:1900000000,access_token_expires_at:1899990000
  }}));
  await page.route('**/api/auth/earthdata/logout',route=>{connected=false;return route.fulfill({json:{connected:false,storage_disposed:true,cleanup_required:false,revocation_recorded:false}});});
  await page.goto('/?earthdata=connected');
  const account=page.getByLabel('NASA Earthdata 계정');
  await expect(account).toContainText('파일의 접근 권한·다운로드는 별도 확인이 필요합니다.');
  await expect(account).toContainText('이 Windows 사용자 계정으로 암호화하여 로컬 저장');
  await expect(account).toContainText('사이트 연결 보관 만료:');
  await expect(account).toContainText('제공처 접근 토큰 만료:');
  await account.getByText('제공처별 연결 상태',{exact:true}).click();
  await expect(account).toContainText('NASA Earthdata 연결은 USGS·Copernicus 로그인을 대신하지 않습니다.');
  await account.getByRole('button',{name:'연결 해제'}).click();
  await expect(account.getByRole('link',{name:'Earthdata 계정 연결'})).toBeVisible();
  await expect(account).toContainText('이 사이트의 Earthdata 연결을 해제했습니다.');
});

test('logout 503 invalidates access, preserves uncertainty through repeated failure and clears only on explicit confirmed retry',async({page})=>{
  let logouts=0,statusReads=0,connected=true;
  await page.addInitScript(()=>window.addEventListener('earthdata-connection-change',()=>{document.documentElement.dataset.authInvalidations=String(Number(document.documentElement.dataset.authInvalidations||0)+1);}));
  await page.route('**/api/auth/earthdata/status',route=>{statusReads++;return route.fulfill({json:{configured:true,connected,storage:'local_single_process_memory',persistence_enabled:false}});});
  await page.route('**/api/auth/earthdata/logout',route=>{
    logouts++;
    if(logouts<3)return route.fulfill({status:503,json:{connected:false,storage_disposed:false,revocation_recorded:false,message:'TEST ONLY 모든 지속 쓰기 실패'}});
    connected=false;return route.fulfill({json:{connected:false,storage_disposed:true,cleanup_required:false,revocation_recorded:false}});
  });
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');const account=page.getByLabel('NASA Earthdata 계정');
  await expect(account).toContainText('Earthdata 연결됨');
  await expect(account).toContainText('기본은 메모리 모드');
  await account.getByRole('button',{name:'연결 해제',exact:true}).click();
  await expect(account.getByRole('alert')).toContainText('디스크 폐기 미확인');
  await expect(account).toContainText('TEST ONLY 모든 지속 쓰기 실패');
  await expect.poll(()=>statusReads).toBeGreaterThan(1);
  await expect(account.getByText('Earthdata 연결됨',{exact:true})).toHaveCount(0);
  await expect(account.getByRole('link',{name:'Earthdata 계정 연결'})).toHaveCount(0);
  await expect.poll(async()=>Number(await page.locator('html').getAttribute('data-auth-invalidations'))).toBeGreaterThanOrEqual(2);
  const signal=await page.evaluate(()=>JSON.parse(localStorage.getItem('satellite-auth-change')!));
  expect(Object.keys(signal).sort()).toEqual(['logout','nonce']);expect(signal.logout).toBe('unconfirmed');
  await account.getByRole('button',{name:'연결 폐기 다시 시도',exact:true}).click();
  await expect.poll(()=>logouts).toBe(2);await expect(account.getByRole('alert')).toContainText('디스크 폐기 미확인');
  await account.getByRole('button',{name:'연결 폐기 다시 시도',exact:true}).click();
  await expect(account).toContainText('저장 정보 폐기를 확인했습니다.');
  await expect(account.getByRole('alert')).toHaveCount(0);
  await expect(account.getByRole('button',{name:'연결 폐기 다시 시도',exact:true})).toHaveCount(0);
  await expect(account.getByRole('link',{name:'Earthdata 계정 연결'})).toBeVisible();
  expect(logouts).toBe(3);
  expect(await page.evaluate(()=>localStorage.getItem('satellite-earthdata-disposal-unconfirmed'))).toBeNull();
});

test('late status with connected true cannot clear disposal uncertainty or show connected after logout 503',async({page})=>{
  let reads=0,heldReads=0,afterLogout=false,release!:()=>void,finish!:()=>void;
  const held=new Promise<void>(resolve=>release=resolve),completed=new Promise<void>(resolve=>finish=resolve);
  await page.route('**/api/auth/earthdata/status',async route=>{reads++;const delay=afterLogout&&heldReads===0;if(delay){heldReads++;await held;}await route.fulfill({json:{configured:true,connected:true}}).catch(()=>{});if(delay)finish();});
  await page.route('**/api/auth/earthdata/logout',route=>{afterLogout=true;return route.fulfill({status:503,json:{connected:false,storage_disposed:false,message:'TEST ONLY 폐기 실패'}});});
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');const account=page.getByLabel('NASA Earthdata 계정');
  await account.getByRole('button',{name:'연결 해제',exact:true}).click();
  await expect(account.getByRole('alert')).toContainText('디스크 폐기 미확인');
  await expect.poll(()=>heldReads).toBe(1);release();await completed;
  await expect(account.getByRole('button',{name:'연결 폐기 다시 시도',exact:true})).toBeEnabled();
  await expect(account.getByRole('alert')).toContainText('디스크 폐기 미확인');
  await expect(account.getByText('Earthdata 연결됨',{exact:true})).toHaveCount(0);
  await expect(account).not.toContainText('저장 정보 폐기를 확인했습니다.');
});

for(const failure of ['network','malformed','missing-session','legacy-success'] as const)
test(`unknown or cookie-less logout cannot claim earlier disposal: ${failure}`,async({page})=>{
  await page.route('**/api/auth/earthdata/status',route=>route.fulfill({json:{configured:true,connected:true,message:{invalid:'TEST ONLY'},storage_message:['invalid'],connection_expires_at:'invalid'}}));
  let count=0;
  await page.route('**/api/auth/earthdata/logout',route=>{
    count++;
    if(failure==='legacy-success'&&count===1)return route.fulfill({status:503,json:{connected:false,storage_disposed:false}});
    if(failure==='network')return route.abort('failed');
    if(failure==='malformed')return route.fulfill({json:{connected:false,storage_disposed:'true',message:{invalid:true}}});
    if(failure==='missing-session')return route.fulfill({status:503,json:{connected:false,storage_disposed:false,session_missing:true,message:'TEST ONLY 원래 연결 쿠키 없음'}});
    return route.fulfill({json:{connected:false,storage_disposed:true}});
  });
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');const account=page.getByLabel('NASA Earthdata 계정');
  await account.getByRole('button',{name:'연결 해제',exact:true}).click();
  await expect(account.getByRole('alert')).toContainText('디스크 폐기 미확인');
  if(failure==='legacy-success'){
    await account.getByRole('button',{name:'연결 폐기 다시 시도',exact:true}).click();
    await expect(account.getByRole('alert')).toContainText('이전 실패 대상의 폐기 성공으로 판단할 수 없습니다.');
  }
  await expect(account.getByRole('button',{name:'연결 폐기 다시 시도',exact:true})).toBeEnabled();
  await expect(account).not.toContainText('저장 정보 폐기를 확인했습니다.');
  await expect(account.getByText('Earthdata 연결됨',{exact:true})).toHaveCount(0);
});

test('another tab learns disposal uncertainty and reload preserves it without sharing credentials',async({page,context})=>{
  let connected=true,logouts=0;
  await context.route('**/api/auth/earthdata/status',route=>route.fulfill({json:{configured:true,connected,storage:'local_single_process_memory'}}));
  await page.route('**/api/auth/earthdata/logout',route=>{
    if(++logouts===1)return route.fulfill({status:503,json:{connected:false,storage_disposed:false,message:'TEST ONLY 폐기 실패'}});
    connected=false;return route.fulfill({json:{connected:false,storage_disposed:true,cleanup_required:false,revocation_recorded:false}});
  });
  await page.goto('/');await page.getByLabel('시작일',{exact:true}).fill('2025-07-01');await page.getByLabel('종료일',{exact:true}).fill('2025-07-31');const other=await context.newPage();await other.goto('/');
  const account=page.getByLabel('NASA Earthdata 계정'),otherAccount=other.getByLabel('NASA Earthdata 계정');
  await expect(otherAccount).toContainText('Earthdata 연결됨');
  await account.getByRole('button',{name:'연결 해제',exact:true}).click();
  await expect(otherAccount.getByRole('alert')).toContainText('다른 탭에서 연결 폐기를 확인하지 못했습니다.');
  await expect(otherAccount.getByText('Earthdata 연결됨',{exact:true})).toHaveCount(0);
  await other.reload();
  await expect(otherAccount.getByRole('alert')).toContainText('이 브라우저의 이전 연결은 디스크 폐기 미확인');
  await expect(otherAccount.getByRole('button',{name:'연결 폐기 다시 시도',exact:true})).toBeEnabled();
  await account.getByRole('button',{name:'연결 폐기 다시 시도',exact:true}).click();
  await expect(account).toContainText('저장 정보 폐기를 확인했습니다.');
  await expect(otherAccount.getByRole('alert')).toHaveCount(0);
  await expect(otherAccount.getByText('Earthdata 연결됨',{exact:true})).toHaveCount(0);
  await expect(otherAccount.getByRole('link',{name:'Earthdata 계정 연결'})).toBeVisible();
  await other.close();
});
