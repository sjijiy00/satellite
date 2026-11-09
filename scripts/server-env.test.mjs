import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,existsSync,rmSync} from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {spawnSync} from 'node:child_process';
import {childEnvironments,frontendEnvironment,SERVER_ENV_NAMES} from './server-env.mjs';
import {configureServerEnv,SAFE_EXAMPLE} from './configure-server-env.mjs';
const fake='TEST_ONLY_NOT_A_CREDENTIAL';

test('HLS product scope and separate review gate reach backend only; process wins',t=>{
 const root=sandbox(t);
 writeFileSync(path.join(root,'backend','.env'),'OPERATOR_NASA_COLLECTIONS=hls-l30-002,hls-s30-002\nOPERATOR_NASA_HLS_REDISTRIBUTION_REVIEWED=1\n');
 const env=childEnvironments(root,{OPERATOR_NASA_HLS_REDISTRIBUTION_REVIEWED:'0',NEXT_PUBLIC_OPERATOR_NASA_COLLECTIONS:'TEST_ONLY'});
 assert.equal(env.backend.OPERATOR_NASA_COLLECTIONS,'hls-l30-002,hls-s30-002');
 assert.equal(env.backend.OPERATOR_NASA_HLS_REDISTRIBUTION_REVIEWED,'0');
 assert.equal(env.frontend.OPERATOR_NASA_COLLECTIONS,undefined);
 assert.equal(env.frontend.NEXT_PUBLIC_OPERATOR_NASA_COLLECTIONS,undefined);
});

test('NASA encrypted grant restart switch reaches backend only',t=>{
 const root=sandbox(t);
 writeFileSync(path.join(root,'backend','.env'),'OPERATOR_NASA_RESUME_STORED_GRANT=1\n');
 const env=childEnvironments(root,{NEXT_PUBLIC_OPERATOR_NASA_RESUME_STORED_GRANT:'1'});
 assert.equal(env.backend.OPERATOR_NASA_RESUME_STORED_GRANT,'1');
 assert.equal(env.frontend.OPERATOR_NASA_RESUME_STORED_GRANT,undefined);
 assert.equal(env.frontend.NEXT_PUBLIC_OPERATOR_NASA_RESUME_STORED_GRANT,undefined);
});

test('whitespace-only operator placeholder cannot consume the next setting',t=>{
 const root=sandbox(t);
 writeFileSync(path.join(root,'backend','.env'),'OPERATOR_CDSE_REFRESH_TOKEN= \nOPERATOR_CDSE_REVISION=2\n');
 const env=childEnvironments(root,{});
 assert.equal(env.backend.OPERATOR_CDSE_REFRESH_TOKEN,'');
 assert.equal(env.backend.OPERATOR_CDSE_REVISION,'2');
});

test('operator issuer credentials are allowlisted server-only, never front/build/NEXT_PUBLIC',t=>{
 const root=sandbox(t);
 writeFileSync(path.join(root,'backend','.env'),`OPERATOR_ACCESS_ENABLED=1\nOPERATOR_USGS_APPLICATION_TOKEN=${fake}\nOPERATOR_CDSE_PASSWORD=${fake}\nOPERATOR_NASA_USER_TOKEN=${fake}\nOPERATOR_UNREVIEWED=never\n`);
 const env=childEnvironments(root,{OPERATOR_CDSE_PASSWORD:'TEST_ONLY_PROCESS',NEXT_PUBLIC_OPERATOR_NASA_USER_TOKEN:fake,AWS_SECRET_ACCESS_KEY:fake});
 assert.equal(env.backend.OPERATOR_USGS_APPLICATION_TOKEN,fake);assert.equal(env.backend.OPERATOR_CDSE_PASSWORD,'TEST_ONLY_PROCESS');assert.equal(env.backend.OPERATOR_NASA_USER_TOKEN,fake);assert.equal(env.backend.OPERATOR_UNREVIEWED,undefined);
 for(const name of Object.keys(env.frontend))assert.ok(!/OPERATOR_|AWS_|CDSE_|USGS_/i.test(name));
});

test('only persistence switch joins Earthdata allowlist; backend only and process precedence',t=>{
 const root=sandbox(t);
 writeFileSync(path.join(root,'backend','.env'),'EARTHDATA_PERSIST_SESSIONS=1\nEARTHDATA_STORAGE_PATH=DO_NOT_LOAD\nEARTHDATA_PASSWORD=DO_NOT_LOAD\n');
 assert.equal(childEnvironments(root,{}).backend.EARTHDATA_PERSIST_SESSIONS,'1');
 const env=childEnvironments(root,{EARTHDATA_PERSIST_SESSIONS:'0',NEXT_PUBLIC_EARTHDATA_PERSIST_SESSIONS:'1'});
 assert.equal(env.backend.EARTHDATA_PERSIST_SESSIONS,'0');
 assert.equal(env.backend.EARTHDATA_STORAGE_PATH,undefined);assert.equal(env.backend.EARTHDATA_PASSWORD,undefined);
 assert.equal(env.frontend.EARTHDATA_PERSIST_SESSIONS,undefined);
 assert.equal(env.frontend.NEXT_PUBLIC_EARTHDATA_PERSIST_SESSIONS,undefined);
});

test('Kakao geocoder key is server-only and never NEXT_PUBLIC; existing process wins',t=>{
 const root=sandbox(t);writeFileSync(path.join(root,'backend','.env'),`GEOCODER_ENABLED=1\nKAKAO_LOCAL_REST_API_KEY=${fake}\n`);
 const env=childEnvironments(root,{KAKAO_LOCAL_REST_API_KEY:'TEST_ONLY_PROCESS',NEXT_PUBLIC_KAKAO_LOCAL_REST_API_KEY:fake});
 assert.equal(env.backend.KAKAO_LOCAL_REST_API_KEY,'TEST_ONLY_PROCESS');assert.equal(env.backend.GEOCODER_ENABLED,'1');
 assert.equal(env.frontend.KAKAO_LOCAL_REST_API_KEY,undefined);assert.equal(env.frontend.NEXT_PUBLIC_KAKAO_LOCAL_REST_API_KEY,undefined);assert.equal(env.frontend.GEOCODER_ENABLED,undefined);
});
function sandbox(t){const root=mkdtempSync(path.join(os.tmpdir(),'satellite-settings-'));mkdirSync(path.join(root,'backend'));t.after(()=>rmSync(root,{recursive:true,force:true}));return root;}

test('one canonical server file, no root/frontend/example merging; only allowlisted fields',t=>{
 const root=sandbox(t);mkdirSync(path.join(root,'frontend'));
 for(const f of ['.env','frontend/.env','backend/.env.example'])writeFileSync(path.join(root,f),'OPENAI_API_KEY=TEST_ONLY_WRONG_FILE\nAI_NL_MODEL=TEST_ONLY_WRONG_MODEL');
 let env=childEnvironments(root,{UNRELATED:'preserved'});assert.equal(env.backend.OPENAI_API_KEY,undefined);
 writeFileSync(path.join(root,'backend','.env'),`AI_NL_ENABLED=1\nAI_NL_PROVIDER=openai\nAI_NL_MODEL=gpt-5.6-luna\nOPENAI_API_KEY=${fake}\nUNEXPECTED=never_pass\n`);
 env=childEnvironments(root,{UNRELATED:'preserved'});assert.equal(env.backend.OPENAI_API_KEY,fake);assert.equal(env.backend.UNRELATED,'preserved');assert.equal(env.backend.UNEXPECTED,undefined);
 assert.equal(env.frontend.OPENAI_API_KEY,undefined);assert.equal(env.frontend.AI_NL_MODEL,undefined);
});

test('existing process values including empty take precedence without mutation',t=>{
 const root=sandbox(t);writeFileSync(path.join(root,'backend','.env'),`OPENAI_API_KEY=${fake}\nAI_NL_MODEL=file-model`);
 const base={OPENAI_API_KEY:'',AI_NL_MODEL:'user-model',PATH:process.env.PATH};const env=childEnvironments(root,base);
 assert.equal(env.backend.OPENAI_API_KEY,'');assert.equal(env.backend.AI_NL_MODEL,'user-model');assert.equal(base.AI_NL_MODEL,'user-model');assert.equal(base.OPENAI_API_KEY,'');
});

test('frontend and worker/build env exclude AI/server and NEXT_PUBLIC AI names',()=>{
 const env=frontendEnvironment({OPENAI_API_KEY:fake,OPENAI_ORG_ID:'TEST_ONLY',AI_NL_ENABLED:'1',NEXT_PUBLIC_OPENAI_API_KEY:fake,NEXT_PUBLIC_AI_NL_MODEL:'TEST_ONLY',API_BASE_URL:'http://127.0.0.1:8000',UNRELATED:'preserved'});
 assert.deepEqual(env,{API_BASE_URL:'http://127.0.0.1:8000',UNRELATED:'preserved'});
});

test('Earthdata application credentials reach backend only; user token is not loaded from file',t=>{
 const root=sandbox(t);
 writeFileSync(path.join(root,'backend','.env'),`EARTHDATA_CLIENT_ID=TEST_ONLY_ID\nEARTHDATA_CLIENT_SECRET=${fake}\nEARTHDATA_REDIRECT_URI=http://127.0.0.1:3000/api/auth/earthdata/callback\nEARTHDATA_TOKEN=DO_NOT_LOAD\n`);
 const env=childEnvironments(root,{});
 assert.equal(env.backend.EARTHDATA_CLIENT_SECRET,fake);
 assert.equal(env.backend.EARTHDATA_TOKEN,undefined);
 assert.equal(env.frontend.EARTHDATA_CLIENT_ID,undefined);
 assert.equal(env.frontend.EARTHDATA_CLIENT_SECRET,undefined);
 assert.equal(frontendEnvironment({EARTHDATA_CLIENT_SECRET:fake,NEXT_PUBLIC_EARTHDATA_TOKEN:fake,UNRELATED:'ok'}).UNRELATED,'ok');
 assert.equal(frontendEnvironment({EARTHDATA_CLIENT_SECRET:fake,NEXT_PUBLIC_EARTHDATA_TOKEN:fake}).EARTHDATA_CLIENT_SECRET,undefined);
});

test('quoted values, BOM, comments; no shell execution or interpolation',t=>{
 const root=sandbox(t);const text='\ufeff# test\nexport OPENAI_API_KEY="TEST_ONLY_hash#literal"\nAI_NL_MODEL=custom-model # comment\nAI_NL_PROVIDER="$(TEST_ONLY)"\n';
 writeFileSync(path.join(root,'backend','.env'),text);const env=childEnvironments(root,{});
 assert.equal(env.backend.OPENAI_API_KEY,'TEST_ONLY_hash#literal');assert.equal(env.backend.AI_NL_MODEL,'custom-model');assert.equal(env.backend.AI_NL_PROVIDER,'$(TEST_ONLY)');assert.equal(readFileSync(path.join(root,'backend','.env'),'utf8'),text);
});

test('read failures never print data or underlying exception contents',t=>{
 const root=sandbox(t);mkdirSync(path.join(root,'backend','.env'));
 assert.throws(()=>childEnvironments(root,{}),{message:'Cannot read the server environment file: backend/.env'});
});

test('actual child processes see key only in server environment',t=>{
 const root=sandbox(t);writeFileSync(path.join(root,'backend','.env'),`OPENAI_API_KEY=${fake}`);const env=childEnvironments(root,frontendEnvironment(process.env));
 const probe='console.log(JSON.stringify({keyPresent:!!process.env.OPENAI_API_KEY,wrongPresent:!!process.env.NEXT_PUBLIC_OPENAI_API_KEY}))';
 const server=spawnSync(process.execPath,['-e',probe],{env:env.backend,encoding:'utf8'});const frontend=spawnSync(process.execPath,['-e',probe],{env:env.frontend,encoding:'utf8'});
 assert.equal(server.status,0);assert.equal(frontend.status,0);assert.equal(JSON.parse(server.stdout).keyPresent,true);assert.equal(JSON.parse(frontend.stdout).keyPresent,false);assert.ok(!server.stdout.includes(fake));assert.ok(!frontend.stdout.includes(fake));
});

test('credential application requires approval and renames existing file',t=>{
 const root=sandbox(t),example=path.join(root,'backend','.env.example'),target=path.join(root,'backend','.env');
 const original=`# keep\nOPENAI_API_KEY=${fake}\nAI_NL_ENABLED=0\nAI_NL_PROVIDER=openai\nAI_NL_MODEL=\nOTHER_OPTION="preserved # text"\n`;
 writeFileSync(example,original);assert.throws(()=>configureServerEnv(root),/approval/);assert.equal(readFileSync(example,'utf8'),original);assert.equal(existsSync(target),false);
 const result=configureServerEnv(root,{approved:true});assert.equal(result.credential_present,true);assert.equal(result.model_preserved,false);
 assert.equal(readFileSync(example,'utf8'),SAFE_EXAMPLE);const privateText=readFileSync(target,'utf8');assert.ok(privateText.includes(`OPENAI_API_KEY=${fake}`));assert.ok(privateText.includes('OTHER_OPTION="preserved # text"'));assert.ok(privateText.includes('AI_NL_MODEL=gpt-4o'));assert.ok(privateText.includes('AI_NL_ENABLED=1'));assert.ok(!JSON.stringify(result).includes(fake));
});

test('user model and unrelated values preserved; no overwriting conflicting files',t=>{
 const root=sandbox(t),target=path.join(root,'backend','.env');writeFileSync(target,`OPENAI_API_KEY=${fake}\nAI_NL_MODEL="user-model" # preserve\nOTHER=unchanged\n`);
 const r=configureServerEnv(root,{approved:true});assert.equal(r.model_preserved,true);assert.ok(readFileSync(target,'utf8').includes('AI_NL_MODEL="user-model" # preserve'));assert.ok(readFileSync(target,'utf8').includes('OTHER=unchanged'));
 writeFileSync(path.join(root,'backend','.env.example'),`OPENAI_API_KEY=${fake}`);const before=readFileSync(target,'utf8');assert.throws(()=>configureServerEnv(root,{approved:true}),/Both/);assert.equal(readFileSync(target,'utf8'),before);
});

test('launcher attaches each isolated environment to the correct process',()=>{
 const text=readFileSync(new URL('./start-local.mjs',import.meta.url),'utf8');assert.match(text,/env:environments.frontend/);assert.match(text,/8000'\],root,environments.backend/);assert.match(text,/3000'\],frontend,environments.frontend/);assert.equal(SERVER_ENV_NAMES.includes('NEXT_PUBLIC_OPENAI_API_KEY'),false);
});


test('independent frontend checks use only the filtered inherited environment',()=>{
 const text=readFileSync(new URL('./frontend-check.mjs',import.meta.url),'utf8');
 assert.match(text,/frontendEnvironment\(process.env\)/);assert.match(text,/cwd:frontend,env,stdio/);assert.ok(!text.includes('childEnvironments('));
});


test('settings update supports export/indentation without duplicate active entries',t=>{
 const root=sandbox(t),target=path.join(root,'backend','.env');
 writeFileSync(target,`OPENAI_API_KEY=${fake}\n export AI_NL_ENABLED=0\n  AI_NL_PROVIDER=other\nAI_NL_MODEL=\n`);
 configureServerEnv(root,{approved:true});const text=readFileSync(target,'utf8');
 assert.equal(text.match(/AI_NL_ENABLED=/g).length,1);assert.ok(text.includes('AI_NL_ENABLED=1'));assert.ok(text.includes('AI_NL_PROVIDER=openai'));
});


test('gitignore excludes private server env but permits secret-free example in a disposable repo',t=>{
 const root=sandbox(t);writeFileSync(path.join(root,'.gitignore'),readFileSync(new URL('../.gitignore',import.meta.url)));
 writeFileSync(path.join(root,'backend','.env'),'OPENAI_API_KEY=TEST_ONLY_NOT_REAL\n');writeFileSync(path.join(root,'backend','.env.example'),SAFE_EXAMPLE);
 const init=spawnSync('git',['-c','init.templateDir=','init','--quiet',root],{encoding:'utf8'});assert.equal(init.status,0);
 const ignored=spawnSync('git',['check-ignore','backend/.env'],{cwd:root,encoding:'utf8'});
 const example=spawnSync('git',['check-ignore','backend/.env.example'],{cwd:root,encoding:'utf8'});
 assert.equal(ignored.status,0);assert.equal(example.status,1);
});
