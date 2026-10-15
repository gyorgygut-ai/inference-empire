import { existsSync } from 'node:fs';
import { spawn } from 'node:child_process';

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
  console.error(`[deploy-flash] failed to start flash: ${err.message}`);
  process.exit(1);
});
child.on('close', (code) => {
  if (!seenUrl) {
    const fallback = process.env.FLASH_URL ?? '';
    if (fallback) {
      seenUrl = fallback;
    }
  }
  if (seenUrl) {
    console.log(seenUrl);
  } else {
    console.error('[deploy-flash] no flash URL found in output');
    process.exit(1);
  }
  process.exit(code ?? 0);
});