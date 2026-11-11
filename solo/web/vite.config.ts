import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const backend = process.env.SOLO_BACKEND_URL ?? 'http://127.0.0.1:8100'
export default defineConfig({
  plugins: [react()],
  server: { host: '127.0.0.1', port: 5174, strictPort: true, proxy: { '/api': backend, '/health': backend } },
  test: { environment: 'jsdom', include: ['src/**/*.test.tsx'], setupFiles: ['./src/setup.ts'], restoreMocks: true },
})
