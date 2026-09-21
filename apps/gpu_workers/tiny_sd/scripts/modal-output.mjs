import { readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const py = readFileSync(join(root, "apps/gpu-workers/tiny_sd/worker_modal_cls_tiny_sd.py"), "utf-8")
const appMatch = py.match(/modal\.App\("([^"]+)"\)/)
const clsMatch = py.match(/class\s+(\w+).*(?=generate)/s)
if (!appMatch) throw new Error("no modal.App in tiny_sd worker")

const app = appMatch[1]
const cls = clsMatch ? clsMatch[1] : "TinySDWorker"
const out = join(root, "dist", "apps", "gpu-workers-tiny-sd")
mkdirSync(out, { recursive: true })
writeFileSync(join(out, "contract.json"), JSON.stringify({
  url: `https://${app}--queue-api.modal.run`,
  app, cls
}, null, 2))
console.log(`wrote dist/apps/gpu-workers-tiny-sd/contract.json (app: ${app}, cls: ${cls})`)
