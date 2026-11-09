import {mkdir,copyFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
const root=new URL('../',import.meta.url);
await mkdir(new URL('public/maplibre/',root),{recursive:true});
// Keep the worker and shared module at the exact installed library version.
for(const file of ['maplibre-gl-worker.mjs','maplibre-gl-shared.mjs']) {
  await copyFile(fileURLToPath(new URL(`node_modules/maplibre-gl/dist/${file}`,root)),fileURLToPath(new URL(`public/maplibre/${file}`,root)));
}
