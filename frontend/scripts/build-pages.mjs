import { spawnSync } from 'node:child_process';
import { copyFile, writeFile, readdir } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = new URL('../', import.meta.url);
const result = spawnSync(process.execPath, [fileURLToPath(new URL('node_modules/next/dist/bin/next', root)), 'build', '--webpack'], {
  cwd: fileURLToPath(root), stdio: 'inherit', windowsHide: true, env: { ...process.env, PAGES_EXPORT: '1' },
});
if (result.error) throw result.error;
if (result.status !== 0) process.exit(result.status ?? 1);
// Next 16.4 on Windows can export segment filenames with backslashes while
// the browser requests dot-separated names. Keep aliases matching Linux output.
if (process.platform === 'win32') {
  const out = fileURLToPath(new URL('out/', root));
  for (const entry of await readdir(out, {recursive: true, withFileTypes: true})) {
    if (!entry.isFile() || !entry.name.endsWith('.txt')) continue;
    const source = path.join(entry.parentPath, entry.name);
    const parts = path.relative(out, source).split(path.sep);
    const index = parts.findIndex(part => part.startsWith('__next'));
    if (index >= 0 && index < parts.length - 1) {
      await copyFile(source, path.join(out, ...parts.slice(0, index), parts.slice(index).join('.')));
    }
  }
}
// Pages advanced mode runs only /api/*; the other files remain static assets.
await copyFile(new URL('cloudflare/worker.mjs', root), new URL('out/_worker.js', root));
await writeFile(new URL('out/_routes.json', root), JSON.stringify({version: 1, include: ['/api', '/api/*'], exclude: []}, null, 2));
console.log('Cloudflare Pages ready: out (static assets + API proxy).');
