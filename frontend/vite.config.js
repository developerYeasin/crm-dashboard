import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3050,
    proxy: {
      '/api': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/api/ai': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/login': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/logout': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/verify': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/change-password': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/agents': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/team': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/tasks': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/notes': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/kb': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/calendar': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/activity': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/scheduled': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
      '/stats': {
        target: 'http://localhost:8087',
        changeOrigin: true,
      },
    },
  },
})
