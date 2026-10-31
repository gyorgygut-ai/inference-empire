import { defineConfig } from "vitest/config"

export default defineConfig({
  test: {
    environment: "node",
    include: ["apps/voice-chat/tests/**/*.test.ts"],
  },
})
