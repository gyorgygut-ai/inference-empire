import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")
const py = readFileSync(join(root, "apps/realtime-voice/worker_beam_asgi_realtime_voice_qwen.py"), "utf-8")
const match = py.match(/name="(realtime-voice-[^"]+)"/)
const svc = match ? match[1] : null
if (!svc) throw new Error("no asgi name in realtime-voice beam worker")

const out = join(root, "dist", "apps", "realtime-voice")
mkdirSync(out, { recursive: true })
const providerPath = join(out, "provider.json")
const prev = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, "utf-8")) : {}
writeFileSync(providerPath, JSON.stringify({
  ...prev,
  beam: {
    url: `https://${svc}.app.beam.cloud`,
    taskApi: "https://api.beam.cloud"
  }
}, null, 2))
console.log(`wrote dist/apps/realtime-voice/provider.json (beam url: https://${svc}.app.beam.cloud)`)
