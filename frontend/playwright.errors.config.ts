import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: 'error-guidance.spec.ts',
  workers: 1,
  retries: 0,
  use: { baseURL: 'http://127.0.0.1:15175', browserName: 'chromium' },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 15175 --strictPort',
    url: 'http://127.0.0.1:15175',
    reuseExistingServer: false,
  },
});
