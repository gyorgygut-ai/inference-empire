import { readdirSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { spawnSync } from "node:child_process"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const args = process.argv.slice(2)
const project = args[args.indexOf("--router") + 1]
if (!project) {
  console.error("[deploy-flash] --router is required")
  process.exit(1)
}
const family = project.endsWith("-router") ? project.slice(0, -"-router".length) : project

const familyDir = join(root, "apps", family)
const workers = readdirSync(familyDir).filter((file) => file.startsWith("worker_flash_cls_") && file.endsWith(".py"))
if (workers.length === 0) {
  console.log(`[deploy-flash] ${family} has no flash worker, nothing to deploy`)
  process.exit(0)
}
if (workers.length !== 1) {
  console.error(`[deploy-flash] expected exactly one flash worker in ${familyDir}, found ${workers.length}`)
  process.exit(1)
}

const name = family.replace(/_/g, "-")
const result = spawnSync("flash", ["deploy", "--app", name], { cwd: familyDir, encoding: "utf-8" })
if (result.status !== 0) {
  process.stderr.write(result.stderr || "")
  console.error(`[deploy-flash] flash deploy failed for ${family}`)
  process.exit(1)
}
const match = (result.stderr || "").match(/endpoint[_\s-]?id[:\s]+(\w+)/i)
const endpointId = match ? match[1] : name

console.log(`[deploy-flash] ${family} flash endpoint: ${endpointId} (store in router Vercel project env)`)
