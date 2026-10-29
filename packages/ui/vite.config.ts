import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  resolve: {
    tsconfigPaths: true,
  },
  root: __dirname,
  cacheDir: '../../node_modules/.vite/packages/ui',
  plugins: [react()],
  test: {
    globals: true,
    cache: {
      dir: '../../node_modules/.vitest'
    },
    environment: 'jsdom',
    include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mjs,cts,jsx,tsx}'],
    reporters: ['default'],
    watch: false,
    passWithNoTests: true
  }
})