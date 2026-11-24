import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './e2e',
  testMatch: 'keyboard-review.spec.ts',
  workers: 1,
  retries: 0,
  timeout: 60000,
  use: { baseURL: 'http://127.0.0.1:15176', browserName: 'chromium' },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1 --port 15176 --strictPort',
    url: 'http://127.0.0.1:15176',
    reuseExistingServer: false,
  },
});
