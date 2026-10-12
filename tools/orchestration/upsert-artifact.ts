import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

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

const outPath = join(process.cwd(), 'dist', project, `${configuration}.env`);
mkdirSync(dirname(outPath), { recursive: true });
const order: string[] = [];
const values = new Map<string, string>();
if (existsSync(outPath)) {
  for (const line of readFileSync(outPath, 'utf8').split('\n')) {
    const eq = line.indexOf('=');
    if (eq === -1) continue;
    const key = line.slice(0, eq).trim();
    if (!values.has(key)) order.push(key);
    values.set(key, line.slice(eq + 1).trim());
  }
}
for (const [key, value] of updates) {
  if (!values.has(key)) order.push(key);
  values.set(key, value);
}
writeFileSync(outPath, order.map((key) => `${key}=${values.get(key)}`).join('\n') + '\n');
console.log(`[upsert-artifact] wrote ${outPath}`);
