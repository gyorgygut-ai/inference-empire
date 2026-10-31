import { defineConfig } from 'vitest/config'

export default defineConfig({
  root: import.meta.dirname,
  tsconfig: './tsconfig.app.json',
  resolve: { tsconfigPaths: false },
  test: { environment: 'node', include: ['src/**/*.test.ts'], watch: false, passWithNoTests: false },
})
