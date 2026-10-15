#!/usr/bin/env -S npx tsx
import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';

const argv = process.argv.slice(2);
const separator = argv.indexOf('--');
if (separator === -1 || separator === argv.length - 1) {
  console.error('usage: export-artifacts.ts [--exclude NAME]… <dir>… -- <command> [args…]');
  process.exit(1);
}

const excludes = new Set<string>();
const dirs: string[] = [];
for (let i = 0; i < separator; i++) {
  const token = argv[i] ?? '';
  if (token === '--exclude') {
    excludes.add(argv[++i] ?? '');
  } else {
    dirs.push(token);
  }
}
if (dirs.length === 0) {
  console.error('[export-artifacts] no artifact directories given');
  process.exit(1);
}

const VAR_NAME = /^[A-Z][A-Z0-9_]*$/;
const exported = new Set<string>();

for (const dir of dirs) {
  if (!existsSync(dir)) {
    console.error(`[export-artifacts] missing artifact directory: ${dir}`);
    process.exit(1);
  }
  let count = 0;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isFile() || !VAR_NAME.test(entry.name) || excludes.has(entry.name)) {
      continue;
    }
    process.env[entry.name] = readFileSync(join(dir, entry.name), 'utf8').trim();
    exported.add(entry.name);
    count++;
  }
  if (count === 0) {
    console.error(`[export-artifacts] no artifacts found in: ${dir}`);
    process.exit(1);
  }
}

console.error(`[export-artifacts] exported: ${[...exported].sort().join(' ')}`);

const [cmd, ...args] = argv.slice(separator + 1);
const result = spawnSync(cmd ?? '', args, { stdio: 'inherit', env: process.env });
if (result.error) {
  console.error(`[export-artifacts] failed to start ${cmd}: ${result.error.message}`);
  process.exit(1);
}
process.exit(result.status ?? 1);
