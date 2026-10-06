import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")
const py = readFileSync(join(root, "apps/realtime-voice/worker_modal_cls_realtime_voice_qwen.py"), "utf-8")
const appMatch = py.match(/modal\.App\("([^"]+)"\)/)
const clsMatch = py.match(/class\s+(\w+Worker)/)
if (!appMatch) throw new Error("no modal.App in realtime-voice worker")

const app = appMatch[1]
const cls = clsMatch ? clsMatch[1] : "RealtimeVoiceWorker"
const out = join(root, "dist", "apps", "realtime-voice")
mkdirSync(out, { recursive: true })
const providerPath = join(out, "provider.json")
const prev = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, "utf-8")) : {}
writeFileSync(providerPath, JSON.stringify({
  ...prev,
  modal: {
    url: `https://${app}--web.modal.run`,
    app, cls, asgi: "web"
  }
}, null, 2))
console.log(`wrote dist/apps/realtime-voice/provider.json (modal app: ${app}, cls: ${cls}, asgi: web)`)
