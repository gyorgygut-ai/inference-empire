import { readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")

const models = [
  { dir: "flux2", contract: "flux2_klein9b", modelKey: "gpu-workers-flux2" },
  { dir: "tiny_sd", contract: "tiny_sd", modelKey: "gpu-workers-tiny-sd" }
]

function loadContract(modelKey) {
  try {
    const path = join(root, "dist", "apps", modelKey, "contract.json")
    return JSON.parse(readFileSync(path, "utf-8"))
  } catch { return null }
}

const providerManifest = {}
for (const model of models) {
  const c = loadContract(model.modelKey)
  providerManifest[model.contract] = {
    beam: c?.url ? { invokeUrl: c.url, taskApi: c.taskApi || "https://api.beam.cloud" } : null,
    flash: c?.url ? { baseUrl: c.url } : null,
    modal: c?.url ? { baseUrl: c.url } : null
  }
}

const token = process.env.ROUTER_SECRET || `router-${new Date().toISOString().slice(0,10)}-${Math.random().toString(36).slice(2,8)}`

const distOut = join(root, "dist", "apps", "worker-router")
mkdirSync(distOut, { recursive: true })
writeFileSync(join(distOut, "contract.json"), JSON.stringify({
  authToken: token,
  endpoints: {
    flux2: "https://worker-router-flux2.gyorgy-gutai.workers.dev",
    tiny_sd: "https://worker-router-tinysd.gyorgy-gutai.workers.dev"
  },
  providers: providerManifest
}, null, 2))

const srcOut = join(root, "apps", "worker-router", "src", "lib", "providers.generated.json")
mkdirSync(dirname(srcOut), { recursive: true })
writeFileSync(srcOut, JSON.stringify(providerManifest, null, 2) + "\n")

console.log(`wrote dist/apps/worker-router/contract.json + src/lib/providers.generated.json`)
