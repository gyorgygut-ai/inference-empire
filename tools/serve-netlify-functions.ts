#!/usr/bin/env -S npx tsx
import { spawn } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { emitReadySignal } = require('/Users/gyorgygutai/Projects/personal/inference-empire/node_modules/nx/dist/src/tasks-runner/readiness/ready-signal');

const functionsRoot = join(process.cwd(), 'apps', 'functions');
const workerEnvFile = join(process.cwd(), 'dist', 'workers-flux2', 'deploy.env');

if (existsSync(workerEnvFile)) {
  process.loadEnvFile(workerEnvFile);
}

const netlifyToml = readFileSync(join(functionsRoot, 'netlify.toml'), 'utf8');
const devTable = /\[dev\]([\s\S]*?)(?=\n\[|$)/.exec(netlifyToml)?.[1] ?? '';
const port = Number(/port\s*=\s*(\d+)/.exec(devTable)?.[1]);

if (!port) {
  console.error('[serve-netlify-functions] no [dev] port in apps/functions/netlify.toml');
  process.exit(1);
}

const child = spawn('npx', ['netlify', 'dev', '--port', String(port)], {
  cwd: functionsRoot,
  stdio: ['ignore', 'pipe', 'pipe'],
});

let ready = false;
child.stdout?.on('data', (chunk: Buffer) => {
  process.stdout.write(chunk.toString());
  if (!ready && chunk.toString().includes('Functions server is listening on')) {
    ready = true;
    emitReadySignal(`http://localhost:${port}`);
  }
});

for (const signal of ['SIGINT', 'SIGTERM'] as const) {
  process.on(signal, () => child.kill(signal));
}

child.on('exit', (code) => process.exit(code ?? 1));

await new Promise<void>((resolve) => child.on('exit', () => resolve()));
