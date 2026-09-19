import { readFileSync } from "node:fs"
import { execSync } from "node:child_process"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..")
const contract = JSON.parse(readFileSync(join(root, "dist", "apps", "worker-router", "contract.json"), "utf-8"))

execSync(`echo "${contract.authToken}" | npx wrangler secret put AUTH_TOKEN`, { stdio: "inherit", cwd: process.cwd() })
execSync("npx wrangler deploy --env flux2", { stdio: "inherit", cwd: process.cwd() })
execSync("npx wrangler deploy --env tinysd", { stdio: "inherit", cwd: process.cwd() })
