import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import Icons from 'unplugin-icons/vite'
import customIcons from './icons/icons.json'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    Icons({
      compiler: 'jsx',
      jsx: 'react',
      customCollections: {
        // Custom icons for the EditEngine project
        'custom': customIcons,
      },
    }),
  ],
  base: '/static/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    manifest: 'manifest.json',
    rollupOptions: {
      input: 'src/main.tsx',
    },
  },
  server: {
    host: 'localhost',
    port: 5173,
    cors: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
