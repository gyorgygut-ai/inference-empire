import { defineConfig } from 'vitest/config';

export default defineConfig({
  root: import.meta.dirname,
  test: {
    globals: false,
    environment: 'node',
    include: ['*.test.ts'],
    watch: false,
    passWithNoTests: false,
  },
});
