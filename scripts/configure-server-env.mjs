import {existsSync, readFileSync, renameSync, writeFileSync} from 'node:fs';
import {parseEnv} from 'node:util';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

export const DEFAULT_MODEL='gpt-4o';
export const SAFE_EXAMPLE = `# Loaded only by scripts/start-local.mjs into the backend process.
# Never put a real credential in this example or NEXT_PUBLIC variables.
AI_NL_ENABLED=1
AI_NL_PROVIDER=openai
AI_NL_MODEL=gpt-4o
OPENAI_API_KEY=
AI_NL_INPUT_USD_PER_MILLION=
AI_NL_OUTPUT_USD_PER_MILLION=
# Only after registering this application with Earthdata Login.
EARTHDATA_CLIENT_ID=
EARTHDATA_CLIENT_SECRET=
EARTHDATA_REDIRECT_URI=
`;

export function configureServerEnv(root,{approved=false}={}) {
  // The caller must obtain the user's approval to connect existing credentials persistently.
  if (!approved) throw new Error('User approval required before applying existing credentials.');
  const target=path.join(root,'backend','.env'),example=path.join(root,'backend','.env.example');
  const hasCredential=file=>existsSync(file)&&Boolean(parseEnv(readFileSync(file,'utf8')).OPENAI_API_KEY?.trim());
  if (existsSync(target)&&hasCredential(example)) throw new Error('Both settings files exist; no files were changed.');
  if (!existsSync(target)) {
    if (!hasCredential(example)) throw new Error('No existing server credential file found; no files were changed.');
    // Rename the user's original file itself. Do not copy a credential to another file or log it.
    renameSync(example,target);
  }
  const original=readFileSync(target,'utf8'),parsed=parseEnv(original);
  const model=parsed.AI_NL_MODEL?.trim()||DEFAULT_MODEL;
  const values={AI_NL_ENABLED:'1',AI_NL_PROVIDER:'openai',AI_NL_MODEL:model};
  let updated=original;
  for (const [name,value] of Object.entries(values)) {
    if (name==='AI_NL_MODEL'&&parsed.AI_NL_MODEL?.trim()) continue;
    const pattern=new RegExp('^[ \t]*(?:export[ \t]+)?'+name+'[ \t]*=.*$','gm');
    if (pattern.test(updated)) updated=updated.replace(pattern,()=>name+'='+value);
    else updated+=(updated.endsWith('\n')?'':'\n')+name+'='+value+'\n';
  }
  if (updated!==original) writeFileSync(target,updated,{mode:0o600});
  if (!existsSync(example)) writeFileSync(example,SAFE_EXAMPLE,{flag:'wx'});
  return {server_file:'backend/.env',credential_present:Boolean(parsed.OPENAI_API_KEY?.trim()),
          model_preserved:Boolean(parsed.AI_NL_MODEL?.trim())};
}

if (process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  if (!process.argv.includes('--apply-approved')) {
    console.error('Approval required. This command has not read or changed credential settings.');process.exitCode=1;
  } else {
    try {console.log(JSON.stringify(configureServerEnv(fileURLToPath(new URL('../',import.meta.url)),{approved:true})));}
    catch {console.error('Settings were not fully applied. Check file existence/approval; values are never logged.');process.exitCode=1;}
  }
}
