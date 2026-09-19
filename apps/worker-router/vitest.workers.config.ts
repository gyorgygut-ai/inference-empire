import { cloudflareTest } from "@cloudflare/vitest-pool-workers"
import { defineConfig } from "vitest/config"

export default defineConfig({
  plugins: [
    cloudflareTest({
      wrangler: { configPath: "./wrangler.jsonc" },
      miniflare: {
        compatibilityDate: "2026-08-22",
        bindings: {
          AUTH_TOKEN: "secret",
          BEAM_BASIC_TOKEN: "basic-test",
          BEAM_BEARER_TOKEN: "bearer-test",
          RUNPOD_API_KEY: "key-test",
          WRAPPER_TOKEN: "wrap-test"
        }
      }
    })
  ],
  test: {
    include: ["tests/**/*.test.ts"]
  }
})
