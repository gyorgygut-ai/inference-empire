#!/usr/bin/env -S npx tsx
import { spawn } from 'node:child_process';

const [workerFile] = process.argv.slice(2);
if (!workerFile) {
  console.error('usage: deploy-modal.ts <worker_modal.py>');
  process.exit(1);
}

const child = spawn('uv', ['run', '--locked', 'modal', 'deploy', workerFile], {
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
