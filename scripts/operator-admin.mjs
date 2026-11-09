// Server-console only; fixed argv, no shell, no credential values in stdout/argv.
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {childEnvironments} from './server-env.mjs';
const root=fileURLToPath(new URL('../',import.meta.url));
const [action,provider]=process.argv.slice(2);
if(!['status','revoke-local'].includes(action)||!['usgs','cdse','nasa'].includes(provider)){
 console.error('Use: node scripts/operator-admin.mjs status|revoke-local usgs|cdse|nasa');process.exit(1);
}
try{
 const result=spawnSync(path.join(root,'.venv','Scripts','python.exe'),[path.join(root,'scripts','operator-access.py'),action,provider],{cwd:root,env:childEnvironments(root).backend,stdio:'inherit',windowsHide:true});
 process.exit(result.status??1);
}catch{console.error('Operator console unavailable. Values are not logged.');process.exit(1);}
