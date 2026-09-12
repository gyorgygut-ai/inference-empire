import { readdirSync, readFileSync, mkdirSync, writeFileSync } from "node:fs"
import { join, basename, resolve, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)

const workersDir = resolve(__dirname, "../../../workers")
const outPath = resolve(__dirname, "../src/lib/manifest.json")

function walk(dir, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) walk(full, out)
    else out.push(full)
  }
  return out
}

const allFiles = walk(workersDir)
const workerFiles = allFiles.filter((p) => /^worker_.*\.py$/.test(basename(p)))
const contractFiles = allFiles.filter((p) => p.includes("/contracts/") && p.endsWith(".json"))

const contractMap = new Map()
for (const p of contractFiles) {
  const model = basename(p, ".json")
  contractMap.set(model, p)
}

const workers = []

for (const file of workerFiles) {
  const stem = basename(file, ".py")
  if (!stem.startsWith("worker_")) continue
  const rest = stem.slice("worker_".length)
  const parts = rest.split("_")
  if (parts.length < 3) continue
  const platform = parts[0]
  const pattern = parts[1]
  const model = parts.slice(2).join("_")

  let contractPath = contractMap.get(model)
  if (!contractPath && model === "voice_chat") contractPath = contractMap.get("realtime_voice_chat")
  if (!contractPath) {
    throw new Error(`missing contract for model ${model} (stem ${stem})`)
  }

  const contract = JSON.parse(readFileSync(contractPath, "utf8"))
  const required = contract.input?.required ?? []
  const properties = contract.input?.properties ?? {}

  const fields = {}
  for (const [key, prop] of Object.entries(properties)) {
    const field = {}
    if (prop.default !== undefined) field.default = prop.default
    else field.default = null
    if (prop.maxItems !== undefined) field.maxItems = prop.maxItems
    fields[key] = field
  }

  workers.push({
    stem,
    platform,
    pattern,
    model,
    inputs: {
      required,
      fields,
    },
  })
}

workers.sort((a, b) => a.stem.localeCompare(b.stem))

mkdirSync(dirname(outPath), { recursive: true })
writeFileSync(outPath, JSON.stringify({ workers }, null, 2) + "\n")
console.log(`wrote ${workers.length} workers to ${outPath}`)
