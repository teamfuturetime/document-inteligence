/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
export default defineConfig({plugins:[react(),tailwindcss()],server:{port:5173,proxy:{'/api':'http://localhost:8000'}},test:{environment:'jsdom',coverage:{provider:'v8',include:['src/components/OCRTextCard.tsx','src/pages/DocumentDetailPage.tsx','src/api/client.ts','src/contexts/AuthContext.tsx','src/utils/ocrDrafts.ts'],reporter:['text','json','json-summary'],reportsDirectory:'../evidence/bt3-vt043/frontend_coverage'}}})
