import { execSync } from 'node:child_process';

export function runCommand(command: string, cwd?: string): boolean {
  try {
    execSync(command, { stdio: 'inherit', cwd: cwd ?? process.cwd() });
    return true;
  } catch {
    return false;
  }
}
