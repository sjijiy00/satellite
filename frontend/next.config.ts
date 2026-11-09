import type { NextConfig } from 'next';
const config: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR || '.next',
  experimental: { proxyTimeout: 26 * 60_000 },
  async rewrites() { return [{ source: '/api/:path*', destination: `${process.env.API_BASE_URL || 'http://127.0.0.1:8000'}/:path*` }]; },
};
export default config;
