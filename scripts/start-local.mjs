import {spawn, spawnSync} from 'node:child_process';
import {existsSync} from 'node:fs';
import {createConnection} from 'node:net';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {childEnvironments} from './server-env.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const frontend = path.join(root, 'frontend');
const python = path.join(root, '.venv', process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python');
const next = path.join(frontend, 'node_modules/next/dist/bin/next');
const children = [];
let stopping = false;

function listening(port) {
  return new Promise(resolve => {
    const socket = createConnection({host:'127.0.0.1',port});
    socket.setTimeout(1000);
    socket.once('connect',()=>{socket.destroy();resolve(true);});
    socket.once('error',()=>{socket.destroy();resolve(false);});
    socket.once('timeout',()=>{socket.destroy();resolve(false);});
  });
}

function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) {
    if (child.exitCode !== null || !child.pid) continue;
    // Only terminate the child process trees created by this launcher.
    if (process.platform === 'win32') spawnSync('taskkill',['/pid',String(child.pid),'/t','/f'],{stdio:'ignore',windowsHide:true});
    else child.kill('SIGTERM');
  }
  process.exit(code);
}

function launch(command,args,cwd,env) {
  const child = spawn(command,args,{cwd,env,stdio:'inherit',windowsHide:true});
  children.push(child);
  child.on('error',error=>{console.error(error.message);stop(1);});
  child.on('exit',code=>{if (!stopping) {console.error(`A server stopped (${code}). Restart with start.cmd.`);stop(code || 1);}});
}

async function ready() {
  for (let i=0;i<60;i++) {
    try {
      const response = await fetch('http://127.0.0.1:3000/api/health',{signal:AbortSignal.timeout(2000)});
      if (response.ok && (await response.json()).phase===1) {
        console.log('\nSatellite Insight AI is ready: http://127.0.0.1:3000');
        console.log('Both frontend and backend are running. Keep this window open. Ctrl+C stops both.');
        return;
      }
    } catch { /* Startup is not ready yet. */ }
    await new Promise(resolve=>setTimeout(resolve,1000));
  }
  console.error('Startup timed out. Check the server errors above.');
  stop(1);
}

if (!existsSync(python) || !existsSync(next)) {
  console.error('Dependencies are missing. Follow the installation instructions in README.md.');
  process.exit(1);
}
const occupied = await Promise.all([listening(3000),listening(8000)]);
if (occupied.some(Boolean)) {
  console.error('Port 3000 or 8000 is already in use. Close the existing server before starting. No existing process was stopped.');
  process.exit(1);
}
let environments;
try { environments=childEnvironments(root); }
catch { console.error('Check the server-only backend/.env configuration. Values are never logged.');process.exit(1); }
const worker = spawnSync(process.execPath,['scripts/copy-map-worker.mjs'],{cwd:frontend,env:environments.frontend,stdio:'inherit',windowsHide:true});
if (worker.status !== 0) process.exit(1);
process.on('SIGINT',()=>stop());
process.on('SIGTERM',()=>stop());
launch(python,['-m','uvicorn','app.main:app','--app-dir','backend','--host','127.0.0.1','--port','8000'],root,environments.backend);
launch(process.execPath,[next,'dev','--webpack','--hostname','127.0.0.1','--port','3000'],frontend,environments.frontend);
await ready();
