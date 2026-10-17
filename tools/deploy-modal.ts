#!/usr/bin/env -S npx tsx
import { readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { spawn } from 'node:child_process';

const raw = process.argv.slice(2);
let worker = '';
let mode = 'deploy';
for (const arg of raw) {
  if (arg.startsWith('--worker=')) worker = arg.slice('--worker='.length);
  else if (arg.startsWith('--mode=')) mode = arg.slice('--mode='.length);
}
if (!worker || (mode !== 'dev' && mode !== 'deploy')) {
  console.error('usage: deploy-modal.ts --worker=<path|glob.py> [--mode=dev|deploy]');
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
    console.error(`[deploy-modal] expected one worker matching ${spec}, found ${matches.length}`);
    process.exit(1);
  }
  return join(dir, matches[0] ?? '');
}

const workerFile = resolveWorker(worker);
const subcommand = mode === 'dev' ? 'serve' : 'deploy';
const child = spawn('uv', ['run', '--locked', 'modal', subcommand, workerFile], {
  stdio: ['inherit', 'pipe', 'pipe'],
});

const urlPattern = /https:\/\/[^\s'"`]*\.modal\.run[^\s'"`]*/;
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
  console.error(`[deploy-modal] failed to start modal: ${err.message}`);
  process.exit(1);
});
child.on('close', (code) => {
  if (!seenUrl) {
    console.error('[deploy-modal] no modal URL found in output');
    process.exit(1);
  }
  console.log(seenUrl);
  process.exit(code ?? 0);
});
