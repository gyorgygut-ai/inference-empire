import { defineConfig, globalIgnores } from "eslint/config"
import nextVitals from "eslint-config-next/core-web-vitals"
import nextTs from "eslint-config-next/typescript"

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  globalIgnores(["dist/**", "worker-configuration.d.ts"]),
  {
    rules: {
      semi: ["error", "never"]
    }
  }
])

export default eslintConfig
