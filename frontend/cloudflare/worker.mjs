// Cloudflare Pages advanced-mode entry point. No credentials are bundled here.
const failure = (status, code, message) => Response.json({error: {code, message}}, {
  status, headers: {'Cache-Control': 'no-store'},
});

export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);
    if (incoming.pathname !== '/api' && !incoming.pathname.startsWith('/api/')) {
      return env.ASSETS.fetch(request);
    }
    let base;
    try {
      base = new URL(env.API_BASE_URL);
      if (base.protocol !== 'https:' || base.username || base.password || base.search || base.hash || base.origin === incoming.origin) throw new Error();
    } catch {
      return failure(503, 'API_NOT_CONFIGURED', 'Cloudflare Pages의 API_BASE_URL에 백엔드 HTTPS 기본 주소를 설정해 주세요.');
    }
    const target = new URL(base);
    target.pathname = base.pathname.replace(/\/$/, '') + (incoming.pathname.slice(4) || '/');
    target.search = incoming.search;
    const headers = new Headers(request.headers);
    for (const name of ['host', 'connection', 'content-length', 'forwarded', 'x-forwarded-for', 'x-forwarded-host', 'x-forwarded-proto']) headers.delete(name);
    headers.set('X-Forwarded-Host', incoming.host);
    headers.set('X-Forwarded-Proto', incoming.protocol.slice(0, -1));
    headers.set('Cache-Control', 'no-store');
    try {
      const upstream = await fetch(target, {
        method: request.method, headers,
        body: ['GET', 'HEAD'].includes(request.method) ? undefined : request.body,
        duplex: 'half', redirect: 'manual', signal: request.signal,
        cache: 'no-store',
      });
      const responseHeaders = new Headers(upstream.headers);
      responseHeaders.set('Cache-Control', 'no-store');
      // Preserve cookies and streaming downloads, and keep backend redirects on /api.
      const location = responseHeaders.get('Location');
      if (location) {
        const redirect = new URL(location, target);
        const prefix = base.pathname.replace(/\/$/, '');
        if (redirect.origin === base.origin && (redirect.pathname === prefix || redirect.pathname.startsWith(prefix + '/'))) {
          redirect.pathname = '/api' + (redirect.pathname.slice(prefix.length) || '/');
          responseHeaders.set('Location', incoming.origin + redirect.pathname + redirect.search + redirect.hash);
        }
      }
      return new Response(upstream.body, {status: upstream.status, statusText: upstream.statusText, headers: responseHeaders});
    } catch {
      return failure(502, 'API_UNREACHABLE', '백엔드 서버에 연결하지 못했습니다. 서버 상태와 API_BASE_URL을 확인해 주세요.');
    }
  },
};
