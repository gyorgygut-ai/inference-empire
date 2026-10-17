#!/usr/bin/env -S npx tsx
import { readdirSync, readFileSync } from 'node:fs';
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
  console.error('usage: deploy-beam.ts --worker=<path|glob.py> [--mode=dev|deploy]');
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
    console.error(`[deploy-beam] expected one worker matching ${spec}, found ${matches.length}`);
    process.exit(1);
  }
  return join(dir, matches[0] ?? '');
}

const workerFile = resolveWorker(worker);
const dir = dirname(workerFile);
let handlerName: string | null = null;
try {
  const content = readFileSync(workerFile, 'utf8');
  const match = /@task_queue\([\s\S]*?\)\s*\n\s*def\s+(\w+)/.exec(content);
  if (match) handlerName = match[1];
} catch {
  handlerName = null;
}
if (!handlerName) {
  console.error(`[deploy-beam] could not find @task_queue handler in ${workerFile}`);
  process.exit(1);
}
const subcommand = mode === 'dev' ? 'serve' : 'deploy';
const child = spawn('uv', ['run', '--locked', 'beam', subcommand, `${workerFile}:${handlerName}`], {
  cwd: dir,
  stdio: ['inherit', 'pipe', 'pipe'],
});

const urlPattern = /https:\/\/[^\s'"]+/;
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
  console.error(`[deploy-beam] failed to start beam: ${err.message}`);
  process.exit(1);
});
child.on('close', (code) => {
  if (!seenUrl) {
    const fallback = process.env.BEAM_URL ?? '';
    if (fallback) {
      seenUrl = fallback;
    }
  }
  if (seenUrl) {
    console.log(seenUrl);
  } else {
    console.error('[deploy-beam] no beam URL found in output');
    process.exit(1);
  }
  process.exit(code ?? 0);
});
