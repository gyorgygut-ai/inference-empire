import { defineConfig } from 'vite';
import { tanstackStart } from '@tanstack/react-start/plugin/vite';
import tailwindcss from '@tailwindcss/vite';
import viteReact from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [
    tailwindcss(),
    tanstackStart({
      target: 'server',
    }),
    // Required for React Fast Refresh in TanStack Start dev mode. Must come after tanstackStart().
    viteReact(),
  ],
});
