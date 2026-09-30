import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")
const py = readFileSync(join(root, "apps/h3_comfy/worker_modal_cls_minimax_h3_comfy.py"), "utf-8")
const appMatch = py.match(/modal\.App\("([^"]+)"\)/)
const clsMatch = py.match(/class\s+(\w+).*(?=generate)/s)
if (!appMatch) throw new Error("no modal.App in h3_comfy worker")

const app = appMatch[1]
const cls = clsMatch ? clsMatch[1] : "MiniMaxH3ComfyWorker"
const out = join(root, "dist", "apps", "h3_comfy")
mkdirSync(out, { recursive: true })
const providerPath = join(out, "provider.json")
const prev = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, "utf-8")) : {}
writeFileSync(providerPath, JSON.stringify({
  ...prev,
  modal: {
    url: `https://${app}--queue-api.modal.run`,
    app, cls
  }
}, null, 2))
console.log(`wrote dist/apps/h3_comfy/provider.json (modal app: ${app}, cls: ${cls})`)
