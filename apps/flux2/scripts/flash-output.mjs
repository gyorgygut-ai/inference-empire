import { readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const endpointId = readFileSync(join(root, "apps/flux2/.flash_endpoint_id"), "utf-8").trim()
const out = join(root, "dist", "apps", "gpu-workers-flux2")
mkdirSync(out, { recursive: true })
writeFileSync(join(out, "contract.json"), JSON.stringify({
  url: `https://endpoints.runpod.io/v2/${endpointId}`,
  endpointId
}, null, 2))
console.log(`wrote dist/apps/flux2/contract.json (endpoint: ${endpointId})`)
