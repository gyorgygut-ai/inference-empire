import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const [project, configuration, ...pairs] = process.argv.slice(2);
const updates = new Map<string, string>();
for (const pair of pairs) {
  const eq = pair.indexOf('=');
  if (!project || (configuration !== 'dev' && configuration !== 'deploy') || eq === -1) {
    console.error('usage: upsert-artifact.ts <project> <dev|deploy> KEY=VAL...');
    process.exit(1);
  }
  updates.set(pair.slice(0, eq), pair.slice(eq + 1));
}

const outDir = join(process.cwd(), 'dist', project, configuration);
mkdirSync(outDir, { recursive: true });
for (const [key, value] of updates) {
  const outPath = join(outDir, key);
  writeFileSync(outPath, value.replace(/\x1b\[[0-9;]*m/g, '').trim());
  console.log(`[upsert-artifact] wrote ${outPath}`);
}
