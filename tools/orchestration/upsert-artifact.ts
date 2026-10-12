import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

const [project, configuration, target, ...pairs] = process.argv.slice(2);
if (!project || !configuration || !target || pairs.length === 0) {
  console.error('usage: upsert-artifact.ts <project> <configuration> <target> KEY=VAL...');
  process.exit(1);
}
for (const pair of pairs) {
  if (!pair.includes('=')) {
    console.error(`[upsert-artifact] bad pair: ${pair}`);
    process.exit(1);
  }
}

const outPath = join(process.cwd(), 'dist', project, configuration, `${target}.env`);
mkdirSync(dirname(outPath), { recursive: true });
const existing = existsSync(outPath) ? readFileSync(outPath, 'utf8') : '';
const lines = existing.length > 0 ? existing.split('\n') : [];
const updates = new Map(pairs.map((p) => [p.slice(0, p.indexOf('=')), p.slice(p.indexOf('=') + 1)]));
const next = lines.map((line) => {
  const eq = line.indexOf('=');
  if (eq === -1) {
    return line;
  }
  const key = line.slice(0, eq).trim();
  if (updates.has(key)) {
    return `${key}=${updates.get(key)}`;
  }
  return line;
});
for (const [key, value] of updates) {
  if (!next.some((line) => line.trim().startsWith(`${key}=`))) {
    next.push(`${key}=${value}`);
  }
}
const seen = new Set<string>();
const deduped: string[] = [];
for (let i = next.length - 1; i >= 0; i--) {
  const eq = next[i].indexOf('=');
  if (eq === -1) {
    deduped.unshift(next[i]);
    continue;
  }
  const key = next[i].slice(0, eq).trim();
  if (seen.has(key)) {
    continue;
  }
  seen.add(key);
  deduped.unshift(next[i]);
}
const body = deduped.join('\n');
writeFileSync(outPath, body.endsWith('\n') ? body : `${body}\n`);
console.log(`[upsert-artifact] wrote ${outPath}`);
