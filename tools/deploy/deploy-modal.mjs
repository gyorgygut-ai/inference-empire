import { readdirSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import { spawnSync } from "node:child_process"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..")
const args = process.argv.slice(2)
const project = args[args.indexOf("--router") + 1]
if (!project) {
  console.error("[deploy-modal] --router is required")
  process.exit(1)
}
const family = project.endsWith("-router") ? project.slice(0, -"-router".length) : project

const familyDir = join(root, "apps", family)
const workers = readdirSync(familyDir).filter((file) => file.startsWith("worker_modal_cls_") && file.endsWith(".py"))
if (workers.length !== 1) {
  console.error(`[deploy-modal] expected exactly one modal worker in ${familyDir}, found ${workers.length}`)
  process.exit(1)
}

// The bridge URL lives in the family contract; this script only ships the Modal app.
const result = spawnSync("uv", ["run", "--locked", "modal", "deploy", `apps/${family}/${workers[0]}`], {
  cwd: root,
  env: { ...process.env, PYTHONPATH: root },
  stdio: "inherit"
})
process.exit(result.status ?? 1)
