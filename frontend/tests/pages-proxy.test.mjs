// TEST ONLY transport; never contacts a real backend/provider.
import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../cloudflare/worker.mjs';
const origin = 'https://test-only.pages.dev';
const env = {API_BASE_URL: 'https://backend.example'};

test('static requests use the Pages asset binding', async () => {
  const response = await worker.fetch(new Request(origin+'/processing'), {ASSETS:{fetch:()=>new Response('static')}});
  assert.equal(await response.text(),'static');
});

test('missing/invalid backend gives explicit 503, never falls back to localhost', async () => {
  for (const value of [undefined,'http://backend.example','https://user:secret@backend.example',origin,'https://backend.example?secret=1']) {
    const response=await worker.fetch(new Request(origin+'/api/health'),{API_BASE_URL:value});
    assert.equal(response.status,503);
    assert.equal((await response.json()).error.code,'API_NOT_CONFIGURED');
  }
});

test('POST path, query, body, cookies and Origin reach only configured backend', async t => {
  t.mock.method(globalThis,'fetch',async (url,init)=>{
    assert.equal(String(url),'https://backend.example/v1/media/inspect?download=1');
    assert.equal(init.headers.get('Origin'),origin);
    assert.equal(init.headers.get('Cookie'),'session=TEST_ONLY');
    assert.equal(init.headers.get('X-Forwarded-Host'),'test-only.pages.dev');
    assert.equal(init.headers.get('Forwarded'),null);
    assert.equal(init.redirect,'manual');
    assert.equal(await new Response(init.body).text(),'{"test":true}');
    const headers=new Headers({'Content-Type':'application/json'});
    headers.append('Set-Cookie','a=TEST_ONLY; Path=/; HttpOnly; Secure');
    headers.append('Set-Cookie','b=TEST_ONLY; Path=/api/media; HttpOnly; Secure');
    return new Response('{}',{headers});
  });
  const request=new Request(origin+'/api/media/inspect?download=1',{method:'POST',body:'{"test":true}',headers:{Origin:origin,Cookie:'session=TEST_ONLY',Forwarded:'host=evil.example'}});
  const response=await worker.fetch(request,{API_BASE_URL:'https://backend.example/v1/'});
  assert.equal(response.headers.getSetCookie().length,2);
  assert.equal(response.headers.get('Cache-Control'),'no-store');
});

test('binary download and backend failures retain body/status, with no caching', async t => {
  const bytes=new Uint8Array([80,75,0,255]);
  t.mock.method(globalThis,'fetch',async ()=>new Response(bytes,{status:206,headers:{'Content-Disposition':'attachment; filename="test.zip"','Content-Range':'bytes 0-3/8'}}));
  const response=await worker.fetch(new Request(origin+'/api/processing/jobs/test/download'),env);
  assert.equal(response.status,206);
  assert.deepEqual(new Uint8Array(await response.arrayBuffer()),bytes);
  assert.match(response.headers.get('Content-Disposition'),/test.zip/);
});

test('redirects are not followed; backend locations retain public /api prefix', async t => {
  for(const [location,expected] of [['/health',origin+'/api/health'],['https://external.example/login','https://external.example/login']]) {
    t.mock.method(globalThis,'fetch',async ()=>new Response(null,{status:307,headers:{Location:location}}));
    const response=await worker.fetch(new Request(origin+'/api/health/'),env);
    assert.equal(response.status,307);
    assert.equal(response.headers.get('Location'),expected);
  }
});

test('upstream error is preserved; network failure is sanitized',async t=>{
  t.mock.method(globalThis,'fetch',async()=>Response.json({error:'TEST_ONLY'},{status:403}));
  assert.equal((await worker.fetch(new Request(origin+'/api/test'),env)).status,403);
  t.mock.method(globalThis,'fetch',async()=>{throw new Error('SECRET_TEST_ONLY');});
  const response=await worker.fetch(new Request(origin+'/api/test'),env);
  assert.equal(response.status,502);
  assert.doesNotMatch(await response.text(),/SECRET_TEST_ONLY/);
});
