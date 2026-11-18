import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const frontend = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  testDir: './e2e',
  testMatch: 'auth.spec.ts',
  outputDir: 'test-results-auth',
  timeout: 90_000,
  expect: { timeout: 20_000 },
  workers: 1,
  retries: 0,
  use: {
    baseURL: 'http://127.0.0.1:15174',
    browserName: 'chromium',
    trace: 'retain-on-failure',
    launchOptions: process.env.DOCINTEL_BROWSER_EXECUTABLE
      ? { executablePath: process.env.DOCINTEL_BROWSER_EXECUTABLE }
      : {},
  },
  webServer: [
    {
      command: 'uv run --project backend --locked python scripts/e2e_auth_backend.py',
      cwd: root,
      url: 'http://127.0.0.1:18812/api/v1/health',
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 15174 --strictPort',
      cwd: frontend,
      url: 'http://127.0.0.1:15174',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:18812' },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
