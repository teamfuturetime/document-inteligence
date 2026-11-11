import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('..', import.meta.url))
export default defineConfig({
  testDir: './e2e', fullyParallel: false, workers: 1, timeout: 60000,
  use: { baseURL: 'http://127.0.0.1:15174', viewport: { width: 1440, height: 1000 },
    launchOptions: { executablePath: process.env.SOLO_BROWSER_PATH || undefined }, trace: 'retain-on-failure' },
  webServer: [
    { command: '.venv/bin/python -m uvicorn ai02_solo.api:app --host 127.0.0.1 --port 18100', cwd: root,
      url: 'http://127.0.0.1:18100/health', reuseExistingServer: false },
    { command: 'npm run dev -- --port 15174', url: 'http://127.0.0.1:15174', reuseExistingServer: false,
      env: { SOLO_BACKEND_URL: 'http://127.0.0.1:18100' } },
  ],
})
