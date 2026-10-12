import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { spawn, spawnSync } from 'node:child_process';

const [project, configuration] = process.argv.slice(2);
if (!project || (configuration !== 'dev' && configuration !== 'deploy')) {
  console.error('usage: deploy-beam.ts <project> <dev|deploy>');
  process.exit(1);
}

const dir = `apps/${project.replace(/^worker-/, '').replace(/-/g, '_')}`;
let workerFiles: string[] = [];
try {
  workerFiles = readdirSync(join(process.cwd(), dir)).filter(
    (f) => f.startsWith('worker_beam_') && f.endsWith('.py'),
  );
} catch {
  workerFiles = [];
}
if (workerFiles.length !== 1) {
  console.error(
    `[deploy-beam] expected exactly one worker_beam_*.py in ${dir}, found ${workerFiles.length}`,
  );
  process.exit(1);
}

const child = spawn('uv', ['run', '--locked', 'beam', 'deploy', `${dir}/${workerFiles[0]}`], {
  stdio: ['inherit', 'pipe', 'pipe'],
});

const urlPattern = /https:\/\/[^\s'"`]+/;
let seenUrl: string | null = null;

function upsert(url: string): void {
  const result = spawnSync(
    'tsx',
    ['tools/orchestration/upsert-artifact.ts', project, configuration, `BEAM_WORKER_URL=${url}`],
    { stdio: 'inherit' },
  );
  if (result.status !== 0) {
    console.error('[deploy-beam] upsert-artifact failed');
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
  console.error(`[deploy-beam] failed to start beam: ${err.message}`);
  process.exit(1);
});
child.on('close', (code, signal) => {
  if (code !== 0) {
    process.exit(code ?? 1);
  }
  if (!seenUrl) {
    const fallback = process.env.APP_URL ?? '';
    if (!fallback) {
      console.error('[deploy-beam] no URL in output and APP_URL unset');
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
