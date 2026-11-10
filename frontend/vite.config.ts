/// <reference types="vitest/config" />
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/health': 'http://localhost:8000',
    },
  },
  test: {
    environment: 'jsdom',
  },
})
