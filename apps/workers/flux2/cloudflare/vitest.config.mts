import { defineConfig } from 'vitest/config'
import { fileURLToPath } from 'node:url'

export default defineConfig({
  root: fileURLToPath(new URL('.', import.meta.url)),
  tsconfig: './tsconfig.json',
  resolve: {
    alias: {
      'cloudflare:workers': fileURLToPath(new URL('./src/cloudflare-workers.mock.ts', import.meta.url)),
    },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
