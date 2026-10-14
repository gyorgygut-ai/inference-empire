import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

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

const workerFile = workerFiles[0];
let handlerName: string | null = null;
try {
  const content = readFileSync(join(process.cwd(), dir, workerFile), 'utf8');
  const match = /@task_queue\([\s\S]*?\)\s*\n\s*def\s+(\w+)/.exec(content);
  if (match) handlerName = match[1];
} catch {
  handlerName = null;
}
if (!handlerName) {
  console.error(`[deploy-beam] could not find @task_queue handler in ${dir}/${workerFile}`);
  process.exit(1);
}
const workerPath = `${dir}/${workerFile}:${handlerName}`;
const subcommand = configuration === 'dev' ? 'serve' : 'deploy';
const child = spawn('uv', ['run', '--locked', 'beam', subcommand, workerPath], {
  stdio: ['inherit', 'pipe', 'pipe'],
});

const urlPattern = /https:\/\/[^\s'"]+/;
let seenUrl: string | null = null;

function scan(chunk: Buffer): void {
  if (seenUrl) {
    return;
  }
  const clean = chunk.toString('utf8').replace(/\x1b\[[0-9;]*m/g, '');
  const match = urlPattern.exec(clean);
  if (match) {
    seenUrl = match[0].replace(/[.,;)]+$/, '');
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
child.on('close', (code) => {
  if (!seenUrl) {
    const fallback = process.env.BEAM_URL ?? '';
    if (fallback) {
      seenUrl = fallback;
    }
  }
  if (seenUrl) {
    console.log(seenUrl);
  } else {
    console.error('[deploy-beam] no beam URL found in output');
    process.exit(1);
  }
  process.exit(code ?? 0);
});