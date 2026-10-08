import { readFileSync } from "fs"
import { join } from "path"

let configCache: { baseUrl: string; authToken: string }

function loadConfig(): { baseUrl: string; authToken: string } {
  if (configCache) { return configCache }
  const envUrl = process.env.FLUX2_ROUTER_URL || ""
  let baseUrl = envUrl
  if (!baseUrl) {
    const contractPath = join(process.cwd(), "dist", "apps", "flux2", "contract.json")
    const raw = readFileSync(contractPath, "utf-8")
    const contract = JSON.parse(raw)
    baseUrl = contract.workerUrl || ""
    if (!baseUrl) { throw new Error(`missing workerUrl in ${contractPath}`) }
  }
  const authToken = process.env.FLUX2_ROUTER_TOKEN || ""
  if (!authToken) { throw new Error("missing FLUX2_ROUTER_TOKEN env var") }
  configCache = { baseUrl, authToken }
  return configCache
}

export const workerRouterConfig = {
  get baseUrl(): string { return loadConfig().baseUrl },
  get authToken(): string { return loadConfig().authToken },
}
