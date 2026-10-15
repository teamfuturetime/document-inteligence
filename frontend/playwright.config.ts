import { defineConfig } from '@playwright/test'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const root = fileURLToPath(new URL('..', import.meta.url))

export default defineConfig({
  testDir: './e2e', workers: 1, timeout: 45000, retries: 0,
  use: { baseURL: 'http://127.0.0.1:15173', browserName: 'chromium', trace: 'retain-on-failure' },
  webServer: [
    { command: '.venv/bin/python -m uvicorn document_backend.main:app --host 127.0.0.1 --port 18000',
      cwd: root, url: 'http://127.0.0.1:18000/health', reuseExistingServer: false,
      env: { VDI_MODE: 'real', VDI_TESSDATA_DIR: path.join(root, 'data/models/tessdata') } },
    { command: 'npm run dev -- --port 15173', url: 'http://127.0.0.1:15173', reuseExistingServer: false,
      env: { VDI_BACKEND_URL: 'http://127.0.0.1:18000' } },
  ],
})
