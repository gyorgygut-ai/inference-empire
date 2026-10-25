#!/usr/bin/env -S npx tsx
import { dirname } from 'node:path';
import { spawn as defaultSpawn, type ChildProcess } from 'node:child_process';

export interface DeployFlashOptions {
  spawnImpl?: typeof defaultSpawn;
  consoleLog?: (...args: any[]) => void;
  processExit?: (code?: number) => never;
}

export async function run(workerFile: string, options: DeployFlashOptions = {}): Promise<void> {
  const { spawnImpl = defaultSpawn, consoleLog = console.log, processExit = process.exit } = options;

  const child = spawnImpl('uv', ['run', '--locked', 'flash', 'deploy'], {
    cwd: dirname(workerFile),
    stdio: ['inherit', 'pipe', 'pipe'],
  }) as ChildProcess;

  const urlPattern = /https:\/\/[^\s'"`]+/;
  let seenUrl: string | null = null;

  function scan(chunk: Buffer): void {
    if (seenUrl) {
      return;
    }
    const clean = chunk.toString('utf8').replace(/\x1b\[[0-9;]*m/g, '');
    const m = urlPattern.exec(clean);
    if (m) {
      seenUrl = m[0].replace(/[.,;)]+$/, '');
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
    processExit(1);
  });
  child.on('close', (code) => {
    if (!seenUrl) {
      console.error('[deploy-flash] no flash URL found in output');
      processExit(1);
    }
    consoleLog(seenUrl);
    processExit(code ?? 0);
  });
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const [workerFile] = process.argv.slice(2);
  if (!workerFile) {
    console.error('usage: deploy-flash.ts <worker_flash.py>');
    process.exit(1);
  }
  await run(workerFile);
}