import {defineConfig} from '@playwright/test';
export default defineConfig({testDir:'./tests',outputDir:process.env.E2E_OUTPUT_DIR||'test-results',timeout:120000,workers:1,use:{baseURL:process.env.E2E_BASE_URL||'http://127.0.0.1:3000',channel:'msedge',headless:true,screenshot:'only-on-failure'},reporter:'list'});
