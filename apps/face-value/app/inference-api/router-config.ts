import { readFileSync } from "fs"
import { join } from "path"

let _config: { baseUrl: string; authToken: string }

function loadConfig(): { baseUrl: string; authToken: string } {
  if (_config) { return _config }
  try {
    const contractPath = join(process.cwd(), "dist", "apps", "worker-router", "contract.json")
    const raw = readFileSync(contractPath, "utf-8")
    const contract = JSON.parse(raw)
    _config = {
      baseUrl: contract.provider?.url || contract.url || "",
      authToken: contract.authToken || "",
    }
  } catch {
    _config = { baseUrl: "", authToken: "" }
  }
  return _config
}

export const workerRouterConfig = loadConfig()
