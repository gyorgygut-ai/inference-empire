import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")
const py = readFileSync(join(root, "apps/flux2/worker_modal_cls_flux2_klein9b.py"), "utf-8")
const appMatch = py.match(/modal\.App\("([^"]+)"\)/)
const clsMatch = py.match(/class\s+(\w+).*(?=generate)/s)
if (!appMatch) throw new Error("no modal.App in flux2 worker")

const app = appMatch[1]
const cls = clsMatch ? clsMatch[1] : "FluxKleinWorker"
const out = join(root, "dist", "apps", "flux2")
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
console.log(`wrote dist/apps/flux2/provider.json (modal app: ${app}, cls: ${cls})`)
