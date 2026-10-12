import { existsSync, readFileSync } from 'node:fs';

const [srcFile, prefix] = process.argv.slice(2);
if (!srcFile || !prefix) {
  console.error('usage: prefix-env-vars.ts <src-file> <PREFIX>');
  process.exit(1);
}
if (!existsSync(srcFile)) {
  console.error(`[prefix-env-vars] missing: ${srcFile}`);
  process.exit(1);
}
for (const line of readFileSync(srcFile, 'utf8').split('\n')) {
  const trimmed = line.trim();
  if (trimmed.length === 0 || trimmed.startsWith('#')) {
    continue;
  }
  const eq = trimmed.indexOf('=');
  if (eq === -1) {
    continue;
  }
  const key = trimmed.slice(0, eq).trim();
  const value = trimmed.slice(eq + 1).trim();
  if (key.length > 0) {
    process.stdout.write(`${prefix}_${key}=${value}\n`);
  }
}
