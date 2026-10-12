import { existsSync } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';

const [project, configuration] = process.argv.slice(2);
if (!project || (configuration !== 'dev' && configuration !== 'deploy')) {
  console.error('usage: deploy-flash.ts <project> <dev|deploy>');
  process.exit(1);
}

const dir = `apps/${project.replace(/^worker-/, '').replace(/-/g, '_')}`;
if (!existsSync(dir)) {
  console.error(`[deploy-flash] missing worker dir: ${dir}`);
  process.exit(1);
}

const child = spawn('uv', ['run', '--locked', 'flash', 'deploy'], {
  cwd: dir,
  stdio: ['inherit', 'pipe', 'pipe'],
});

const urlPattern = /https:\/\/[^\s'"`]+/;
let seenUrl: string | null = null;

function upsert(url: string): void {
  const result = spawnSync(
    'tsx',
    ['tools/orchestration/upsert-artifact.ts', project, configuration, `FLASH_WORKER_URL=${url}`],
    { stdio: 'inherit', cwd: process.cwd() },
  );
  if (result.status !== 0) {
    console.error('[deploy-flash] upsert-artifact failed');
    process.exit(result.status ?? 1);
  }
}

function scan(chunk: Buffer): void {
  if (seenUrl) {
    return;
  }
  const match = urlPattern.exec(chunk.toString('utf8'));
  if (match) {
    seenUrl = match[0];
  }
}

child.stdout?.on('data', (chunk: Buffer) => {
  process.stdout.write(chunk);
  scan(chunk);
});
child.stderr?.on('data', (chunk: Buffer) => {
  process.stderr.write(chunk);
  scan(chunk);
});
child.on('error', (err) => {
  console.error(`[deploy-flash] failed to start flash: ${err.message}`);
  process.exit(1);
});
child.on('close', (code, signal) => {
  if (code !== 0) {
    process.exit(code ?? 1);
  }
  if (!seenUrl) {
    const fallback = process.env.APP_URL ?? '';
    if (!fallback) {
      console.error('[deploy-flash] no URL in output and APP_URL unset');
      process.exit(1);
    }
    upsert(fallback);
  } else {
    upsert(seenUrl);
  }
  if (signal) {
    process.exit(0);
  }
  process.exit(code ?? 0);
});
