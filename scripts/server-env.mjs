import {existsSync, readFileSync} from 'node:fs';
import path from 'node:path';
import {parseEnv} from 'node:util';

export const SERVER_ENV_NAMES = Object.freeze([
  'PUBLIC_APP_ORIGIN',
  'AI_NL_ENABLED', 'AI_NL_PROVIDER', 'AI_NL_MODEL', 'OPENAI_API_KEY',
  'AI_NL_INPUT_USD_PER_MILLION', 'AI_NL_OUTPUT_USD_PER_MILLION',
  'AI_NL_TIMEOUT_SECONDS', 'AI_NL_MAX_OUTPUT_TOKENS', 'AI_NL_REQUESTS_PER_MINUTE', 'AI_NL_REQUESTS_PER_PROCESS',
  'EARTHDATA_CLIENT_ID', 'EARTHDATA_CLIENT_SECRET', 'EARTHDATA_REDIRECT_URI',
  'EARTHDATA_PERSIST_SESSIONS',
  'GEOCODER_ENABLED', 'KAKAO_LOCAL_REST_API_KEY',
  'OPERATOR_ACCESS_ENABLED', 'OPERATOR_PUBLIC_ORIGIN', 'OPERATOR_STORE_PATH', 'OPERATOR_WORKERS',
  'OPERATOR_NASA_COLLECTIONS', 'OPERATOR_NASA_HLS_REDISTRIBUTION_REVIEWED',
  'OPERATOR_NASA_RESUME_STORED_GRANT',
  ...['USGS','CDSE','NASA'].flatMap(provider=>[
    `OPERATOR_${provider}_ENABLED`, `OPERATOR_${provider}_REVISION`, `OPERATOR_${provider}_REDISTRIBUTION_REVIEWED`,
    ...({USGS:['USERNAME','APPLICATION_TOKEN'],CDSE:['USERNAME','PASSWORD','REFRESH_TOKEN'],NASA:['USER_TOKEN','TOKEN_EXPIRES_AT']}[provider].map(name=>`OPERATOR_${provider}_${name}`)),
  ]),
]);

export function frontendEnvironment(inherited) {
  // Preserve unrelated process settings. All OpenAI/AI_NL configuration is server-only.
  return Object.fromEntries(Object.entries(inherited).filter(([name]) =>
    !/^(?:OPENAI_|AI_NL_|EARTHDATA_|KAKAO_|GEOCODER_|OPERATOR_|USGS_|CDSE_|COPERNICUS_|AWS_|NEXT_PUBLIC_(?:OPENAI_|AI_NL_|EARTHDATA_|KAKAO_|GEOCODER_|OPERATOR_|USGS_|CDSE_|COPERNICUS_|AWS_))/i.test(name)));
}

export function childEnvironments(root, inherited=process.env) {
  // Exactly one fixed file. Never use .env.example or merge root/frontend env files.
  const file = path.join(root, 'backend', '.env');
  let parsed = {};
  try {
    if (existsSync(file)) {
      const raw = readFileSync(file, 'utf8');
      // Node's parseEnv may swallow the next assignment after `KEY= `.
      // Treat whitespace-only operator placeholders as genuinely empty.
      const normalized = raw.split(/\r?\n/).map(line => line.replace(
        /^([ \t]*(?:export[ \t]+)?OPERATOR_[A-Z0-9_]+)=[ \t]+$/, '$1=',
      )).join('\n');
      parsed = parseEnv(normalized);
    }
  } catch {
    // Do not print parser errors, lines, values or raw file contents.
    throw new Error('Cannot read the server environment file: backend/.env');
  }
  const backend = {...inherited};
  for (const name of SERVER_ENV_NAMES) {
    // Presence, including an intentionally empty process value, wins over the file.
    if (!Object.hasOwn(inherited,name) && Object.hasOwn(parsed,name)) backend[name]=parsed[name];
  }
  return {backend, frontend:frontendEnvironment(inherited)};
}
