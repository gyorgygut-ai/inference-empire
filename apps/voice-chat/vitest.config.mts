import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { join } from 'node:path';

export default defineConfig(() => ({
  root: import.meta.dirname,
  cacheDir: '../../node_modules/.vite/apps/voice-chat',
  plugins: [react()],
  resolve: {
    alias: {
      '@inference/contracts': join(import.meta.dirname, '../../packages/contracts/src/index.ts'),
      '@inference/types': join(import.meta.dirname, '../../packages/types/src/index.ts'),
      '@inference/workspace-plugin': join(import.meta.dirname, '../.././tools/workspace-plugin/src/index.ts'),
    },
  },
  test: {
    name: 'voice-chat',
    watch: false,
    globals: true,
    environment: 'jsdom',
    include: ['{src,app,pages,specs}/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
    reporters: ['default'],
    coverage: {
      reportsDirectory: '../../coverage/apps/voice-chat',
      provider: 'v8' as const,
    }
  },
}));
