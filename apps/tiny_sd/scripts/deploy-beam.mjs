import { readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const yamlPath = join(root, "apps/tiny_sd/beam.yaml")
let project
try {
  const yaml = readFileSync(yamlPath, "utf-8")
  const match = yaml.match(/^project:\s*(.+)$/m)
  if (!match) throw new Error("no project in tiny_sd/beam.yaml")
  project = match[1].trim()
} catch {
  project = "tiny-sd"
}

const out = join(root, "dist", "apps", "gpu-workers-tiny-sd")
mkdirSync(out, { recursive: true })
writeFileSync(join(out, "contract.json"), JSON.stringify({
  url: `https://${project}.app.beam.cloud`,
  taskApi: "https://api.beam.cloud"
}, null, 2))
console.log(`wrote dist/apps/tiny_sd/contract.json (url: https://${project}.app.beam.cloud)`)
