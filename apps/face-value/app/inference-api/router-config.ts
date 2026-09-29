import { readFileSync } from "fs"
import { join } from "path"

let _config: { baseUrl: string; authToken: string }

function loadConfig(): { baseUrl: string; authToken: string } {
  if (_config) { return _config }
  const contractPath = join(process.cwd(), "dist", "apps", "flux2", "contract.json")
  const raw = readFileSync(contractPath, "utf-8")
  const contract = JSON.parse(raw)
  const baseUrl = contract.workerUrl || ""
  const authToken = process.env.FLUX2_ROUTER_TOKEN || ""
  if (!baseUrl) { throw new Error(`missing workerUrl in ${contractPath}`) }
  if (!authToken) { throw new Error("missing FLUX2_ROUTER_TOKEN env var") }
  _config = { baseUrl, authToken }
  return _config
}

export const workerRouterConfig = loadConfig()
