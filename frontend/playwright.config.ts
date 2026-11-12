import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('..', import.meta.url));
const frontend = fileURLToPath(new URL('.', import.meta.url));

export default defineConfig({
  testDir: './e2e',
  testMatch: '*.spec.ts',
  timeout: 60_000,
  expect: { timeout: 20_000 },
  workers: 1,
  retries: 0,
  use: { baseURL: 'http://127.0.0.1:15173', browserName: 'chromium', trace: 'retain-on-failure' },
  webServer: [
    {
      command: 'uv run --project backend --locked python scripts/e2e_backend.py',
      cwd: root,
      url: 'http://127.0.0.1:18811/api/v1/health',
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 15173 --strictPort',
      cwd: frontend,
      url: 'http://127.0.0.1:15173',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:18811' },
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
