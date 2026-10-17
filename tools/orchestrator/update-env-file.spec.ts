import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { updateEnvFile } from './update-env-file';

function scratch(): string {
  return mkdtempSync(join(tmpdir(), 'orchestrator-'));
}

describe('updateEnvFile', () => {
  it('creates the parent directory and the file when absent', async () => {
    const target = join(scratch(), 'flux2', 'dev.env');

    await updateEnvFile(target, 'ROUTER_URL', 'http://127.0.0.1:5040');

    expect(readFileSync(target, 'utf8')).toBe('ROUTER_URL=http://127.0.0.1:5040\n');
  });

  it('replaces an existing key without duplicating it', async () => {
    const target = join(scratch(), 'dev.env');

    await updateEnvFile(target, 'ROUTER_URL', 'http://127.0.0.1:5040');
    await updateEnvFile(target, 'ROUTER_URL', 'http://127.0.0.1:9999');

    expect(readFileSync(target, 'utf8')).toBe('ROUTER_URL=http://127.0.0.1:9999\n');
  });

  it('preserves other keys and is idempotent on re-run', async () => {
    const target = join(scratch(), 'dev.env');

    await updateEnvFile(target, 'MODAL_WORKER_URL', 'https://modal.example');
    await updateEnvFile(target, 'ROUTER_AUTH_TOKEN', 'token-value');
    await updateEnvFile(target, 'MODAL_WORKER_URL', 'https://modal.example');

    expect(readFileSync(target, 'utf8')).toBe(
      'MODAL_WORKER_URL=https://modal.example\nROUTER_AUTH_TOKEN=token-value\n',
    );
  });

  it('does not treat a longer key with the same prefix as a match', async () => {
    const target = join(scratch(), 'dev.env');

    await updateEnvFile(target, 'PORTAL', 'https://portal.example');
    await updateEnvFile(target, 'PORT', '5040');

    expect(readFileSync(target, 'utf8')).toBe('PORTAL=https://portal.example\nPORT=5040\n');
  });
});
