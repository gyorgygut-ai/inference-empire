import { execSync } from 'node:child_process';

export function runCommand(command: string, cwd?: string, env?: NodeJS.ProcessEnv): boolean {
  try {
    execSync(command, {
      stdio: 'inherit',
      cwd: cwd ?? process.cwd(),
      env: { ...process.env, ...env },
    });
    return true;
  } catch {
    return false;
  }
}
