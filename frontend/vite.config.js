import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3050,
    proxy: {
      '/api': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/login': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/logout': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/verify': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/change-password': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/agents': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/team': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/tasks': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/notes': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/kb': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/calendar': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/activity': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/scheduled': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
      '/stats': {
        target: 'http://localhost:8091',
        changeOrigin: true,
      },
    },
  },
})
