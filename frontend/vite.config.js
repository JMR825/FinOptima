import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/FinOptima/',
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: VITE_API_URL,
        changeOrigin: true,
      },
    },
  },
})