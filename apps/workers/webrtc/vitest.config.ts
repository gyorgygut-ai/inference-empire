import { defineConfig } from 'vitest/config'

export default defineConfig({
  test: {
    environment: 'node',
    include: ['apps/workers/webrtc/tests/**/*.test.ts'],
    fileParallelism: false,
    testTimeout: 60000,
  },
})
