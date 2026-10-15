import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    // Same-origin requests avoid needing backend CORS in local development.
    proxy: { '/health': process.env.VDI_BACKEND_URL ?? 'http://127.0.0.1:8000',
             '/api': process.env.VDI_BACKEND_URL ?? 'http://127.0.0.1:8000' },
  },
  test: {
    include: ['src/**/*.test.{ts,tsx}'],
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    restoreMocks: true,
    clearMocks: true,
  },
})
