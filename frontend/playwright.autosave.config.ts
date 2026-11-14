import { defineConfig } from '@playwright/test';
import { fileURLToPath } from 'node:url';
const root = fileURLToPath(new URL('..', import.meta.url));
export default defineConfig({
  outputDir: 'test-results/autosave',
  testDir: './autosave-e2e',
  testMatch: 'autosave.spec.ts',
  workers: 1,
  retries: 0,
  timeout: 60000,
  use: { baseURL: 'http://127.0.0.1:15174', trace: 'retain-on-failure' },
  webServer: [
    {
      command: 'backend\\.venv\\Scripts\\python.exe backend/tests/browser_autosave_server.py',
      cwd: root,
      url: 'http://127.0.0.1:18812/api/v1/health',
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 15174 --strictPort',
      url: 'http://127.0.0.1:15174',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:18812' },
      reuseExistingServer: false,
    },
  ],
});
