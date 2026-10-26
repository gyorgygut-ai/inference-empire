import { defineConfig } from 'vitest/config'

export default defineConfig({
  root: import.meta.dirname,
  resolve: { tsconfigPaths: false },
  test: { environment: 'node', include: ['src/**/*.test.ts', '../../tools/functions-runtime.test.ts'], watch: false, passWithNoTests: false },
})
