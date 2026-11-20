import react from '@vitejs/plugin-react';
import { configDefaults, defineConfig } from 'vitest/config';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: { '/api': { target: process.env.API_PROXY_TARGET ?? 'http://127.0.0.1:8000' } },
  },
  test: {
    exclude: [...configDefaults.exclude, 'e2e/**', 'autosave-e2e/**'],
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
    clearMocks: true,
  },
});
