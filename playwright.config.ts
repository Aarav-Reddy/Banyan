import { defineConfig } from '@playwright/test';
import { existsSync } from 'node:fs';
const systemChrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const executablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH || (existsSync(systemChrome) ? systemChrome : undefined);
export default defineConfig({
  testDir: './tests/e2e', fullyParallel: false, workers: 1, retries: 0,
  timeout: 90000, expect: { timeout: 15000 },
  reporter: [['list'], ['html', { open: 'never' }]],
  use: { baseURL: 'http://127.0.0.1:8081', browserName: 'chromium', launchOptions: { executablePath }, trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [{ name: 'desktop', use: { viewport: { width: 1440, height: 1000 } } }, { name: 'mobile', use: { viewport: { width: 390, height: 844 } } }],
  webServer: { command: '.venv/bin/python scripts/e2e-server.py', url: 'http://127.0.0.1:8081', reuseExistingServer: false, timeout: 120000, gracefulShutdown: { signal: 'SIGTERM', timeout: 15000 } },
});
