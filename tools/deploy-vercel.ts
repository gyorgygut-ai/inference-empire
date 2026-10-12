import { spawn, spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const raw = process.argv.slice(2);
const envFlag = raw.indexOf('--env-file');
const head = envFlag === -1 ? raw : raw.slice(0, envFlag);
const envFiles: string[] = [];
if (envFlag !== -1) {
  for (let i = envFlag + 1; i < raw.length; i++) {
    const arg = raw[i] ?? '';
    if (arg.startsWith('--')) {
      break;
    }
    envFiles.push(arg);
  }
}
const [appDir, vercelProject, artifactProject, configuration, key] = head;
if (!appDir || !vercelProject || !artifactProject || configuration !== 'deploy' || !key) {
  console.error(
    'usage: deploy-vercel.ts <app-dir> <vercel-project> <artifact-project> deploy <KEY> [--env-file <path>...]',
  );
  process.exit(1);
}

const resolvedAppDir = join(process.cwd(), 'apps', appDir);
if (!existsSync(resolvedAppDir)) {
  console.error(`[deploy-vercel] missing app dir: apps/${appDir}`);
  process.exit(1);
}

const vercelEnv: string[] = [];
for (const file of envFiles) {
  const path = join(process.cwd(), file);
  if (!existsSync(path)) {
    console.error(`[deploy-vercel] missing env file: ${file}`);
    process.exit(1);
  }
  for (const line of readFileSync(path, 'utf8').split('\n')) {
    const trimmed = line.trim();
    if (trimmed.length === 0 || trimmed.startsWith('#') || !trimmed.includes('=')) {
      continue;
    }
    vercelEnv.push('-e', trimmed);
  }
}

const child = spawn(
  'vercel',
  ['deploy', '--project', vercelProject, '--prod', '--yes', ...vercelEnv, '-F', 'json'],
  { cwd: resolvedAppDir, stdio: ['inherit', 'pipe', 'pipe'] },
);
let stdout = '';
let stderr = '';
child.stdout?.on('data', (chunk: Buffer) => {
  process.stdout.write(chunk);
  stdout += chunk.toString('utf8');
});
child.stderr?.on('data', (chunk: Buffer) => {
  process.stderr.write(chunk);
  stderr += chunk.toString('utf8');
});
child.on('error', (err) => {
  console.error(`[deploy-vercel] failed to start vercel: ${err.message}`);
  process.exit(1);
});
child.on('close', (code) => {
  const output = `${stdout}\n${stderr}`;
  if ((code ?? 1) !== 0) {
    console.error('[deploy-vercel] vercel deploy failed');
    process.exit(code ?? 1);
  }
  finish(output);
});

function finish(output: string): void {
  let url = '';
  const trimmed = stdout.trim();
  if (trimmed) {
    try {
      const parsed = JSON.parse(trimmed) as { url?: unknown };
      if (typeof parsed.url === 'string') {
        url = parsed.url;
      }
    } catch {
      url = '';
    }
  }
  if (!url) {
    const urlMatches = [...output.matchAll(/"url"\s*:\s*"([^"]+)"/g)];
    url = urlMatches.length > 0 ? (urlMatches[urlMatches.length - 1][1] ?? '') : '';
  }
  if (!url) {
    const fallback = process.env.APP_URL ?? '';
    if (!fallback) {
      console.error(output);
      console.error('[deploy-vercel] no url in vercel deploy output and APP_URL unset');
      process.exit(1);
    }
    url = fallback;
  }
  if (!url.startsWith('http')) {
    url = `https://${url}`;
  }

  const upsert = spawnSync(
    'tsx',
    ['tools/orchestration/upsert-artifact.ts', artifactProject, configuration, `${key}=${url}`],
    { stdio: 'inherit' },
  );
  if (upsert.status !== 0) {
    console.error('[deploy-vercel] upsert-artifact failed');
    process.exit(upsert.status ?? 1);
  }
}
