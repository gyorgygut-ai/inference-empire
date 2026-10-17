import { execSync, spawn } from 'node:child_process';

export function runCommand(command: string, cwd?: string): boolean {
  try {
    execSync(command, { stdio: 'inherit', cwd: cwd ?? process.cwd() });
    return true;
  } catch {
    return false;
  }
}

export function runCommandCapture(
  command: string,
  cwd: string,
  onStdout: (line: string) => void,
  env?: NodeJS.ProcessEnv,
): Promise<boolean> {
  const child = spawn(command, {
    cwd,
    shell: true,
    env,
    stdio: ['ignore', 'pipe', 'inherit'],
  });

  let buffered = '';
  let emitted = false;
  child.stdout?.on('data', (chunk: Buffer) => {
    if (emitted) {
      return;
    }
    buffered += chunk.toString();
    const newline = buffered.indexOf('\n');
    if (newline === -1) {
      return;
    }
    emitted = true;
    const line = buffered.slice(0, newline).trim();
    buffered = '';
    onStdout(line);
  });

  return new Promise((resolve) => {
    child.once('error', () => resolve(false));
    child.once('close', (code) => resolve(code === 0));
  });
}
