import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {frontendEnvironment} from './server-env.mjs';
const root=fileURLToPath(new URL('../',import.meta.url)),frontend=path.join(root,'frontend');
const command=process.argv[2],env=frontendEnvironment(process.env);
if (!['typecheck','build'].includes(command)) {console.error('Use typecheck or build.');process.exit(1);}
function run(script,args=[]) {
  const result=spawnSync(process.execPath,[script,...args],{cwd:frontend,env,stdio:'inherit',windowsHide:true});
  if(result.error){console.error('Frontend check failed to start. Environment values are not logged.');process.exit(1);}
  if(result.status!==0)process.exit(result.status||1);
}
if(command==='build') {
  run(path.join(frontend,'scripts/copy-map-worker.mjs'));
  run(path.join(frontend,'node_modules/next/dist/bin/next'),['build','--webpack']);
} else run(path.join(frontend,'node_modules/typescript/bin/tsc'),['--noEmit']);
