import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';
import { readEnv } from './utils/read-env';

const WS = join(__dirname, '../../..');

describe('generative-ui face-value:dev', () => {
  it('artifact exists with router FLUX2 env', () => {
    const env = readEnv('dist/router-flux2/dev.env');
    expect(env['ROUTER_URL'] ?? '').not.toBe('');
    expect(env['SECRET_AUTH_TOKEN'] ?? '').not.toBe('');
  });

  it('reaches the router', async () => {
    const env = readEnv('dist/router-flux2/dev.env');
    const url = env['ROUTER_URL'] ?? '';
    const res = await fetch(url, { signal: AbortSignal.timeout(8000) });
    expect(res.status).toBe(401);
    await res.arrayBuffer().catch(() => undefined);
  });

  it('rejects unauthenticated POST /q', async () => {
    const env = readEnv('dist/router-flux2/dev.env');
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
    const env = readEnv('dist/router-flux2/dev.env');
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
    const env = readEnv('dist/router-flux2/dev.env');
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
    const env = readEnv('dist/router-flux2/dev.env');
    const url = env['ROUTER_URL'] ?? '';
    const token = env['SECRET_AUTH_TOKEN'] ?? '';
    const res = await fetch(`${url}/sup`, {
      headers: { Authorization: `Bearer ${token}` },
      signal: AbortSignal.timeout(8000),
    });
    expect(res.status).not.toBe(401);
    await res.arrayBuffer().catch(() => undefined);
  });

  describe('frontend face-value dev', () => {
    it('loads the router artifact directly with zero consumer copy', () => {
      expect(existsSync(join(WS, 'dist/generative-ui/dev.env'))).toBe(false);
      const project = JSON.parse(
        readFileSync(join(WS, 'apps/generative-ui/project.json'), 'utf8')
      ) as { targets: { 'face-value': { configurations: { dev: { envFile: string } } } } };
      expect(project.targets['face-value'].configurations.dev.envFile).toBe("dist/router-flux2/dev.env");
      const router = readEnv('dist/router-flux2/dev.env');
      expect(router['ROUTER_URL'] ?? '').not.toBe('');
      expect(router['SECRET_AUTH_TOKEN'] ?? '').not.toBe('');
    });

    it('serves the app', async () => {
      const res = await fetch('http://localhost:3000', {
        signal: AbortSignal.timeout(8000),
      });
      expect(res.status).toBe(200);
      await res.arrayBuffer().catch(() => undefined);
    });

    it('generate-image reads URL plus token from env with zero hardcoded values', () => {
      const src = readFileSync(
        join(WS, 'apps/generative-ui/app/actions/generate-image.ts'),
        'utf8'
      );
      expect(src).toContain('process.env.ROUTER_FLUX2_APP_URL');
      expect(src).toContain('process.env.ROUTER_FLUX2_SECRET_AUTH_TOKEN');
      expect(src).not.toMatch(/https?:\/\//);
    });
  });
});
