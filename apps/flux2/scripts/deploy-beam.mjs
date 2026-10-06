import { readFileSync, mkdirSync, writeFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { exec } from "node:child_process";
import { promisify } from "node:util";

const execAsync = promisify(exec);

const root = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const handler = "apps/flux2/worker_beam_tq_flux2_klein9b.py:dispatch";
const outDir = join(root, "dist", "apps", "flux2");
mkdirSync(outDir, { recursive: true });
const providerPath = join(outDir, "provider.json");
const prev = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, "utf-8")) : {};
const command = `beam deploy ${handler} --json`;

let output;
try {
  const { stdout } = await execAsync(command, { cwd: root, maxBuffer: 1024 * 1024 });
  const clean = stdout.replace(/\u001b\[[0-9;?]*[A-Za-z]/g, "");
  const json = clean.slice(clean.indexOf("{"), clean.lastIndexOf("}") + 1);
  output = JSON.parse(json);
} catch (err) {
  const detail = (err.stdout || err.stderr || "").toString().trim();
  console.error(`Beam deploy failed: ${detail || err.message}`);
  process.exit(1);
}

const beamUrl = output.invoke_url;
const taskApi = "https://api.beam.cloud";

writeFileSync(providerPath, JSON.stringify({
  ...prev,
  beam: {
    url: beamUrl,
    taskApi: taskApi
  }
}, null, 2));
console.log(`wrote dist/apps/flux2/provider.json (beam url: ${beamUrl})`);