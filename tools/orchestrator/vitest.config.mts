import { defineConfig } from 'vitest/config'

export default defineConfig(() => ({
  root: import.meta.dirname,
  cacheDir: '../../node_modules/.vite/tools/orchestrator',
  resolve: { tsconfigPaths: true },
  test: {
    name: 'orchestrator',
    watch: false,
    globals: true,
    environment: 'node',
    include: ['**/*.{test,spec}.ts'],
    passWithNoTests: true,
    reporters: ['default'],
    coverage: {
      reportsDirectory: '../../coverage/tools/orchestrator',
      provider: 'v8' as const,
    },
  },
}))
