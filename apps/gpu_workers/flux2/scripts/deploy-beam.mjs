import { readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const yaml = readFileSync(join(root, "apps/gpu-workers/flux2/beam.yaml"), "utf-8")
const match = yaml.match(/^project:\s*(.+)$/m)
if (!match) throw new Error("no project in flux2/beam.yaml")

const project = match[1].trim()
const out = join(root, "dist", "apps", "gpu-workers-flux2")
mkdirSync(out, { recursive: true })
writeFileSync(join(out, "contract.json"), JSON.stringify({
  url: `https://${project}.app.beam.cloud`,
  taskApi: "https://api.beam.cloud"
}, null, 2))
console.log(`wrote dist/apps/gpu-workers-flux2/contract.json (url: https://${project}.app.beam.cloud)`)
