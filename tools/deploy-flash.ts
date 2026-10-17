#!/usr/bin/env -S npx tsx
import { dirname } from 'node:path';
import { spawn } from 'node:child_process';

const [workerFile] = process.argv.slice(2);
if (!workerFile) {
  console.error('usage: deploy-flash.ts <worker_flash.py>');
  process.exit(1);
}

const child = spawn('uv', ['run', '--locked', 'flash', 'deploy'], {
  cwd: dirname(workerFile),
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
    console.error('[deploy-flash] no flash URL found in output');
    process.exit(1);
  }
  console.log(seenUrl);
  process.exit(code ?? 0);
});
