import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['tests/**/*.e2e.spec.ts'],
    testTimeout: 600_000,
    hookTimeout: 120_000,
  },
})
