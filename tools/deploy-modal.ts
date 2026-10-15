import { readdirSync } from 'node:fs';
import { join } from 'node:path';
import { spawn } from 'node:child_process';

const [project, configuration] = process.argv.slice(2);
if (!project || (configuration !== 'dev' && configuration !== 'deploy')) {
  console.error('usage: deploy-modal.ts <project> <dev|deploy>');
  process.exit(1);
}

const workerDir = `apps/${project.replace(/^worker-/, '').replace(/-/g, '_')}`;
let workerFiles: string[] = [];
try {
  workerFiles = readdirSync(join(process.cwd(), workerDir)).filter(
    (f) => f.startsWith('worker_modal_') && f.endsWith('.py'),
  );
} catch {
  workerFiles = [];
}
if (workerFiles.length !== 1) {
  console.error(
    `[deploy-modal] expected exactly one worker_modal_*.py in ${workerDir}, found ${workerFiles.length}`,
  );
  process.exit(1);
}

const subcommand = configuration === 'dev' ? 'serve' : 'deploy';
const child = spawn('uv', ['run', '--locked', 'modal', subcommand, join(workerDir, workerFiles[0])], {
  stdio: ['inherit', 'pipe', 'pipe'],
});

const urlPattern = /https:\/\/[^\s'"`]*\.modal\.run[^\s'"`]*/;
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
  process.stderr.write(chunk);
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
child.on('close', (code) => {
  if (!seenUrl) {
    console.error('[deploy-modal] no modal URL found in output');
    process.exit(1);
  }
  console.log(seenUrl);
  process.exit(code ?? 0);
});