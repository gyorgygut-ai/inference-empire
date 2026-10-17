#!/usr/bin/env -S npx tsx
import { existsSync, readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { spawn } from 'node:child_process';

const raw = process.argv.slice(2);
let worker = '';
for (const arg of raw) {
  if (arg.startsWith('--worker=')) worker = arg.slice('--worker='.length);
}
if (!worker) {
  console.error('usage: deploy-flash.ts --worker=<path|glob.py>');
  process.exit(1);
}

function resolveWorker(spec: string): string {
  if (!spec.includes('*')) {
    return spec;
  }
  const dir = dirname(spec);
  const pattern = new RegExp(`^${spec.slice(dir.length + 1).replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*/g, '.*')}$`);
  const matches = readdirSync(dir).filter((name) => pattern.test(name));
  if (matches.length !== 1) {
    console.error(`[deploy-flash] expected one worker matching ${spec}, found ${matches.length}`);
    process.exit(1);
  }
  return join(dir, matches[0] ?? '');
}

const workerFile = resolveWorker(worker);
const dir = dirname(workerFile);
if (!existsSync(dir)) {
  console.error(`[deploy-flash] missing worker dir: ${dir}`);
  process.exit(1);
}

const child = spawn('uv', ['run', '--locked', 'flash', 'deploy'], {
  cwd: dir,
  stdio: ['inherit', 'pipe', 'pipe'],
});

const urlPattern = /https:\/\/[^\s'"`]+/;
let seenUrl: string | null = null;

function scan(chunk: Buffer): void {
  if (seenUrl) {
    return;
  }
  const clean = chunk.toString('utf8').replace(/\x1b\[[0-9;]*m/g, '');
  const match = urlPattern.exec(clean);
  if (match) {
    seenUrl = match[0].replace(/[.,;)]+$/, '');
  }
}

child.stdout?.on('data', (chunk: Buffer) => {
  process.stderr.write(chunk);
  scan(chunk);
});
child.stderr?.on('data', (chunk: Buffer) => {
  process.stderr.write(chunk);
  scan(chunk);
});
child.on('error', (err) => {
  console.error(`[deploy-flash] failed to start flash: ${err.message}`);
  process.exit(1);
});
child.on('close', (code) => {
  if (!seenUrl) {
    const fallback = process.env.FLASH_URL ?? '';
    if (fallback) {
      seenUrl = fallback;
    }
  }
  if (seenUrl) {
    console.log(seenUrl);
  } else {
    console.error('[deploy-flash] no flash URL found in output');
    process.exit(1);
  }
  process.exit(code ?? 0);
});
