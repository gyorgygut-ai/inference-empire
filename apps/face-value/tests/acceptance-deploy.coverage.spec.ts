import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

const WS = join(__dirname, '../../..');

function readDeployRouterEnv(): Record<string, string> {
  return {
    ROUTER_URL: readFileSync(join(WS, 'dist/router-flux2/deploy/ROUTER_URL'), 'utf8').trim(),
    SECRET_AUTH_TOKEN: readFileSync(
      join(WS, 'dist/router-flux2/deploy/ROUTER_SECRET_AUTH_TOKEN'),
      'utf8',
    ).trim(),
  };
}

describe('face-value:deploy', () => {
  it('artifact exists with router FLUX2 env', () => {
    const env = readDeployRouterEnv();
    expect(env['ROUTER_URL'] ?? '').not.toBe('');
    expect(env['SECRET_AUTH_TOKEN'] ?? '').not.toBe('');
  });

  it('reaches the router', async () => {
    const env = readDeployRouterEnv();
    const url = env['ROUTER_URL'] ?? '';
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
    expect(res.status).toBe(401);
    await res.arrayBuffer().catch(() => undefined);
  });

  it('rejects unauthenticated POST /q', async () => {
    const env = readDeployRouterEnv();
    const url = env['ROUTER_URL'] ?? '';
    const res = await fetch(`${url}/q`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
      signal: AbortSignal.timeout(8000),
    });
    expect(res.status).toBe(401);
    expect((await res.json()).error).toBe('Unauthorized');
  });

  it('rejects bad-token POST /q', async () => {
    const env = readDeployRouterEnv();
    const url = env['ROUTER_URL'] ?? '';
    const res = await fetch(`${url}/q`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer BAD',
      },
      body: '{}',
      signal: AbortSignal.timeout(8000),
    });
    expect(res.status).toBe(401);
    expect((await res.json()).error).toBe('Invalid token');
  });

  it('accepts good-token POST /q past auth', async () => {
    const env = readDeployRouterEnv();
    const url = env['ROUTER_URL'] ?? '';
    const token = env['SECRET_AUTH_TOKEN'] ?? '';
    const res = await fetch(`${url}/q`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ input: { prompt: 'a red square' } }),
      signal: AbortSignal.timeout(8000),
    });
    expect(res.status).not.toBe(401);
    await res.arrayBuffer().catch(() => undefined);
  });

  it('reaches GET /sup with valid token', async () => {
    const env = readDeployRouterEnv();
    const url = env['ROUTER_URL'] ?? '';
    const token = env['SECRET_AUTH_TOKEN'] ?? '';
    const res = await fetch(`${url}/sup`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(8000),
    });
    expect(res.status).not.toBe(401);
    await res.arrayBuffer().catch(() => undefined);
  });

  it('generate-image reads URL plus token from env with zero hardcoded values', () => {
    const src = readFileSync('apps/face-value/app/actions/generate-image.ts', 'utf8');
    expect(src).toContain('process.env.ROUTER_URL');
    expect(src).toContain('process.env.SECRET_AUTH_TOKEN');
    expect(src).not.toMatch(/https?:\/\//);
  });
});
