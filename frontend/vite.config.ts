import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), tailwindcss()],
  server: {
    proxy: {
      '/health': 'http://localhost:8000',
      '/games': {
        target: 'http://localhost:8000',
        bypass: (request) =>
          request.headers.accept?.includes('text/html')
            ? '/index.html'
            : undefined,
      },
      // Like /games: a browser asking for a page gets the app, so /pools/new is the editor, not JSON.
      '/pools': {
        target: 'http://localhost:8000',
        bypass: (request) =>
          request.headers.accept?.includes('text/html')
            ? '/index.html'
            : undefined,
      },
      '/socket.io': { target: 'http://localhost:8000', ws: true },
    },
  },
})
