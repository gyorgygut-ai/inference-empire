#!/usr/bin/env -S npx tsx
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const raw = process.argv.slice(2);
let token = process.env.VERCEL_TOKEN ?? '';
let org = process.env.VERCEL_ORG_ID ?? '';
let projectId = process.env.VERCEL_PROJECT_ID ?? '';
let model = process.env.ROUTER_MODEL ?? '';
const head: string[] = [];
for (let i = 0; i < raw.length; i++) {
  const a = raw[i] ?? '';
  if (a === '--token') token = raw[++i] ?? token;
  else if (a === '--org') org = raw[++i] ?? org;
  else if (a === '--project-id') projectId = raw[++i] ?? projectId;
  else if (a === '--model') model = raw[++i] ?? model;
  else if (a.startsWith('--model=')) model = a.slice('--model='.length);
  else head.push(a);
}

const [appDir, scope] = head;
if (!appDir || !token || !org || !projectId || head.length > 2) {
  console.error(
    'usage: deploy-vercel.ts <app-dir> [from-root] [--model=<model>] (VERCEL_TOKEN/VERCEL_ORG_ID/VERCEL_PROJECT_ID env or --token/--org/--project-id)',
  );
  process.exit(1);
}
const resolvedAppDir = join(process.cwd(), 'apps', appDir);
if (!existsSync(resolvedAppDir)) { console.error(`[deploy-vercel] missing app dir: apps/${appDir}`); process.exit(1); }
// Monorepo apps with workspace deps must upload the repo root so Vercel
// can install from the workspace root; the project's Root Directory setting
// (e.g. apps/face-value) then scopes the build. Default stays app-dir only.
const deployCwd = scope === 'from-root' ? process.cwd() : resolvedAppDir;

const RUNTIME_KEYS = ['ROUTER_AUTH_TOKEN', 'ROUTER_URL', 'ROUTER_MODEL', 'MODAL_WORKER_URL', 'BEAM_WORKER_URL', 'FLASH_WORKER_URL'];
const runtime: NodeJS.ProcessEnv = model ? { ...process.env, ROUTER_MODEL: model } : process.env;
const envRun = RUNTIME_KEYS.filter((k) => runtime[k]).map((k) => `${k}=${runtime[k]}`);

const child = spawn(
  'vercel',
  ['deploy', ...envRun.flatMap((e) => ['-e', e]), '--prod', '--yes', `--token=${token}`, '-F', 'json'],
  { cwd: deployCwd, stdio: ['inherit', 'pipe', 'pipe'], env: { ...process.env, VERCEL_ORG_ID: org, VERCEL_PROJECT_ID: projectId } },
);
let stdout = '';
let stderr = '';
child.stdout?.on('data', (c: Buffer) => { process.stderr.write(c); stdout += c.toString('utf8'); });
child.stderr?.on('data', (c: Buffer) => { process.stderr.write(c); stderr += c.toString('utf8'); });
child.on('error', (e) => { console.error(`[deploy-vercel] failed to start vercel: ${e.message}`); process.exit(1); });
child.on('close', (code) => {
  const output = `${stdout}\n${stderr}`;
  if ((code ?? 1) !== 0) { console.error('[deploy-vercel] vercel deploy failed'); process.exit(code ?? 1); }
  let url = '';
  try {
    const p = JSON.parse(stdout.trim()) as { url?: unknown };
    if (typeof p.url === 'string') url = p.url;
  } catch { url = ''; }
  if (!url) {
    const m = [...output.matchAll(/"url"\s*:\s*"([^"]+)"/g)];
    url = m.length > 0 ? (m[m.length - 1][1] ?? '') : '';
  }
  if (!url) { console.error(output); console.error('[deploy-vercel] no url in vercel deploy output'); process.exit(1); }
  if (!url.startsWith('http')) url = `https://${url}`;
  console.log(url);
});