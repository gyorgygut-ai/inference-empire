import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import type { ExecutorContext } from '@nx/devkit';
import executor from './run-command';

const NODE = process.execPath;
const scratch = () => mkdtempSync(join(tmpdir(), 'run-command-'));
const ctx = () => ({ root: process.cwd() }) as unknown as ExecutorContext;
const echo = (expression: string) => `-e "console.log(${expression})"`;

describe('run-command', () => {
  it('writes the first stdout line under envKey', async () => {
    const envFile = join(scratch(), 'dev.env');
    const r = await executor(
      { command: NODE, args: echo("'http://127.0.0.1:5040'"), envFile, envKey: 'ROUTER_URL' },
      ctx(),
    );
    expect(r.success).toBe(true);
    expect(readFileSync(envFile, 'utf8')).toBe('ROUTER_URL=http://127.0.0.1:5040\n');
  });

  it('preserves existing keys and is idempotent', async () => {
    const envFile = join(scratch(), 'dev.env');
    writeFileSync(envFile, 'MODAL_WORKER_URL=https://modal.example\n');
    const options = { command: NODE, args: echo("'x'"), envFile, envKey: 'ROUTER_URL' };
    await executor(options, ctx());
    await executor(options, ctx());
    expect(readFileSync(envFile, 'utf8')).toBe('MODAL_WORKER_URL=https://modal.example\nROUTER_URL=x\n');
  });

  it('loads envFile into the child env', async () => {
    const envFile = join(scratch(), 'dev.env');
    writeFileSync(envFile, 'SEED=from-file\n');
    const r = await executor(
      { command: NODE, args: echo('process.env.SEED'), envFile, envKey: 'ECHOED' },
      ctx(),
    );
    expect(r.success).toBe(true);
    expect(readFileSync(envFile, 'utf8')).toContain('ECHOED=from-file');
  });

  it('overlays env vars into the child env', async () => {
    const envFile = join(scratch(), 'dev.env');
    const r = await executor(
      {
        command: NODE,
        args: echo('process.env.PORT'),
        env: { PORT: '5040' },
        envFile,
        envKey: 'ECHOED',
      },
      ctx(),
    );
    expect(r.success).toBe(true);
    expect(readFileSync(envFile, 'utf8')).toContain('ECHOED=5040');
  });

  it('expands shell variables in the command', async () => {
    const envFile = join(scratch(), 'dev.env');
    const r = await executor(
      {
        command: NODE,
        args: '-e "console.log(\'$SHELL_VALUE\')"',
        env: { SHELL_VALUE: 'from-shell' },
        envFile,
        envKey: 'ECHOED',
      },
      ctx(),
    );
    expect(r.success).toBe(true);
    expect(readFileSync(envFile, 'utf8')).toContain('ECHOED=from-shell');
  });

  it('fails on non-zero exit', async () => {
    const r = await executor({ command: NODE, args: '-e "process.exit(1)"' }, ctx());
    expect(r.success).toBe(false);
  });

  it('writes the env value on capture while the process keeps running', async () => {
    const envFile = join(scratch(), 'dev.env');
    const done = executor(
      {
        command: NODE,
        args: `-e "console.log('http://127.0.0.1:5040'); setTimeout(() => {}, 300)"`,
        envFile,
        envKey: 'ROUTER_URL',
      },
      ctx(),
    );
    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(readFileSync(envFile, 'utf8')).toBe('ROUTER_URL=http://127.0.0.1:5040\n');
    expect((await done).success).toBe(true);
  });
});
