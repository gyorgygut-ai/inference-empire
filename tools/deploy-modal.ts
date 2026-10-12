import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';

const [project, configuration] = process.argv.slice(2);
if (!project || (configuration !== 'dev' && configuration !== 'deploy')) {
  console.error('usage: deploy-modal.ts <project> <dev|deploy>');
  process.exit(1);
}

const dir = `apps/${project.replace(/^worker-/, '').replace(/-/g, '_')}`;
let workerFiles: string[] = [];
try {
  workerFiles = readdirSync(join(process.cwd(), dir)).filter(
    (f) => f.startsWith('worker_modal_') && f.endsWith('.py'),
  );
} catch {
  workerFiles = [];
}
if (workerFiles.length !== 1) {
  console.error(
    `[deploy-modal] expected exactly one worker_modal_*.py in ${dir}, found ${workerFiles.length}`,
  );
  process.exit(1);
}

const subcommand = configuration === 'dev' ? 'serve' : 'deploy';
const child = spawn('uv', ['run', '--locked', 'modal', subcommand, `${dir}/${workerFiles[0]}`], {
  stdio: ['inherit', 'pipe', 'pipe'],
});

const urlPattern = /https:\/\/[^\s'"`]*\.modal\.run[^\s'"`]*/;
let seenUrl: string | null = null;

function upsert(url: string): void {
  const result = spawnSync(
    'tsx',
    ['tools/orchestration/upsert-artifact.ts', project, configuration, `MODAL_WORKER_URL=${url}`],
    { stdio: 'inherit' },
  );
  if (result.status !== 0) {
    console.error('[deploy-modal] upsert-artifact failed');
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
    if (configuration === 'dev') {
      upsert(seenUrl);
    }
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
  console.error(`[deploy-modal] failed to start modal: ${err.message}`);
  process.exit(1);
});
child.on('close', (code, signal) => {
  if (configuration === 'deploy' && code !== 0) {
    process.exit(code ?? 1);
  }
  if (!seenUrl) {
    const fallback = process.env.APP_URL ?? '';
    if (!fallback) {
      console.error('[deploy-modal] no modal.run URL in output and APP_URL unset');
      process.exit(1);
    }
    upsert(fallback);
  } else if (configuration === 'deploy') {
    upsert(seenUrl);
  }
  if (signal) {
    process.exit(0);
  }
  process.exit(code ?? 0);
});
