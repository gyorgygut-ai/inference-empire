import { readdirSync, readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const dir = dirname(fileURLToPath(import.meta.url));
for (const f of readdirSync(dir).filter((x) => x.endsWith(".json"))) {
  const c = JSON.parse(readFileSync(join(dir, f), "utf8"));
  for (const section of ["input", "output"]) {
    const s = c[section];
    if (!s || !Array.isArray(s.required) || s.required.length === 0)
      throw new Error(`${f}: ${section}.required must be non-empty`);
  }
}
console.log("contracts ok");
