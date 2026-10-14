import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { join } from 'node:path';

const raw = process.argv.slice(2);
let token = '';
let org = '';
let projectId = '';
const head: string[] = [];
for (let i = 0; i < raw.length; i++) {
  const a = raw[i] ?? '';
  if (a === '--token') token = raw[++i] ?? '';
  else if (a === '--org') org = raw[++i] ?? '';
  else if (a === '--project-id') projectId = raw[++i] ?? '';
  else head.push(a);
}

const [appDir, vercelProject, artifactProject, configuration, key] = head;
if (!appDir || !vercelProject || !artifactProject || configuration !== 'deploy' || !key || !token || !org || !projectId) {
  console.error('usage: deploy-vercel.ts <app-dir> <vercel-project> <artifact-project> deploy <KEY> --token <t> --org <o> --project-id <p>');
  process.exit(1);
}
const resolvedAppDir = join(process.cwd(), 'apps', appDir);
if (!existsSync(resolvedAppDir)) { console.error(`[deploy-vercel] missing app dir: apps/${appDir}`); process.exit(1); }

const child = spawn(
  'vercel',
  ['deploy', '--project', vercelProject, '--prod', '--yes', `--token=${token}`, '-F', 'json'],
  { cwd: resolvedAppDir, stdio: ['inherit', 'pipe', 'pipe'], env: { ...process.env, VERCEL_ORG_ID: org, VERCEL_PROJECT_ID: projectId } },
);
let stdout = '';
let stderr = '';
child.stdout?.on('data', (c: Buffer) => { process.stdout.write(c); stdout += c.toString('utf8'); });
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