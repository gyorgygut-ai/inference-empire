import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['apps/face-value/tests/**/*.coverage.spec.ts'],
    testTimeout: 600_000,
    hookTimeout: 120_000,
  },
})
