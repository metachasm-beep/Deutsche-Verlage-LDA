import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/run-lda': 'http://localhost:8000',
      '/trends': 'http://localhost:8000',
      '/topic-viz': 'http://localhost:8000',
      '/data-summary': 'http://localhost:8000',
    }
  }
})
