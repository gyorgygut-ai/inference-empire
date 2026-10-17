import { defineConfig } from 'vitest/config';
import { nxViteTsPaths } from '@nx/vite/plugins/nx-tsconfig-paths.plugin';

export default defineConfig(() => ({
  root: import.meta.dirname,
  cacheDir: '../../node_modules/.vite/tools/orchestrator',
  plugins: [nxViteTsPaths()],
  test: {
    name: 'orchestrator',
    watch: false,
    globals: true,
    environment: 'node',
    include: ['**/*.{test,spec}.ts'],
    reporters: ['default'],
    coverage: {
      reportsDirectory: '../../coverage/tools/orchestrator',
      provider: 'v8' as const,
    },
  },
}));
