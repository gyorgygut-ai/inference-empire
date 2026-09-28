import { readFileSync } from "fs"
import { join } from "path"

let _config: { baseUrl: string; token: string }

function loadConfig(): { baseUrl: string; token: string } {
  if (_config) {return _config}
  try {
    const contractPath = join(process.cwd(), "dist", "apps", "worker-router", "contract.json")
    const raw = readFileSync(contractPath, "utf-8")
    const contract = JSON.parse(raw)
    const entry = contract?.endpoints?.["flux2_klein9b"]
    _config = {
      baseUrl: entry?.url || "",
      token: entry?.token || "",
    }
  } catch {
    _config = { baseUrl: "", token: "" }
  }
  return _config
}

export const workerRouterConfig = loadConfig()
