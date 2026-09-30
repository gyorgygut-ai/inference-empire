import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")
const py = readFileSync(join(root, "apps/tiny_sd/worker_beam_tq_tiny_sd.py"), "utf-8")
const match = py.match(/name="(tiny-sd-[^"]+)"|name:\s*"([^"]+)"/)
const queue = match ? (match[1] || match[2]) : null
if (!queue) throw new Error("no task_queue name in tiny_sd beam worker")

const out = join(root, "dist", "apps", "tiny_sd")
mkdirSync(out, { recursive: true })
const providerPath = join(out, "provider.json")
const prev = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, "utf-8")) : {}
writeFileSync(providerPath, JSON.stringify({
  ...prev,
  beam: {
    url: `https://${queue}.app.beam.cloud`,
    taskApi: "https://api.beam.cloud"
  }
}, null, 2))
console.log(`wrote dist/apps/tiny_sd/provider.json (beam url: https://${queue}.app.beam.cloud)`)
