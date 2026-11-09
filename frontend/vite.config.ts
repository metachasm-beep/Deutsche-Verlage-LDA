import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/run-lda': 'http://127.0.0.1:8000',
      '/trends': 'http://127.0.0.1:8000',
      '/topic-viz': 'http://127.0.0.1:8000',
      '/data-summary': 'http://127.0.0.1:8000',
    }
  }
})
