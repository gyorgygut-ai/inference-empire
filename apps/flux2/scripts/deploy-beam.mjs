import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const yaml = readFileSync(join(root, "apps/flux2/beam.yaml"), "utf-8")
const match = yaml.match(/^project:\s*(.+)$/m)
if (!match) throw new Error("no project in flux2/beam.yaml")

const project = match[1].trim()
const out = join(root, "dist", "apps", "flux2")
mkdirSync(out, { recursive: true })
const providerPath = join(out, "provider.json")
const prev = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, "utf-8")) : {}
writeFileSync(providerPath, JSON.stringify({
  ...prev,
  beam: {
    url: `https://${project}.app.beam.cloud`,
    taskApi: "https://api.beam.cloud"
  }
}, null, 2))
console.log(`wrote dist/apps/flux2/provider.json (beam url: https://${project}.app.beam.cloud)`)
