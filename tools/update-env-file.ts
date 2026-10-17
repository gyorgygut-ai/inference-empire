#!/usr/bin/env -S npx tsx
import { mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { lock } from 'proper-lockfile';

function upsert(content: string, key: string, value: string): string {
  const line = `${key}=${value}`;
  const lines = content.split('\n');
  const index = lines.findIndex((entry) => entry.startsWith(`${key}=`));
  if (index !== -1) {
    lines[index] = line;
    return lines.join('\n');
  }
  const base = content.length === 0 || content.endsWith('\n') ? content : `${content}\n`;
  return `${base}${line}\n`;
}

export async function updateEnvFile(target: string, key: string, value: string): Promise<void> {
  mkdirSync(dirname(target), { recursive: true });
  writeFileSync(target, '', { flag: 'a' });
  const release = await lock(target, {
    retries: { retries: 10, factor: 1.5, minTimeout: 20, maxTimeout: 200 },
  });
  try {
    const tmp = `${target}.${process.pid}.tmp`;
    writeFileSync(tmp, upsert(readFileSync(target, 'utf8'), key, value));
    renameSync(tmp, target);
  } finally {
    await release();
  }
}

if (process.argv[1]?.endsWith('update-env-file.ts')) {
  const [target, key, value] = process.argv.slice(2);
  if (!target || !key || value === undefined) {
    console.error('usage: update-env-file <file> <KEY> <value>');
    process.exit(1);
  }
  updateEnvFile(target, key, value).catch((error: unknown) => {
    console.error(`[update-env-file] ${String(error)}`);
    process.exit(1);
  });
}
