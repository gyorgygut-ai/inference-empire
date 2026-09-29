import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const endpointId = readFileSync(join(root, "apps/flux2/.flash_endpoint_id"), "utf-8").trim()
const out = join(root, "dist", "apps", "flux2")
mkdirSync(out, { recursive: true })
const providerPath = join(out, "provider.json")
const prev = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, "utf-8")) : {}
writeFileSync(providerPath, JSON.stringify({
  ...prev,
  flash: {
    url: `https://endpoints.runpod.io/v2/${endpointId}`,
    endpointId
  }
}, null, 2))
console.log(`wrote dist/apps/flux2/provider.json (flash endpoint: ${endpointId})`)
