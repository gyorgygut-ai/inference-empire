import { readFileSync, readdirSync, mkdirSync, writeFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { execSync } from "node:child_process"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const args = process.argv.slice(2)
const project = args[args.indexOf("--router") + 1]
if (!project) {
  console.error("[deploy-beam] --router is required")
  process.exit(1)
}
const family = project.endsWith("-router") ? project.slice(0, -"-router".length) : project

const familyDir = join(root, "apps", family)
const workers = readdirSync(familyDir).filter((file) => file.startsWith("worker_beam_") && file.endsWith(".py"))
if (workers.length !== 1) {
  console.error(`[deploy-beam] expected exactly one beam worker in ${familyDir}, found ${workers.length}`)
  process.exit(1)
}
const worker = workers[0]

const outDir = join(root, "dist", "apps", family)
mkdirSync(outDir, { recursive: true })
const providerPath = join(outDir, "provider.json")
const prev = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, "utf-8")) : {}

let beam
if (worker.startsWith("worker_beam_tq_")) {
  const handler = `apps/${family}/${worker}:dispatch`
  let stdout
  try {
    stdout = execSync(`beam deploy ${handler} --json`, { cwd: root, encoding: "utf-8", maxBuffer: 1024 * 1024 })
  } catch (err) {
    const detail = (err.stdout || err.stderr || "").toString().trim()
    console.error(`Beam deploy failed: ${detail || err.message}`)
    process.exit(1)
  }
  const clean = stdout.replace(/\u001b\[[0-9;?]*[A-Za-z]/g, "")
  const output = JSON.parse(clean.slice(clean.indexOf("{"), clean.lastIndexOf("}") + 1))
  beam = { url: output.invoke_url, taskApi: "https://api.beam.cloud" }
} else {
  const source = readFileSync(join(familyDir, worker), "utf-8")
  const match = source.match(/name="([^"]+)"/)
  if (!match) {
    console.error(`[deploy-beam] no service name in ${worker}`)
    process.exit(1)
  }
  beam = { url: `https://${match[1]}.app.beam.cloud`, taskApi: "https://api.beam.cloud" }
}

writeFileSync(providerPath, JSON.stringify({ ...prev, beam }, null, 2))
console.log(`wrote dist/apps/${family}/provider.json (beam url: ${beam.url})`)
